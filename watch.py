#!/usr/bin/python
from tweetcap import tweetcap
from util import human_time_difference, dt_from_timestampms

from datetime import datetime
import dateutil.tz
import sqlite3
import sys
import json
import os
import re
from twython import Twython, TwythonStreamer
from twython.exceptions import TwythonAuthError
from requests.exceptions import ChunkedEncodingError

def get_setting(name):
    global cur
    cur.execute("SELECT value FROM settings WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is None:
        return None
    else:
        return row[0]

def render_tweet(tweet):
    global template_path
    return tweetcap(
            template_path,
            tweet['user']['name'],
            tweet['user']['screen_name'],
            tweet['user']['profile_image_url'],
            Twython.html_for_tweet(tweet),
            datetime.fromtimestamp(int(tweet['timestamp_ms']) / 1000).replace(tzinfo=dateutil.tz.tzutc()))

class MyStreamer(TwythonStreamer):
    def on_success(self, data):
        global cur, rest, follow_ids, template_path
        if 'text' in data:
            if data['user']['id_str'] in follow_ids:
                data_json = json.dumps(data)
                cur.execute(
                    'INSERT OR IGNORE INTO tweets(id_str, json) VALUES (?,?)', (data['id_str'], data_json))
                print('inserted ' + data['id_str'])
        elif 'delete' in data:
            deleted_status = data['delete']['status']
            cur.execute('SELECT json FROM tweets WHERE id_str = ?',
                        (deleted_status['id_str'],))
            row = cur.fetchone()
            if row is None:
                print(deleted_status['id_str'] + ' not found in db')
            else:
                tweet = json.loads(row[0])
                if 'retweeted_status' not in tweet:
                    elapsed = human_time_difference(dt_from_timestampms(tweet['timestamp_ms']), dt_from_timestampms(data['delete']['timestamp_ms']))
                    status = 'deleted after ' + elapsed
                    if len(tweet['entities']['urls']) > 0:
                        status += "\nlinks in original tweet:"
                        for url in tweet['entities']['urls']:
                            status += ' ' + url['expanded_url']
                    image_path = render_tweet(tweet)
                    image = open(image_path, 'rb')
                    media_id = rest.upload_media(media=image)['media_id']
                    rest.update_status(status=status, media_ids=[media_id])
                    image.close()
                    os.remove(image_path)

    def on_error(self, status_code, data):
        if status_code == 420:
            print('hit ratelimit, disconnecting')
            self.disconnect()


def begin_streaming():
    global follow_ids
    streaming = MyStreamer(consumer_key, consumer_secret,
                            access_token, access_token_secret)
    try:
        streaming.statuses.filter(follow=','.join(follow_ids))
    except ChunkedEncodingError as err:
        print('Recoverable stream error: ', err)
        begin_streaming()

db_path_default = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'tweets.db')
db_path = os.getenv('DB', db_path_default)
con = sqlite3.connect(db_path, isolation_level=None)
with con:
    cur = con.cursor()
    if len(sys.argv) == 2 and sys.argv[1] == 'init':
        cur.execute(
            'CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value TEXT)')
        consumer_key_old = get_setting('consumer_key')
        prompt = 'Enter consumer key'
        if consumer_key_old:
            prompt += ' [' + consumer_key_old + ']'
        consumer_key = input(prompt + ': ')
        if consumer_key == '':
            if consumer_key_old:
                consumer_key = consumer_key_old
            else:
                print("No consumer key provided")
                exit(1)
        consumer_secret_old = get_setting('consumer_secret')
        prompt = 'Enter consumer secret'
        if consumer_secret_old:
            prompt += ' [' + consumer_secret_old + ']'
        consumer_secret = input(prompt + ': ')
        if consumer_secret == '':
            if consumer_secret_old:
                consumer_secret = consumer_secret_old
            else:
                print("No consumer secret provided")
                exit(1)
        rest = Twython(consumer_key, consumer_secret)
        try:
            auth = rest.get_authentication_tokens()
        except TwythonAuthError:
            print("Bad API keys")
            exit(1)
        access_token_old = get_setting('access_token')
        access_token_secret_old = get_setting('access_token_secret')
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
    else:
        consumer_key = get_setting('consumer_key')
        consumer_secret = get_setting('consumer_secret')
        access_token = get_setting('access_token')
        access_token_secret = get_setting('access_token_secret')

        follow_ids = get_setting('follow').split(',')
        print("Following user IDs: " + ', '.join(follow_ids))
        template_path_default = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'template_new.html')
        template_path = os.getenv('TEMPLATE', template_path_default)
        rest = Twython(consumer_key, consumer_secret,
                       access_token, access_token_secret)
        
        begin_streaming()
