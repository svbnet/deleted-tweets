import os.path, logging, mimetypes

import context
from util import human_time_difference, dt_from_timestampms
from tweetcap import tweetcap
from retryer import Retryer


logger = logging.getLogger(__name__)


db = context.get_db()


retry = Retryer(lambda a, m: logger.info('Attempting %s / %s', a, m), lambda e: logger.error('Error while attempting: %s', e))


def render_tweet(tweet):
    return tweetcap(context.get_config()['template']['name'], tweet)


class Poster:
    def __init__(self, credentials):
        self.credentials = credentials
        self.twython = credentials.create_twython()
    
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
                    new_media_id = self.twython.upload_video(fp, mime_type, check_progress=True)['media_id']
                new_media_ids.append(new_media_id)
            if new_media_ids:
                stat = self.twython.update_status(
                    status=status, 
                    media_ids=new_media_ids,
                    in_reply_to_status_id=in_reply_id,
                    auto_populate_reply_metadata=True
                )
                db.insert_repost(stat['id_str'], self.credentials.account_id, tweet_id, 'media')
    
    def post_saved_tweet(self, tweet_id):
        logger.info(f"[tweet:{tweet_id}] begin reposting")
        saved_tweet = db.find_tweet(tweet_id)
        
        if saved_tweet is None:
            logger.info(f"[tweet:{tweet_id}] not found")
            return
        
        tweet = saved_tweet['tweet']
        if 'retweeted_status' in tweet:
            logger.info(f"[tweet:{tweet_id}] is a retweet, so skipping")
            return
        
        elapsed = human_time_difference(dt_from_timestampms(tweet['timestamp_ms']), saved_tweet['deleted_at'])
        status = 'deleted ' + elapsed
        if len(tweet['entities']['urls']) > 0:
            status += "\nlinks in original tweet:"
            for url in tweet['entities']['urls']:
                status += ' ' + url['expanded_url']

        image_path = render_tweet(tweet)
        mime_type, _ = mimetypes.guess_type(image_path)
        with open(image_path, 'rb') as image:
            media = retry.attempt(lambda: self.twython.upload_video(image, mime_type, check_progress=True))
            if not media:
                logger.error('Failed to upload media!')
                return
            new_tweet = retry.attempt(lambda: self.twython.update_status(status=status, media_ids=[media['media_id']]))
            if not new_tweet:
                logger.error('Failed to send tweet!')
                return

        db.insert_repost(new_tweet['id_str'], self.credentials.account_id, tweet_id)
        logger.info(f"[tweet:{tweet_id}] reposted, id = {new_tweet['id_str']}")

        # Post media if we have it as a reply
        self.post_tweet_media_as_followup(tweet_id, new_tweet['id_str'], 'media included in this tweet:')
        # Try and post quoted media
        if tweet['is_quote_status']:
            self.post_tweet_media_as_followup(tweet['quoted_status']['id_str'], new_tweet['id_str'], 'media from quoted tweet:')
