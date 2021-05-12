import sys, json

from deleted_tweets.tweetcap import tweetcap
from deleted_tweets import context

context.initialize()

db = context.get_db()

if len(sys.argv) < 2:
    print('Usage: test_render.py tweet_id')
    exit()

tweet_id = sys.argv[1]
tweet = db.find_tweet(tweet_id)
if tweet:
    print(tweetcap(context.template_name, tweet[0]))
else:
    print('Not found')
