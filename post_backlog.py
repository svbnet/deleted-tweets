from deleted_tweets import context, config as cfg
context.initialize(__file__)

from deleted_tweets.watcher import Watcher
from deleted_tweets.twitter import CredentialsBag
from deleted_tweets.poster import Poster

context.initialize(__file__)
db = context.get_db()
config = context.get_config()

watch_id = config['watcher']['watcher_account_id']
watcher_account = cfg.find_account_by_id(config, watch_id)

watcher_credentials = CredentialsBag() \
        .update_consumer(**config['consumer']) \
        .update_account(**watcher_account['access'], account_id=watch_id)
poster = Poster(watcher_credentials)

tweets = db.find_unreposted_tweets()

for tweet in tweets:
    poster.post_saved_tweet(tweet['tweet']['id_str'])
