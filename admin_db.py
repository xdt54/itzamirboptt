# database/admin_db.py
"""
مدیریت دیتابیس ادمین‌ها و تنظیمات
"""

import json
import os
from typing import List, Optional, Dict, Any
from database.db import db
from utils.logger import logger


class AdminDatabase:
    """مدیریت ادمین‌ها و تنظیمات در دیتابیس"""
    
    SETTINGS_FILE = "data/admin_settings.json"
    
    def __init__(self):
        self._ensure_tables()
        self._load_settings()
    
    def _ensure_tables(self):
        """ایجاد جداول مورد نیاز"""
        with db.get_cursor() as cursor:
            # جدول ادمین‌ها
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    role TEXT DEFAULT 'admin',
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # جدول لاگ عملیات ادمین
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        logger.info("Admin database tables initialized")
    
    def _load_settings(self):
        """بارگذاری تنظیمات از فایل"""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                logger.error(f"Error loading admin settings: {e}")
                self.settings = {}
        else:
            self.settings = {}
    
    def _save_settings(self):
        """ذخیره تنظیمات در فایل"""
        os.makedirs(os.path.dirname(self.SETTINGS_FILE), exist_ok=True)
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving admin settings: {e}")
    
    # ==================== مدیریت ادمین‌ها ====================
    
    def add_admin(self, user_id: int, username: str, role: str, added_by: int) -> bool:
        """اضافه کردن ادمین جدید"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO admins (user_id, username, role, added_by)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, role, added_by))
            logger.info(f"Admin added: {user_id} by {added_by}")
            return True
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        """حذف ادمین"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("UPDATE admins SET is_active = 0 WHERE user_id = ?", (user_id,))
            logger.info(f"Admin removed: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing admin: {e}")
            return False
    
    def get_all_admins(self) -> List[Dict]:
        """دریافت لیست تمام ادمین‌ها"""
        rows = db.fetchall("SELECT * FROM admins WHERE is_active = 1 ORDER BY added_at DESC")
        return [dict(row) for row in rows]
    
    def is_admin(self, user_id: int) -> bool:
        """بررسی ادمین بودن"""
        row = db.fetchone(
            "SELECT 1 FROM admins WHERE user_id = ? AND is_active = 1",
            (user_id,)
        )
        return row is not None
    
    def get_admin_role(self, user_id: int) -> Optional[str]:
        """دریافت نقش ادمین"""
        row = db.fetchone(
            "SELECT role FROM admins WHERE user_id = ? AND is_active = 1",
            (user_id,)
        )
        return row['role'] if row else None
    
    # ==================== مدیریت تنظیمات ====================
    
    def set_log_group(self, group_id: int) -> bool:
        """تنظیم گروه لاگ"""
        try:
            self.settings['log_group_id'] = group_id
            self._save_settings()
            logger.info(f"Log group set to: {group_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting log group: {e}")
            return False
    
    def get_log_group(self) -> Optional[int]:
        """دریافت ID گروه لاگ"""
        return self.settings.get('log_group_id')
    
    def set_maintenance_mode(self, enabled: bool) -> bool:
        """تنظیم حالت تعمیر"""
        try:
            self.settings['maintenance_mode'] = enabled
            self._save_settings()
            return True
        except Exception as e:
            logger.error(f"Error setting maintenance mode: {e}")
            return False
    
    def is_maintenance_mode(self) -> bool:
        """بررسی حالت تعمیر"""
        return self.settings.get('maintenance_mode', False)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """دریافت تنظیم"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """تنظیم یک مقدار"""
        try:
            self.settings[key] = value
            self._save_settings()
            return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    # ==================== لاگ عملیات ====================
    
    def log_admin_action(self, admin_id: int, action: str, target: str = "", details: str = ""):
        """ثبت لاگ عملیات ادمین"""
        try:
            with db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_logs (admin_id, action, target, details)
                    VALUES (?, ?, ?, ?)
                """, (admin_id, action, target, details))
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
    
    def get_admin_logs(self, limit: int = 50) -> List[Dict]:
        """دریافت لاگ‌های اخیر"""
        rows = db.fetchall(
            "SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in rows]


# نمونه سینگلتون
_admin_db_instance = None

def get_admin_db() -> AdminDatabase:
    global _admin_db_instance
    if _admin_db_instance is None:
        _admin_db_instance = AdminDatabase()
    return _admin_db_instance
