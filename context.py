import os, os.path
import sqlite3

con = None
media_dir = './media'
template_path = os.getenv('TEMPLATE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_new.html'))
db_path = os.getenv('DB', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tweets.db'))


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
