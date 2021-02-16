import json, os, os.path, urllib.request

import context
from util import human_time_difference, dt_from_timestampms

def tweet_has_media(tweet_dict):
    return tweet_dict['extended_entities'] and tweet_dict['extended_entities']['media']

class Watcher(object):

    def __init__(self, poster):
        super().__init__()
        self.poster = poster
    
    def save_tweet(self, tweet_dict):
        print(f"[tweet:{tweet_dict['id_str']}] Inserting into DB...")
        data_json = json.dumps(tweet_dict)
        context.con.execute('INSERT OR IGNORE INTO tweets(id_str, json) VALUES (?,?)', (tweet_dict['id_str'], data_json))

        if tweet_has_media(tweet_dict):
            print(f"[tweet:{tweet_dict['id_str']}] Downloading media...")
            dir_pref = os.path.join(context.media_dir, tweet_dict['id_str'])
            media = data_json['extended_entities']['media']
            i = 1
            for item in media:
                mtype = item['type']
                if mtype == 'video':
                    variants = sorted(item['video_info']['variants'], key=lambda variant: variant['bitrate'])
                    url = variants[0]['url']
                    ext = 'mp4'
                else:
                    url = item['media_url_https']
                ext = os.path.splitext(url)[1]
                media_path = os.path.join(dir_pref, f"{i}_{mtype}{ext}")
                print(f"[tweet:{tweet_dict['id_str']}][{mtype}:{i}] Downloading {url}...")
                urllib.request.urlretrieve(url, media_path)
                i += 1
    
    def post_saved_tweet(self, tweet_id, deleted_at):
        cur = context.con.execute('SELECT json FROM tweets WHERE id_str = ?', (tweet_id,))
        row = cur.fetchone()
        if row is None:
            print(f"[tweet:{tweet_id}] not found")
            return

        tweet = json.loads(row[0])
        if 'retweeted_status' in tweet:
            print(f"[tweet:{tweet_id}] is a retweet, so skipping")
            return
        
        elapsed = human_time_difference(dt_from_timestampms(tweet['timestamp_ms']), deleted_at)
        status = 'deleted after ' + elapsed
        if len(tweet['entities']['urls']) > 0:
            status += "\nlinks in original tweet:"
            for url in tweet['entities']['urls']:
                status += ' ' + url['expanded_url']

        image_path = render_tweet(tweet)
        image = open(image_path, 'rb')
        media_id = self.poster.upload_media(media=image)['media_id']
        new_tweet = self.poster.update_status(status=status, media_ids=[media_id])
        image.close()
        os.remove(image_path)

        dir_pref = os.path.join(context.media_dir, tweet_id)


