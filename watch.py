#!/usr/bin/python
import logging

import context
from watcher import Watcher

from twython import Twython

logger = logging.getLogger(__name__)

config = context.get_config()

watch_id = config['watcher']['watcher_account_id']
watcher_account = context.find_account_by_id(watch_id)

follow_ids = config['watcher']['watch_ids']
logger.info("Following user IDs: " + ', '.join(follow_ids))

try:
    rest = Twython(config['consumer']['key'], config['consumer']['secret'], watcher_account['access']['token'], watcher_account['access']['secret'])
    Watcher(config['consumer']['key'], config['consumer']['secret'], watcher_account['access']['token'], watcher_account['access']['secret'], rest, follow_ids).begin()
except KeyboardInterrupt:
    logger.info('SIGINT/ctrl-c received')
    exit(0)
except Exception as exc:
    logger.critical('Critical error: %s', exc, exc_info=True)
