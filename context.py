import os, os.path
import sqlite3
import logging


def relativize(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


con = None
media_dir = os.getenv('MEDIA_DIR', relativize('media'))
template_path = os.getenv('TEMPLATE', relativize('templates'))
template_name = os.getenv('TEMPLATE_NAME', 'template_new.html')
db_path = os.getenv('DB', relativize('tweets.db'))
log_path = os.getenv('LOG', relativize('log'))
log_level = os.getenv('LOGLEVEL', 'INFO')


def setup_logger():
    formatter = logging.Formatter('%(asctime)s:%(name)s [%(levelname)s] %(message)s')
    fh = logging.FileHandler(log_path)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger = logging.getLogger('')
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(getattr(logging, log_level))


def open_db():
    global con
    con = sqlite3.connect(db_path, isolation_level=None)


def get_setting(name):
    cur = con.execute("SELECT value FROM settings WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is None:
        return None
    else:
        return row[0]
