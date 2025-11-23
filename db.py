import sqlite3
import threading
from typing import Optional
from contextlib import contextmanager

from config.settings import DB_PATH
from utils.logger import logger


class Database:
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = DB_PATH
            self._local = threading.local()
            self.initialized = True
            logger.info(f"Database manager initialized with path: {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            logger.debug(f"New database connection created for thread {threading.current_thread().name}")
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor
    
    def fetchone(self, query: str, params: tuple = ()):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()):
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def close_all(self):
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
            logger.info("Database connections closed")


db = Database()


def init_database():
    logger.info("Initializing database tables...")
    
    with db.get_cursor() as cursor:
        # جدول users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            factory_level INTEGER DEFAULT 1,
            crafting_level INTEGER DEFAULT 1
        )
        """)
        
        # Migration: اضافه کردن ستون username
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            logger.info("Added username column to users table")
        except Exception:
            pass
        
        # Migration: اضافه کردن ستون factory_level
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN factory_level INTEGER DEFAULT 1")
            logger.info("Added factory_level column to users table")
        except Exception:
            pass
        
        # Migration: اضافه کردن ستون crafting_level
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN crafting_level INTEGER DEFAULT 1")
            logger.info("Added crafting_level column to users table")
        except Exception:
            pass
        
        # جدول resources
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            user_id INTEGER PRIMARY KEY,
            iron INTEGER DEFAULT 0,
            silver INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            mining_started INTEGER DEFAULT 0,
            last_iron REAL DEFAULT 0,
            last_silver REAL DEFAULT 0,
            last_daily REAL DEFAULT 0,
            power INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        # Migration: اضافه کردن ستون‌های wins و losses
        try:
            cursor.execute("ALTER TABLE resources ADD COLUMN wins INTEGER DEFAULT 0")
            logger.info("Added wins column to resources table")
        except Exception:
            pass
        
        try:
            cursor.execute("ALTER TABLE resources ADD COLUMN losses INTEGER DEFAULT 0")
            logger.info("Added losses column to resources table")
        except Exception:
            pass
        
        # Migration: اضافه کردن ستون power
        try:
            cursor.execute("ALTER TABLE resources ADD COLUMN power INTEGER DEFAULT 0")
            logger.info("Added power column to resources table")
        except Exception:
            pass
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS armory (
            user_id INTEGER,
            weapon_name TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, weapon_name),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS armory_meta (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            capacity INTEGER DEFAULT 5,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            leader_id INTEGER NOT NULL,
            description TEXT DEFAULT '',
            points INTEGER DEFAULT 0,
            treasury_coins INTEGER DEFAULT 0,
            treasury_iron INTEGER DEFAULT 0,
            treasury_silver INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            created_at REAL DEFAULT 0,
            FOREIGN KEY (leader_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_members (
            user_id INTEGER PRIMARY KEY,
            clan_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TEXT DEFAULT '',
            contribution_coins INTEGER DEFAULT 0,
            contribution_iron INTEGER DEFAULT 0,
            contribution_silver INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_wars (
            war_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            attacker_score INTEGER DEFAULT 0,
            defender_score INTEGER DEFAULT 0,
            winner_id INTEGER DEFAULT NULL,
            FOREIGN KEY (attacker_id) REFERENCES clans(clan_id),
            FOREIGN KEY (defender_id) REFERENCES clans(clan_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clan_missions (
            mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan_id INTEGER NOT NULL,
            mission_type TEXT NOT NULL,
            description TEXT NOT NULL,
            target INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            reward INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at REAL DEFAULT 0,
            FOREIGN KEY (clan_id) REFERENCES clans(clan_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_interest REAL DEFAULT 0,
            loan INTEGER DEFAULT 0,
            loan_date REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wheel_spins (
            user_id INTEGER PRIMARY KEY,
            last_spin REAL DEFAULT 0,
            total_spins INTEGER DEFAULT 0,
            free_spins_used INTEGER DEFAULT 0,
            last_free_spin_date TEXT DEFAULT '',
            streak_days INTEGER DEFAULT 0,
            last_streak_date TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wheel_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            reward_emoji TEXT NOT NULL,
            reward_description TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            user_id INTEGER,
            mission_type TEXT,
            target INTEGER,
            progress INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            date TEXT,
            PRIMARY KEY(user_id, date),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            achievement_id TEXT,
            unlocked_at REAL DEFAULT 0,
            PRIMARY KEY(user_id, achievement_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        # جدول کاربران بن شده
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            banned_at REAL DEFAULT 0,
            banned_by INTEGER DEFAULT NULL,
            reason TEXT DEFAULT NULL
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS battle_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender_id INTEGER NOT NULL,
            winner_id INTEGER NOT NULL,
            attacker_power INTEGER,
            defender_power INTEGER,
            coins_won INTEGER DEFAULT 0,
            timestamp REAL DEFAULT 0,
            FOREIGN KEY (attacker_id) REFERENCES users(user_id),
            FOREIGN KEY (defender_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pvp_ratings (
            user_id INTEGER PRIMARY KEY,
            rating INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            total_fights INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pvp_cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_battle REAL DEFAULT 0,
            shield_until REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            status TEXT DEFAULT 'active'
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_participants (
            tournament_id INTEGER,
            user_id INTEGER,
            score INTEGER DEFAULT 0,
            PRIMARY KEY(tournament_id, user_id),
            FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS revenge_used (
            user_id INTEGER,
            battle_log_id INTEGER,
            PRIMARY KEY(user_id, battle_log_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (battle_log_id) REFERENCES battle_logs(id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_queue (
            user_id INTEGER,
            weapon_name TEXT NOT NULL,
            started_at REAL NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            date TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(user_id),
            FOREIGN KEY (receiver_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            status TEXT DEFAULT 'active'
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_participants (
            event_id INTEGER,
            user_id INTEGER,
            score INTEGER DEFAULT 0,
            rewards_claimed INTEGER DEFAULT 0,
            PRIMARY KEY(event_id, user_id),
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            buyer_id INTEGER,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            listed_at REAL NOT NULL,
            sold_at REAL,
            FOREIGN KEY (seller_id) REFERENCES users(user_id),
            FOREIGN KEY (buyer_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_offers (
            offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            offer_items TEXT NOT NULL,
            request_items TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at REAL NOT NULL,
            completed_at REAL,
            FOREIGN KEY (from_user) REFERENCES users(user_id),
            FOREIGN KEY (to_user) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bosses (
            boss_id INTEGER PRIMARY KEY AUTOINCREMENT,
            boss_type TEXT NOT NULL,
            name TEXT NOT NULL,
            max_hp INTEGER NOT NULL,
            current_hp INTEGER NOT NULL,
            spawn_time REAL NOT NULL,
            end_time REAL NOT NULL,
            status TEXT DEFAULT 'active'
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS boss_participants (
            boss_id INTEGER,
            user_id INTEGER,
            damage_dealt INTEGER DEFAULT 0,
            attacks INTEGER DEFAULT 0,
            attacked_at REAL,
            rewards_claimed INTEGER DEFAULT 0,
            PRIMARY KEY(boss_id, user_id),
            FOREIGN KEY (boss_id) REFERENCES bosses(boss_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS campaign_progress (
            user_id INTEGER PRIMARY KEY,
            current_stage INTEGER DEFAULT 1,
            completed_stages INTEGER DEFAULT 0,
            total_stars INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_completions (
            user_id INTEGER,
            stage_id INTEGER,
            stars INTEGER DEFAULT 0,
            completed_at REAL,
            PRIMARY KEY(user_id, stage_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
        """)
    
    logger.info("Database tables initialized successfully")
