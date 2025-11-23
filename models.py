import time
from typing import Tuple, List, Optional

from database.db import db
from config.settings import (
    ARMORY_INITIAL_CAPACITY,
    ARMORY_UPGRADE_BASE_PRICE,
    ARMORY_UPGRADE_MULTIPLIER,
    ARMORY_CAPACITY_INCREMENT,
    IRON_SELL_PRICE,
    SILVER_SELL_PRICE
)
from utils.logger import logger


def user_exists(user_id: int) -> bool:
    row = db.fetchone("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return row is not None


def add_user(user_id: int, username: str = None) -> bool:
    if user_exists(user_id):
        # اگر کاربر وجود داره، username رو آپدیت کن
        if username:
            try:
                with db.get_cursor() as cursor:
                    cursor.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
            except Exception as e:
                logger.error(f"Error updating username for {user_id}: {e}")
        return False
    
    try:
        with db.get_cursor() as cursor:
            cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            cursor.execute("INSERT INTO resources (user_id) VALUES (?)", (user_id,))
            cursor.execute(
                "INSERT INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)",
                (user_id, 1, ARMORY_INITIAL_CAPACITY)
            )
        logger.info(f"New user added: {user_id} (@{username})")
        return True
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return False


def get_resources(user_id: int) -> Tuple[int, int, int]:
    row = db.fetchone(
        "SELECT iron, silver, coins FROM resources WHERE user_id=?",
        (user_id,)
    )
    if row:
        return row['iron'], row['silver'], row['coins']
    return 0, 0, 0


def get_user_money(user_id: int) -> int:
    """دریافت سکه‌های کاربر"""
    row = db.fetchone(
        "SELECT coins FROM resources WHERE user_id=?",
        (user_id,)
    )
    return row['coins'] if row else 0


def update_user_money(user_id: int, amount: int):
    """آپدیت سکه‌های کاربر (مقدار مثبت = اضافه، منفی = کم)"""
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE resources SET coins = coins + ? WHERE user_id = ?",
                (amount, user_id)
            )
        logger.info(f"User {user_id} coins updated: {amount:+d}")
    except Exception as e:
        logger.error(f"Error updating coins for user {user_id}: {e}")


def add_resources(user_id: int, iron: int = 0, silver: int = 0, coins: int = 0):
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE resources 
                SET iron = iron + ?, silver = silver + ?, coins = coins + ?
                WHERE user_id = ?
                """,
                (iron, silver, coins, user_id)
            )
        logger.info(f"User {user_id} resources updated: iron{iron:+d}, silver{silver:+d}, coins{coins:+d}")
    except Exception as e:
        logger.error(f"Error updating resources for user {user_id}: {e}")


def start_mining(user_id: int):
    now = time.time()
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE resources 
                SET mining_started=1, last_iron=?, last_silver=? 
                WHERE user_id=?
                """,
                (now, now, user_id)
            )
        logger.info(f"Mining started for user {user_id}")
    except Exception as e:
        logger.error(f"Error starting mining for user {user_id}: {e}")


def is_mining_active(user_id: int) -> bool:
    row = db.fetchone(
        "SELECT mining_started FROM resources WHERE user_id=?",
        (user_id,)
    )
    return bool(row and row['mining_started'] == 1)


def get_mining_users() -> List[Tuple[int, float, float]]:
    rows = db.fetchall(
        "SELECT user_id, last_iron, last_silver FROM resources WHERE mining_started=1"
    )
    return [(row['user_id'], row['last_iron'], row['last_silver']) for row in rows]


def update_mining_times(user_id: int, last_iron: float, last_silver: float):
    with db.get_cursor() as cursor:
        cursor.execute(
            "UPDATE resources SET last_iron=?, last_silver=? WHERE user_id=?",
            (last_iron, last_silver, user_id)
        )


def get_last_daily(user_id: int) -> float:
    row = db.fetchone(
        "SELECT last_daily FROM resources WHERE user_id=?",
        (user_id,)
    )
    return row['last_daily'] if row else 0


def claim_daily_reward(user_id: int, coins: int) -> bool:
    now = time.time()
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE resources SET coins=coins+?, last_daily=? WHERE user_id=?",
                (coins, now, user_id)
            )
        logger.info(f"User {user_id} claimed daily reward: +{coins} coins")
        return True
    except Exception as e:
        logger.error(f"Error claiming daily reward for user {user_id}: {e}")
        return False


def get_armory_meta(user_id: int) -> Tuple[int, int]:
    row = db.fetchone(
        "SELECT level, capacity FROM armory_meta WHERE user_id=?",
        (user_id,)
    )
    if row:
        return int(row['level']), int(row['capacity'])
    
    try:
        with db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)",
                (user_id, 1, ARMORY_INITIAL_CAPACITY)
            )
        return 1, ARMORY_INITIAL_CAPACITY
    except Exception as e:
        logger.error(f"Error initializing armory_meta for user {user_id}: {e}")
        return 1, ARMORY_INITIAL_CAPACITY


def set_armory_meta(user_id: int, level: int, capacity: int):
    with db.get_cursor() as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)",
            (user_id, level, capacity)
        )


def get_armory_count(user_id: int) -> int:
    row = db.fetchone(
        "SELECT SUM(count) as total FROM armory WHERE user_id=?",
        (user_id,)
    )
    return int(row['total']) if (row and row['total']) else 0


def add_weapon(user_id: int, weapon: str, amount: int = 1) -> bool:
    level, capacity = get_armory_meta(user_id)
    current = get_armory_count(user_id)
    
    if current + amount > capacity:
        logger.info(f"User {user_id} armory full ({current}/{capacity})")
        return False
    
    try:
        with db.get_cursor() as cursor:
            row = cursor.execute(
                "SELECT count FROM armory WHERE user_id=? AND weapon_name=?",
                (user_id, weapon)
            ).fetchone()
            
            if row:
                new_amount = row['count'] + amount
                cursor.execute(
                    "UPDATE armory SET count=? WHERE user_id=? AND weapon_name=?",
                    (new_amount, user_id, weapon)
                )
            else:
                cursor.execute(
                    "INSERT INTO armory (user_id, weapon_name, count) VALUES (?, ?, ?)",
                    (user_id, weapon, amount)
                )
        
        logger.info(f"User {user_id} added {amount}x {weapon} to armory ({current+amount}/{capacity})")
        return True
    except Exception as e:
        logger.error(f"Error adding weapon to armory for user {user_id}: {e}")
        return False


def get_armory_list(user_id: int) -> List[Tuple[str, int]]:
    rows = db.fetchall(
        "SELECT weapon_name, count FROM armory WHERE user_id=?",
        (user_id,)
    )
    return [(row['weapon_name'], row['count']) for row in rows]


def get_armory_upgrade_price(current_level: int) -> int:
    base = ARMORY_UPGRADE_BASE_PRICE
    multiplier = ARMORY_UPGRADE_MULTIPLIER
    exponent = max(0, current_level - 1)
    price = base * (multiplier ** exponent)
    return int(round(price))


def upgrade_armory(user_id: int) -> Tuple[bool, int, int]:
    level, capacity = get_armory_meta(user_id)
    price = get_armory_upgrade_price(level)
    
    iron, silver, coins = get_resources(user_id)
    if coins < price:
        logger.info(f"User {user_id} insufficient coins for armory upgrade: has {coins}, needs {price}")
        return False, level, capacity
    
    try:
        new_level = level + 1
        new_capacity = capacity + ARMORY_CAPACITY_INCREMENT
        
        add_resources(user_id, coins=-price)
        set_armory_meta(user_id, new_level, new_capacity)
        
        logger.info(f"User {user_id} upgraded armory to level {new_level}, capacity {new_capacity}, paid {price} coins")
        return True, new_level, new_capacity
    except Exception as e:
        logger.error(f"Error upgrading armory for user {user_id}: {e}")
        return False, level, capacity
