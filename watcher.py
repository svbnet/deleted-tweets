import json, os, os.path, urllib.request, logging, mimetypes
from datetime import datetime
from PIL.Image import new

from twython import Twython, TwythonStreamer, TwythonError
import dateutil.tz
from requests.exceptions import ChunkedEncodingError, ConnectionError

import context
from util import human_time_difference, dt_from_timestampms
from retryer import Retryer
from tweetcap import tweetcap

logger = logging.getLogger(__name__)

db = context.get_db()

def tweet_has_media(tweet_dict):
    return 'extended_entities' in tweet_dict and 'media' in tweet_dict['extended_entities']


def render_tweet(tweet):
    return tweetcap(context.get_config()['template']['name'], tweet)


def save_tweet_media(tweet_dict):
    logger.info(f"[tweet:{tweet_dict['id_str']}] Downloading media...")
    dir_pref = os.path.join(context.relativize(context.get_config()['media_dir']), tweet_dict['id_str'])
    media = tweet_dict['extended_entities']['media']
    i = 1
    for item in media:
        mtype = item['type']
        if mtype == 'video':
            variants = sorted(item['video_info']['variants'], key=lambda variant: variant.get('bitrate', 0), reverse=True)
            url = variants[0]['url']
            ext = '.mp4'
        else:
            url = item['media_url_https']
            ext = os.path.splitext(url)[1]
        media_path = os.path.join(dir_pref, f"{i}_{mtype}{ext}")
        logger.debug(f"[tweet:{tweet_dict['id_str']}][{mtype}:{i}] Downloading {url}...")
        os.makedirs(dir_pref, exist_ok=True)
        urllib.request.urlretrieve(url, media_path)
        i += 1


def save_tweet(tweet_dict):
    logger.info(f"[tweet:{tweet_dict['id_str']}] Inserting into DB...")
    db.insert_tweet(tweet_dict)

    if tweet_has_media(tweet_dict):
        try:
            save_tweet_media(tweet_dict)
        except Exception as err:
            logger.exception(f"[tweet:{tweet_dict['id_str']}] Downloading media failed, tweet may have been deleted too early: %s", err)
    
    if tweet_dict['is_quote_status']:
        quoted_tweet = tweet_dict['quoted_status']
        if tweet_has_media(quoted_tweet):
            logger.info('Quoted tweet has media, so downloading')
            try:
                save_tweet_media(quoted_tweet)
            except Exception as err:
                logger.exception(f"[tweet:{quoted_tweet['id_str']}] Downloading media failed, tweet may have been deleted too early: %s", err)
    
    logger.debug(f"[tweet:{tweet_dict['id_str']}] finished")


retry = Retryer(lambda a, m: logger.info('Attempting %s / %s', a, m), lambda e: logger.error('Error while attempting: %s', e))

class Watcher(TwythonStreamer):

    def __init__(self, credentials, poster_credentials, follow_ids):
        super().__init__(credentials.consumer_key, credentials.consumer_secret, 
                        credentials.access_token, credentials.access_token_secret)
        self.connection_attempts = 0
        self.poster_credentials = poster_credentials
        self.poster = poster_credentials.create_twython()
        self.follow_ids = follow_ids
    
    def begin(self):
        while self.connection_attempts < 10:
            logger.info('Attempting connection (attempts: %s)', self.connection_attempts)
            try:
                self.statuses.filter(follow=','.join(self.follow_ids))
            except ChunkedEncodingError as err:
                self.connection_attempts += 1
                logger.info('Recoverable stream error: %s', err, exc_info=True)
            except TwythonError as err:
                self.connection_attempts += 1
                logger.info('Twython error, may be recoverable: %s', err, exc_info=True)

        logger.warning('Failed to connect! Check network status/system time')
    
    def post_tweet_media_as_followup(self, tweet_id, in_reply_id, status):
        dir_pref = os.path.join(context.relativize(context.get_config()['media_dir']), tweet_id)
        if os.path.exists(dir_pref):
            logger.info(f"[tweet:{tweet_id}] posting followup media")
            new_media_ids = []
            for m in os.listdir(dir_pref):
                full_path = os.path.join(dir_pref, m)
                mime_type, _ = mimetypes.guess_type(full_path)
                with open(full_path, 'rb') as fp:
                    # chunked media upload for every type = better?
                    new_media_id = self.poster.upload_video(fp, mime_type, check_progress=True)['media_id']
                new_media_ids.append(new_media_id)
            if new_media_ids:
                stat = self.poster.update_status(
                    status=status, 
                    media_ids=new_media_ids,
                    in_reply_to_status_id=in_reply_id,
                    auto_populate_reply_metadata=True
                )
                db.insert_repost(stat['id_str'], self.poster_credentials.account_id, tweet_id, 'media')
    
    def post_saved_tweet(self, tweet_id, deleted_at):
        logger.info(f"[tweet:{tweet_id}] begin reposting")
        tweet = db.find_tweet(tweet_id)
        if tweet is None:
            logger.info(f"[tweet:{tweet_id}] not found")
            return

        db.update_tweet_deleted_at(tweet_id, deleted_at)

        if 'retweeted_status' in tweet:
            logger.info(f"[tweet:{tweet_id}] is a retweet, so skipping")
            return
        
        elapsed = human_time_difference(dt_from_timestampms(tweet['timestamp_ms']), deleted_at)
        status = 'deleted ' + elapsed
        if len(tweet['entities']['urls']) > 0:
            status += "\nlinks in original tweet:"
            for url in tweet['entities']['urls']:
                status += ' ' + url['expanded_url']

        image_path = render_tweet(tweet)
        mime_type, _ = mimetypes.guess_type(image_path)
        with open(image_path, 'rb') as image:
            media = retry.attempt(lambda: self.poster.upload_video(image, mime_type, check_progress=True))
            if not media:
                logger.error('Failed to upload media!')
                return
            new_tweet = retry.attempt(lambda: self.poster.update_status(status=status, media_ids=[media['media_id']]))
            if not new_tweet:
                logger.error('Failed to send tweet!')
                return

        db.insert_repost(new_tweet['id_str'], self.poster_credentials.account_id, tweet_id)
        logger.info(f"[tweet:{tweet_id}] reposted, id = {new_tweet['id_str']}")

        # Post media if we have it as a reply
        self.post_tweet_media_as_followup(tweet_id, new_tweet['id_str'], 'media included in this tweet:')
        # Try and post quoted media
        if tweet['is_quote_status']:
            self.post_tweet_media_as_followup(tweet['quoted_status']['id_str'], new_tweet['id_str'], 'media from quoted tweet:')
    
    def on_success(self, data):
        self.connection_attempts = 0
        if 'text' in data:
            if data['user']['id_str'] in self.follow_ids:
                save_tweet(data)
        elif 'delete' in data:
            self.post_saved_tweet(
                data['delete']['status']['id_str'], 
                dt_from_timestampms(data['delete']['timestamp_ms'])
            )
    
    def on_error(self, status_code, data, headers):
        logger.error('Stream error: %s %s %s', status_code, data, headers)
        if status_code == 420:
            logger.info('hit ratelimit, disconnecting')
            self.disconnect()
