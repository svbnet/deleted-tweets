import sys
import json
import re
from twython import Twython
from twython.exceptions import TwythonAuthError

import context

db = context.get_db()
config = context.get_config()

consumer_keys = config.get('consumer', None)
if not consumer_keys:
    print('''
    Please set the consumer keys in config.json as:
        {
            "consumer": {
                "key": "<your_consumer_key_here>",
                "secret": "<your_consumer_secret_here>"
            }
            ...
        }
    ''')

rest = Twython(consumer_keys['key'], consumer_keys['secret'])
try:
    auth = rest.get_authentication_tokens()
except TwythonAuthError:
    print("Bad API keys")
    exit(1)
access_token_old = context.get_setting('access_token')
access_token_secret_old = context.get_setting('access_token_secret')
if access_token_old is not None and access_token_secret_old is not None:
    keep = input('Use saved access token? [Y/n]: ')
    keep = not (keep == 'n' or keep == 'N')
else:
    keep = False
if keep:
    access_token = access_token_old
    access_token_secret = access_token_secret_old
else:
    print("\nGo to this URL and log in:\n" + auth['auth_url'] + "\n")
    rest = Twython(consumer_key, consumer_secret,
                    auth['oauth_token'], auth['oauth_token_secret'])
    pin = input('Enter PIN code: ')
    try:
        tokens = rest.get_authorized_tokens(pin)
        access_token = tokens['oauth_token']
        access_token_secret = tokens['oauth_token_secret']
    except TwythonAuthError:
        print("Invalid or expired PIN")
        exit(1)
rest = Twython(consumer_key, consumer_secret,
                access_token, access_token_secret)
follow = input('List of twitter accounts to follow: ')
follow_list = []
for account in re.split('[\s,]+', follow):
    if account.isdigit():
        user = rest.show_user(user_id=account)
    else:
        if account[0] == '@':
            account = account[1:]
        user = rest.show_user(screen_name=account)
    if 'id_str' in user:
        print("@" + user['screen_name'] +
                " (user ID " + user['id_str'] + ") found")
        follow_list.append(user['id_str'])
    else:
        print(account + " not found, aborting")
        exit(1)
follow_ids = ','.join(follow_list)
values = [('consumer_key', consumer_key), ('consumer_secret', consumer_secret), ('access_token',
                                                                                    access_token), ('access_token_secret', access_token_secret), ('follow', follow_ids)]
cur.executemany(
    'INSERT OR REPLACE INTO settings(name, value) VALUES (?,?)', values)
cur.execute('DROP TABLE IF EXISTS tweets')
cur.execute('CREATE TABLE tweets(id_str TEXT PRIMARY KEY, json TEXT)')
for user_id in follow_list:
    print("Backfilling user ID " + user_id)
    tweets = rest.get_user_timeline(user_id=user_id, count=200)
    count = 1
    for tweet in tweets:
        if 'text' in tweet and tweet['user']['id_str'] == user_id:
            tweet_json = json.dumps(tweet)
            cur.execute(
                'INSERT OR IGNORE INTO tweets(id_str, json) VALUES (?,?)', (tweet['id_str'], tweet_json))
            print("\r" + str(count) + '/' + str(len(tweets)), end=' ')
            sys.stdout.flush()
            count += 1
    print("\n")
print("Done")
