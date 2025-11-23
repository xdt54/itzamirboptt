# utils/backup_manager.py
"""
مدیریت بکاپ خودکار دیتابیس
"""

import os
import shutil
import asyncio
from datetime import datetime
from typing import Optional
from utils.logger import logger


class BackupManager:
    def __init__(self, db_path: str, backup_dir: str, interval: int):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.interval = interval  # به ثانیه
        self.task: Optional[asyncio.Task] = None
        
        # ایجاد دایرکتوری بکاپ
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self) -> Optional[str]:
        """ایجاد بکاپ از دیتابیس"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # کپی فایل دیتابیس
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def cleanup_old_backups(self, keep_last: int = 10):
        """پاک‌سازی بکاپ‌های قدیمی"""
        try:
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")],
                reverse=True
            )
            
            # حذف بکاپ‌های اضافی
            for backup in backups[keep_last:]:
                backup_path = os.path.join(self.backup_dir, backup)
                os.remove(backup_path)
                logger.info(f"Deleted old backup: {backup}")
        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
    
    async def auto_backup_loop(self):
        """حلقه بکاپ خودکار"""
        from utils.log_manager import get_log_manager
        
        logger.info(f"Auto backup started (interval: {self.interval}s)")
        
        while True:
            try:
                await asyncio.sleep(self.interval)
                
                # ایجاد بکاپ
                backup_path = self.create_backup()
                
                if backup_path:
                    # پاک‌سازی بکاپ‌های قدیمی
                    self.cleanup_old_backups(keep_last=10)
                    
                    # ارسال به گروه لاگ
                    log_manager = get_log_manager()
                    if log_manager:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        caption = f"💾 بکاپ خودکار\n🕐 {timestamp}"
                        await log_manager.send_backup(backup_path, caption)
                    
                    logger.info("Auto backup completed successfully")
            except Exception as e:
                logger.error(f"Error in auto backup loop: {e}")
    
    def start(self):
        """شروع بکاپ خودکار"""
        if self.task is None or self.task.done():
            loop = asyncio.get_event_loop()
            self.task = loop.create_task(self.auto_backup_loop())
            logger.info("Backup manager started")
    
    def stop(self):
        """توقف بکاپ خودکار"""
        if self.task and not self.task.done():
            self.task.cancel()
            logger.info("Backup manager stopped")


# نمونه سینگلتون
_backup_manager_instance = None

def init_backup_manager(db_path: str, backup_dir: str, interval: int):
    global _backup_manager_instance
    _backup_manager_instance = BackupManager(db_path, backup_dir, interval)
    return _backup_manager_instance

def get_backup_manager() -> Optional[BackupManager]:
    return _backup_manager_instance
