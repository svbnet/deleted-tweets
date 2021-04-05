import os, os.path, logging, json, sys

from db import DB

def relativize(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

# Defaults
_DEFAULT_CONFIG = {
    'log': {
        'path': './log',
        'level': 'INFO',
    },
    'template': {
        'path': './templates',
        'name': 'template_new.html',
    },
    'db': './tweets.db',
    'media_dir': './media',
    'temp_dir': './temp',
    'custom_font': None,
}
_config = None

try:
    config_path = sys.argv[sys.argv.index('-c') + 1]
except (KeyError, ValueError):
    config_path = relativize('config.json')


def get_config():
    global _config
    if not _config:
        _config = _DEFAULT_CONFIG
        try:
            with open(config_path, 'r') as fp:
                _config.update(json.load(fp))
        except FileNotFoundError:
            commit_config()
            get_config()
    return _config


def find_account_by_id(account_id):
    return [a for a in get_config()['accounts'] if a['id'] == account_id][0]


def commit_config():
    with open(config_path, 'w') as fp:
        json.dump(_config, fp, indent='    ')


formatter = logging.Formatter('%(asctime)s:%(name)s [%(levelname)s] %(message)s')
fh = logging.FileHandler(get_config()['log']['path'])
fh.setFormatter(formatter)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger = logging.root
logger.setLevel(getattr(logging, get_config()['log']['level']))
logger.addHandler(fh)
logger.addHandler(sh)


_db = DB(get_config()['db'])
_db.connect()

def get_db():
    return _db
