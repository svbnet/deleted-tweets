import logging

from deleted_tweets import context, config as cfg
context.initialize(__file__)

from deleted_tweets.watcher import Watcher
from deleted_tweets.twitter import CredentialsBag
from deleted_tweets.poster import Poster


logger = logging.getLogger(__name__)

config = context.get_config()

watch_id = config['watcher']['watcher_account_id']
watcher_account = cfg.find_account_by_id(config, watch_id)

follow_ids = config['watcher']['watch_ids']
logger.info("Following user IDs: " + ', '.join(follow_ids))

try:
    watcher_credentials = CredentialsBag() \
            .update_consumer(**config['consumer']) \
            .update_account(**watcher_account['access'], account_id=watch_id)
    poster = Poster(watcher_credentials)
    # TODO distinct watcher and poster credentials...
    Watcher(watcher_credentials, poster, follow_ids).begin()
except KeyboardInterrupt:
    logger.info('SIGINT/ctrl-c received')
    exit(0)
except Exception as exc:
    logger.critical('Critical error: %s', exc, exc_info=True)
