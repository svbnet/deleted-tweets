#!/usr/bin/python
import logging

import context
from watcher import Watcher

from twython import Twython

context.setup_logger()
logger = logging.getLogger(__name__)

context.open_db()

consumer_key = context.get_setting('consumer_key')
consumer_secret = context.get_setting('consumer_secret')
access_token = context.get_setting('access_token')
access_token_secret = context.get_setting('access_token_secret')

follow_ids = context.get_setting('follow').split(',')
logger.info("Following user IDs: " + ', '.join(follow_ids))

try:
    rest = Twython(consumer_key, consumer_secret, access_token, access_token_secret)
    Watcher(consumer_key, consumer_secret, access_token, access_token_secret, rest, follow_ids).begin()
except KeyboardInterrupt:
    logger.info('SIGINT/ctrl-c received')
    exit(0)
except Exception as exc:
    logger.exception('Critical error', exc)
