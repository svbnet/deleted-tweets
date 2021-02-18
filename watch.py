#!/usr/bin/python
import context
from watcher import Watcher

from twython import Twython

context.open_db()

consumer_key = context.get_setting('consumer_key')
consumer_secret = context.get_setting('consumer_secret')
access_token = context.get_setting('access_token')
access_token_secret = context.get_setting('access_token_secret')

follow_ids = context.get_setting('follow').split(',')
print("Following user IDs: " + ', '.join(follow_ids))

rest = Twython(consumer_key, consumer_secret,
                access_token, access_token_secret)
Watcher(consumer_key, consumer_secret, access_token, access_token_secret, rest, follow_ids).begin()
