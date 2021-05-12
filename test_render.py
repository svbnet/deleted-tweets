import sys

from deleted_tweets.tweetcap import tweetcap
from deleted_tweets import context

context.initialize(__file__)

db = context.get_db()
config = context.get_config()

if len(sys.argv) < 2:
    print('Usage: test_render.py tweet_id')
    exit()

tweet_id = sys.argv[1]
tweet = db.find_tweet(tweet_id)
if tweet:
    print(tweetcap(config['template']['name'], tweet['tweet']))
else:
    print('Not found')
