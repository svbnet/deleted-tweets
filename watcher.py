import json, os, os.path, urllib.request, logging
from datetime import datetime

from twython import Twython, TwythonStreamer
import dateutil.tz
from requests.exceptions import ChunkedEncodingError, ConnectionError

import context
from util import human_time_difference, dt_from_timestampms
from tweetcap import tweetcap

logger = logging.getLogger(__name__)

def tweet_has_media(tweet_dict):
    return 'extended_entities' in tweet_dict and 'media' in tweet_dict['extended_entities']


def render_tweet(tweet):
    return tweetcap(context.template_name, tweet)


class Watcher(TwythonStreamer):

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret, poster, follow_ids):
        super().__init__(consumer_key, consumer_secret, access_token, access_token_secret)
        self.connection_attempts = 0
        self.poster = poster
        self.follow_ids = follow_ids
    
    def begin(self):
        while self.connection_attempts < 10:
            logger.info('Attempting connection (attempts: %s)', self.connection_attempts)
            try:
                self.statuses.filter(follow=','.join(self.follow_ids))
            except ChunkedEncodingError as err:
                self.connection_attempts += 1
                logger.info('Recoverable stream error: %s', err, exc_info=True)
            except ConnectionError as err:
                self.connection_attempts += 1
                logger.info('Connection error, may be recoverable: %s', err, exc_info=True)

        logger.warning('Failed to connect! Check network status/system time')
    
    def save_tweet_media(self, tweet_dict):
        logger.info(f"[tweet:{tweet_dict['id_str']}] Downloading media...")
        dir_pref = os.path.join(context.media_dir, tweet_dict['id_str'])
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

    def save_tweet(self, tweet_dict):
        logger.info(f"[tweet:{tweet_dict['id_str']}] Inserting into DB...")
        data_json = json.dumps(tweet_dict)
        context.con.execute('INSERT OR IGNORE INTO tweets(id_str, json) VALUES (?,?)', (tweet_dict['id_str'], data_json))

        if tweet_has_media(tweet_dict):
            try:
                self.save_tweet_media(tweet_dict)
            except Exception as err:
                logger.exception(f"[tweet:{tweet_dict['id_str']}] Downloading media failed, tweet may have been deleted too early ", err)
        
        if tweet_dict['is_quote_status']:
            quoted_tweet = tweet_dict['quoted_status']
            if tweet_has_media(quoted_tweet):
                logger.info('Quoted tweet has media, so downloading')
                try:
                    self.save_tweet_media(quoted_tweet)
                except Exception as err:
                    logger.exception(f"[tweet:{quoted_tweet['id_str']}] Downloading media failed, tweet may have been deleted too early ", err)
        
        logger.debug(f"[tweet:{tweet_dict['id_str']}] finished")
    
    def post_tweet_media_as_followup(self, tweet_id, in_reply_id, status):
        dir_pref = os.path.join(context.media_dir, tweet_id)
        if os.path.exists(dir_pref):
            logger.info(f"[tweet:{tweet_id}] posting followup media")
            new_media_ids = []
            for m in os.listdir(dir_pref):
                full_path = os.path.join(dir_pref, m)
                with open(full_path, 'rb') as fp:
                    if full_path.endswith('mp4'):
                        pass # Not working
                        # new_media_id = self.poster.upload_media(media=fp, media_type='video/mp4')['media_id']
                    else:
                        new_media_id = self.poster.upload_media(media=fp)['media_id']
                        new_media_ids.append(new_media_id)
            if new_media_ids:
                self.poster.update_status(
                    status=status, 
                    media_ids=new_media_ids,
                    in_reply_to_status_id=in_reply_id,
                    auto_populate_reply_metadata=True
                )
    
    def post_saved_tweet(self, tweet_id, deleted_at):
        logger.info(f"[tweet:{tweet_id}] begin reposting")
        cur = context.con.execute('SELECT json FROM tweets WHERE id_str = ?', (tweet_id,))
        row = cur.fetchone()
        if row is None:
            logger.info(f"[tweet:{tweet_id}] not found")
            return

        tweet = json.loads(row[0])
        if 'retweeted_status' in tweet:
            logger.info(f"[tweet:{tweet_id}] is a retweet, so skipping")
            return
        
        elapsed = human_time_difference(dt_from_timestampms(tweet['timestamp_ms']), deleted_at)
        status = 'deleted after ' + elapsed
        if len(tweet['entities']['urls']) > 0:
            status += "\nlinks in original tweet:"
            for url in tweet['entities']['urls']:
                status += ' ' + url['expanded_url']

        image_path = render_tweet(tweet)
        image = open(image_path, 'rb')
        media_id = self.poster.upload_media(media=image)['media_id']
        new_tweet = self.poster.update_status(status=status, media_ids=[media_id])
        image.close()
        os.remove(image_path)
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
                self.save_tweet(data)
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
