import json


_DEFAULT_CONFIG = {
    'log': {
        'path': './data/log',
        'level': 'INFO',
    },
    'template': {
        'path': './templates',
        'name': 'template_new.html',
    },
    'db': './data/tweets.db',
    'media_dir': './data/media',
    'temp_dir': './data/temp',
    'custom_font': None,
}


def get_or_create(config_path):
    config = _DEFAULT_CONFIG
    try:
        with open(config_path, 'r') as fp:
            config.update(json.load(fp))
    except FileNotFoundError:
        commit(config_path, config)
    return config


def commit(config_path, config_dict):
    with open(config_path, 'w') as fp:
        json.dump(config_dict, fp, indent='    ')


def find_account_by_id(config, account_id):
    return [a for a in config['accounts'] if a['id'] == account_id][0]
