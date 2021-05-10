import context
from twitter import CredentialsBag
from poster import Poster

db = context.get_db()
config = context.get_config()
watch_id = config['watcher']['watcher_account_id']
watcher_account = context.find_account_by_id(watch_id)

watcher_credentials = CredentialsBag() \
        .update_consumer(**config['consumer']) \
        .update_account(**watcher_account['access'], account_id=watch_id)
poster = Poster(watcher_credentials)

tweets = db.find_unreposted_tweets()

for tweet in tweets:
    poster.post_saved_tweet(tweet['tweet']['id_str'])
