import os, os.path, urllib.request, logging

from twython import TwythonStreamer, TwythonError
from requests.exceptions import ChunkedEncodingError

from deleted_tweets import context
from deleted_tweets.util import dt_from_timestampms


logger = logging.getLogger(__name__)

db = context.get_db()


def tweet_has_media(tweet_dict):
    return 'extended_entities' in tweet_dict and 'media' in tweet_dict['extended_entities']


def save_tweet_media(tweet_dict):
    logger.info(f"[tweet:{tweet_dict['id_str']}] Downloading media...")
    dir_pref = os.path.join(context.relativize(context.get_config()['media_dir']), tweet_dict['id_str'])
    media = tweet_dict['extended_entities']['media']
    i = 1
    for item in media:
        mtype = item['type']
        if mtype == 'video' or mtype == 'animated_gif':
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


class Watcher(TwythonStreamer):

    def __init__(self, credentials, poster, follow_ids):
        super().__init__(credentials.consumer_key, credentials.consumer_secret, 
                        credentials.access_token, credentials.access_token_secret)
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
            except TwythonError as err:
                self.connection_attempts += 1
                logger.info('Twython error, may be recoverable: %s', err, exc_info=True)

        logger.warning('Failed to connect! Check network status/system time')
    
    def on_delete(self, tweet_id, deleted_at):
        db.update_tweet_deleted_at(tweet_id, deleted_at)
        self.poster.post_saved_tweet(tweet_id)

    def on_success(self, data):
        self.connection_attempts = 0
        if 'text' in data:
            if data['user']['id_str'] in self.follow_ids:
                save_tweet(data)
        elif 'delete' in data:
            self.on_delete(
                data['delete']['status']['id_str'], 
                dt_from_timestampms(data['delete']['timestamp_ms'])
            )
    
    def on_error(self, status_code, data, headers):
        logger.error('Stream error: %s %s %s', status_code, data, headers)
        if status_code == 420:
            logger.info('hit ratelimit, disconnecting')
            self.disconnect()
