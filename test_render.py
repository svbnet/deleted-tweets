import sys, json

from tweetcap import tweetcap
import context

context.open_db()

tweet_id = sys.argv[1]
tweet = json.loads(context.con.execute('select json from tweets where id_str = ?', (tweet_id,)).fetchone()[0])

print(tweetcap(context.template_name, tweet))
