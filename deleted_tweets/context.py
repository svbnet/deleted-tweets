import os, os.path, logging, json, sys, distutils.spawn

from deleted_tweets.db import DB
from deleted_tweets import config


_config = None
_config_path = None
_db = None
_init_dir = None


def relativize(filename):
    return os.path.join(_init_dir, filename)


def get_config():
    return _config


def commit_config():
    config.commit(_config_path, _config)


def get_db():
    return _db


def initialize(init_file_path):
    global _db, _config, _config_path, _init_dir
    _init_dir = os.path.dirname(os.path.abspath(init_file_path))

    # Check wkhtmltoimage
    if not distutils.spawn.find_executable('wkhtmltoimage'):
        raise RuntimeError('The `wkhtmltoimage\' command was not found in PATH. Please install wkhtmltopdf and try again.')

    # Make config path
    try:
        _config_path = sys.argv[sys.argv.index('-c') + 1]
    except (KeyError, ValueError):
        _config_path = relativize('config.json')
    
    # Init config
    _config = config.get_or_create(config_path)

    # Init logging
    formatter = logging.Formatter('%(asctime)s:%(name)s [%(levelname)s] %(message)s')
    fh = logging.FileHandler(get_config()['log']['path'])
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger = logging.root
    logger.setLevel(getattr(logging, get_config()['log']['level']))
    logger.addHandler(fh)
    logger.addHandler(sh)

    # Init DB
    logger.debug('Loading or initializing database')
    _db = DB(get_config()['db'])
    _db.connect()
