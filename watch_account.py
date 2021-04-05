import re, sys

from twython import Twython

import context
config = context.get_config()
db = context.get_db()

if len(sys.argv) < 2:
    print('Usage: watch_account.py <watcher_name_or_id> [accounts_to_watch...]\n')
    exit(-1)

watcher = sys.argv[1].lower()
accounts = config['accounts']

watcher_account = [account for account in accounts if account['id'] == watcher or account['handle'].lower() == watcher][0]
rest = Twython(
    config['consumer']['key'],
    config['consumer']['secret'],
    watcher_account['access']['token'],
    watcher_account['access']['secret'])


def backfill(user_id):
    print(f"Backfilling user ID {user_id} (max: 3,200 tweets)")
    cur = rest.cursor(rest.get_user_timeline, return_pages=True, user_id=user_id, count=200)
    page_index = 1
    tweet_index = 1
    total_index = 1
    try:
        for page in cur:
            for tweet in page:
                if 'text' in tweet and tweet['user']['id_str'] == user_id:
                    db.insert_tweet(tweet)
                    print(f"\rPage {page_index} / Tweet {tweet_index} / Total {total_index}", end=' ')
                    sys.stdout.flush()
                    tweet_index += 1
                    total_index += 1
            tweet_index = 1
            page_index += 1
    except RuntimeError as ex:
        # TODO remove this when Twython fixes StopIteration being raised... grr
        if type(ex.__cause__) != StopIteration:
            raise
        
    print("\n")

watcher = config.get('watcher', {})
config['watcher'] = watcher
watch_ids = watcher.get('watch_ids', [])
watcher['watch_ids'] = watch_ids

for account in sys.argv[2:]:
    if account.isdigit():
        user = rest.show_user(user_id=account)
    else:
        if account[0] == '@':
            account = account[1:]
        user = rest.show_user(screen_name=account)
    if 'id_str' in user:
        print("@" + user['screen_name'] +
                " (user ID " + user['id_str'] + ") found")
        if user['id_str'] not in watch_ids:
            watch_ids.append(user['id_str'])
        context.commit_config()
        backfill(user['id_str'])
    else:
        print(account + " not found, skipping")

print("Done")