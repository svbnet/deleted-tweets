import logging, sqlite3, os, os.path, shutil, json
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class DBVersionError(Exception):
    pass


class DB:
    EXPECTED_VERSION = 1
    INIT_SCHEMA = f"""
    CREATE TABLE IF NOT EXISTS `settings` (
        `name` TEXT PRIMARY KEY, 
        `value` TEXT);
    
    CREATE TABLE IF NOT EXISTS `tweets` (
        `id_str` TEXT PRIMARY KEY,
        `inserted_at` TIMESTAMP,
        `deleted_at` TIMESTAMP,
        `json` TEXT);
    
    CREATE TABLE IF NOT EXISTS `reposts` (
        `id_str` TEXT PRIMARY KEY,
        `poster_id_str` TEXT,
        `original_tweet_id_str` TEXT,
        `repost_type` TEXT,
        `inserted_at` TIMESTAMP);
    
    INSERT INTO `settings` (`name`, `value`) VALUES ('version', '{EXPECTED_VERSION}');
    """

    def __init__(self, path):
        self.path = path
        self.conn = None
        self.current_version = None
        
    def _connect(self):
        exists = os.path.exists(self.path)
        self.conn = sqlite3.connect(self.path, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
        if not exists:
            self.initialize()
    
    def connect(self):
        if self.conn:
            return
        self.check_for_migrations()            
    
    def disconnect(self):
        if self.conn:
            self.conn.close()
        self.conn = None
    
    def initialize(self):
        logger.info("%s doesn't exist, so creating...", self.path)
        self.conn.executescript(self.INIT_SCHEMA)
    
    def insert_tweet(self, tweet_dict):
        self.conn.execute(
            "INSERT OR IGNORE INTO `tweets` (`id_str`, `inserted_at`, `json`) VALUES (?, ?, ?)",
            [tweet_dict['id_str'], datetime.utcnow(), json.dumps(tweet_dict)]
        )
    
    def find_tweet(self, id_str):
        row = self.conn.execute("SELECT `json`, `deleted_at` FROM `tweets` WHERE `id_str` = ? LIMIT 0, 1", [id_str]).fetchone()
        if not row: return None
        return {
            'tweet': json.loads(row[0]),
            'deleted_at': row[1].replace(tzinfo=timezone.utc)
        }
    
    def update_tweet_deleted_at(self, id_str, deleted_at):
        self.conn.execute("UPDATE `tweets` SET `deleted_at` = ? WHERE `id_str` = ?", [deleted_at, id_str])

    def insert_repost(self, id_str, poster_id_str, original_tweet_id_str, repost_type='tweet'):
        self.conn.execute("""INSERT INTO `reposts` (`id_str`, `poster_id_str`, 
        `original_tweet_id_str`, `repost_type`, `inserted_at`)
        VALUES (?, ?, ?, ?, ?)""", [id_str, poster_id_str, original_tweet_id_str, repost_type, datetime.now()])
    
    def find_unreposted_tweets(self):
        rows = self.conn.execute("""SELECT `json`, `deleted_at` FROM `tweets`
        LEFT JOIN `reposts` ON `reposts`.`original_tweet_id_str` = `tweets`.`id_str`
        WHERE `tweets`.`deleted_at` IS NOT NULL 
        AND `reposts`.`original_tweet_id_str` IS NULL
        ORDER BY `tweets`.`deleted_at`""")
        if not rows: return []
        return [{'tweet': json.loads(row[0]), 'deleted_at': row[1].replace(tzinfo=timezone.utc)} for row in rows]

    def check_for_migrations(self):
        self._connect()
        cur = self.conn.cursor()
        version_row = cur.execute("SELECT `value` FROM `settings` WHERE `name` = 'version'").fetchone()
        if version_row:
            self.current_version = int(version_row[0])
            # TODO change when migrating from 1 to 2
            if self.current_version != self.EXPECTED_VERSION:
                raise DBVersionError(f"DB version is {self.current_version}, expected {self.EXPECTED_VERSION}")
        else:
            self.current_version = 0
            self.disconnect()
            self.execute_migration(self.current_version, self.EXPECTED_VERSION)
    
    def _versioned_path(self):
            return f'{self.path}.{self.current_version}'
    
    def _prepare_migration_db(self):
        logger.info('Backing up old DB...')
        shutil.copy(self.path, self._versioned_path())
    
    def _rollback_migration_db(self):
        logger.warning('Migration failed - restoring previous version...')
        self.disconnect()
        os.remove(self.path)
        os.rename(self._versioned_path(), self.path)
    
    def execute_migration(self, current_version, new_version):
        logger.info('Migrating DB from %s to %s', current_version, new_version)
        meth = f'_migrate_{current_version}_to_{new_version}'
        try:
            self._prepare_migration_db()
            getattr(self, meth)()
            self.current_version = new_version
        except Exception as ex:
            self._rollback_migration_db()
            raise ex
    
    def _migrate_0_to_1(self):
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        logger.info('Migrating tweets...')
        old_tweets = self.conn.execute("SELECT * FROM `tweets`").fetchall()
        self.conn.executescript("""
            DROP TABLE `tweets`;

            CREATE TABLE IF NOT EXISTS `tweets` (
                `id_str` TEXT PRIMARY KEY,
                `inserted_at` TIMESTAMP,
                `deleted_at` TIMESTAMP,
                `json` TEXT);

            CREATE TABLE IF NOT EXISTS `reposts` (
                `id_str` TEXT PRIMARY KEY,
                `poster_id_str` TEXT,
                `original_tweet_id_str` TEXT,
                `repost_type` TEXT,
                `inserted_at` TIMESTAMP);
        """)
        self.conn.executemany("INSERT INTO `tweets` (`id_str`, `json`) VALUES (?, ?)", old_tweets)
        self.conn.execute("INSERT INTO `settings` (`name`, `value`) VALUES ('version', '1')")
        logger.info('Complete - now please reinit')
        