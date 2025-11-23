# config/admin_config.py
"""
تنظیمات ادمین پنل و سیستم لاگینگ
"""

import os

# ==================== Admin Settings ====================
ADMIN_IDS = [
8093292086
]

SUPER_ADMIN_IDS = [8093292086]

# ==================== Log Group Settings ====================
LOG_GROUP_ID = os.getenv("LOG_GROUP_ID", None)  # ID گروه لاگ (با - در اول)

# Topic IDs - اینا رو بات خودش می‌سازه و ذخیره می‌کنه
LOG_TOPICS = {
    "system": None,      # لاگ‌های سیستم (شروع، توقف، خطا)
    "users": None,       # لاگ‌های کاربری (ثبت‌نام، ورود)
    "economy": None,     # لاگ‌های اقتصادی (خرید، فروش، تراکنش)
    "war": None,         # لاگ‌های جنگ
    "admin": None,       # لاگ‌های عملیات ادمین
    "backup": None,      # بکاپ‌های خودکار
    "security": None,    # لاگ‌های امنیتی (تقلب، بن)
}

# Emoji برای Topic‌ها
TOPIC_EMOJIS = {
    "system": "⚙️",
    "users": "👥",
    "economy": "💰",
    "war": "⚔️",
    "admin": "🔐",
    "backup": "💾",
    "security": "🛡️",
}

# ==================== Backup Settings ====================
BACKUP_INTERVAL = 6 * 60 * 60  # 6 ساعت (به ثانیه)
BACKUP_PATH = "backups/"

# ==================== Admin Panel Settings ====================
ITEMS_PER_PAGE = 10  # تعداد آیتم در هر صفحه

# ==================== Permissions ====================
PERMISSIONS = {
    "super_admin": ["all"],  # دسترسی به همه چیز
    "admin": [
        "view_users", "edit_users", "ban_users",
        "view_economy", "send_rewards", 
        "view_stats", "manage_events",
        "backup", "maintenance"
    ],
    "moderator": [
        "view_users", "ban_users", 
        "view_stats"
    ]
}
