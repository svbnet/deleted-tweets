import argparse
from datetime import datetime

from tweetcap import tweetcap
import context

parser = argparse.ArgumentParser()
parser.add_argument('--dispname', default='John 🤩 Sample')
parser.add_argument('--username', default='johnsample')
parser.add_argument('--text', default='The quick brown fox jumps over the lazy dog 1234567890 🤓🦴👩🏾‍🤝‍👩🏻👩‍👧👨‍👩‍👦‍👦👨‍👨‍👦🌷🌲🌕⛱')
parser.add_argument('--profpic', default='https://placehold.it/64x64')
parser.add_argument('--date', default=datetime.now())

args = parser.parse_args()

print(tweetcap(context.template_path, args.dispname, args.username, args.profpic, args.text, args.date))
