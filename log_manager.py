# utils/log_manager.py
"""
مدیریت لاگینگ به گروه تلگرام با Topic
"""

import json
import os
from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError
from utils.logger import logger

TOPICS_FILE = "data/log_topics.json"


class LogManager:
    def __init__(self, bot: Bot, log_group_id: Optional[int]):
        self.bot = bot
        self.log_group_id = log_group_id
        self.topics = self._load_topics()
        
    def _load_topics(self) -> dict:
        """بارگذاری Topic ID های ذخیره شده"""
        if os.path.exists(TOPICS_FILE):
            try:
                with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading topics: {e}")
        return {}
    
    def _save_topics(self):
        """ذخیره Topic ID ها"""
        os.makedirs(os.path.dirname(TOPICS_FILE), exist_ok=True)
        try:
            with open(TOPICS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.topics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving topics: {e}")
    
    async def ensure_topics(self):
        """ایجاد یا بازیابی Topic‌ها"""
        if not self.log_group_id:
            logger.warning("Log group ID not set!")
            return
        
        from config.admin_config import TOPIC_EMOJIS
        
        topic_configs = {
            "system": f"{TOPIC_EMOJIS['system']} سیستم",
            "users": f"{TOPIC_EMOJIS['users']} کاربران",
            "economy": f"{TOPIC_EMOJIS['economy']} اقتصاد",
            "war": f"{TOPIC_EMOJIS['war']} جنگ",
            "admin": f"{TOPIC_EMOJIS['admin']} ادمین",
            "backup": f"{TOPIC_EMOJIS['backup']} بکاپ",
            "security": f"{TOPIC_EMOJIS['security']} امنیت",
        }
        
        for topic_key, topic_name in topic_configs.items():
            # اگه Topic از قبل وجود داره، چک کن هنوز معتبره
            if topic_key in self.topics:
                topic_id = self.topics[topic_key]
                # تست ارسال پیام برای اطمینان از معتبر بودن
                try:
                    # فقط در صورت نیاز تست کن (برای اولین بار)
                    continue
                except TelegramError:
                    logger.warning(f"Topic {topic_key} invalid, recreating...")
                    del self.topics[topic_key]
            
            # ایجاد Topic جدید
            if topic_key not in self.topics:
                try:
                    result = await self.bot.create_forum_topic(
                        chat_id=self.log_group_id,
                        name=topic_name
                    )
                    self.topics[topic_key] = result.message_thread_id
                    self._save_topics()
                    logger.info(f"Created topic: {topic_name} (ID: {result.message_thread_id})")
                except TelegramError as e:
                    logger.error(f"Failed to create topic {topic_name}: {e}")
    
    async def log(self, topic: str, message: str, parse_mode: Optional[str] = None):
        """ارسال لاگ به Topic مشخص"""
        if not self.log_group_id or topic not in self.topics:
            logger.warning(f"Cannot log to topic '{topic}' - not configured")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_message = f"🕐 {timestamp}\n\n{message}"
            
            await self.bot.send_message(
                chat_id=self.log_group_id,
                message_thread_id=self.topics[topic],
                text=full_message,
                parse_mode=parse_mode
            )
        except TelegramError as e:
            logger.error(f"Failed to send log to topic {topic}: {e}")
    
    async def log_system(self, message: str):
        """لاگ سیستم"""
        await self.log("system", f"⚙️ {message}")
    
    async def log_user_action(self, user_id: int, username: str, action: str):
        """لاگ عملیات کاربر"""
        msg = f"👤 کاربر: <code>{user_id}</code> (@{username or 'بدون یوزرنیم'})\n📌 عملیات: {action}"
        await self.log("users", msg, parse_mode="HTML")
    
    async def log_economy(self, user_id: int, action: str, amount: int, item: str = ""):
        """لاگ اقتصادی"""
        msg = f"💰 کاربر: <code>{user_id}</code>\n📊 عملیات: {action}\n💵 مقدار: {amount:,}"
        if item:
            msg += f"\n🎯 آیتم: {item}"
        await self.log("economy", msg, parse_mode="HTML")
    
    async def log_war(self, attacker_id: int, target_id: int, missile: str, result: str):
        """لاگ جنگ"""
        msg = (
            f"⚔️ حمله‌کننده: <code>{attacker_id}</code>\n"
            f"🛡️ مدافع: <code>{target_id}</code>\n"
            f"🚀 موشک: {missile}\n"
            f"📊 نتیجه: {result}"
        )
        await self.log("war", msg, parse_mode="HTML")
    
    async def log_admin_action(self, admin_id: int, action: str, target: str = ""):
        """لاگ عملیات ادمین"""
        msg = f"🔐 ادمین: <code>{admin_id}</code>\n⚡ عملیات: {action}"
        if target:
            msg += f"\n🎯 هدف: {target}"
        await self.log("admin", msg, parse_mode="HTML")
    
    async def log_security(self, user_id: int, issue: str, details: str = ""):
        """لاگ امنیتی"""
        msg = (
            f"🚨 هشدار امنیتی\n"
            f"👤 کاربر: <code>{user_id}</code>\n"
            f"⚠️ مشکل: {issue}"
        )
        if details:
            msg += f"\n📝 جزئیات: {details}"
        await self.log("security", msg, parse_mode="HTML")
    
    async def send_backup(self, file_path: str, caption: str = ""):
        """ارسال فایل بکاپ"""
        if not self.log_group_id or "backup" not in self.topics:
            logger.warning("Cannot send backup - topic not configured")
            return
        
        try:
            with open(file_path, 'rb') as f:
                await self.bot.send_document(
                    chat_id=self.log_group_id,
                    message_thread_id=self.topics["backup"],
                    document=f,
                    caption=caption or "💾 بکاپ خودکار دیتابیس"
                )
            logger.info(f"Backup sent: {file_path}")
        except Exception as e:
            logger.error(f"Failed to send backup: {e}")


# نمونه سینگلتون
_log_manager_instance = None

def init_log_manager(bot: Bot, log_group_id: Optional[int]):
    global _log_manager_instance
    _log_manager_instance = LogManager(bot, log_group_id)
    return _log_manager_instance

def get_log_manager() -> Optional[LogManager]:
    return _log_manager_instance
