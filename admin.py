# handlers/admin.py
"""
پنل مدیریت (Admin Panel)
"""

import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config.admin_config import SUPER_ADMIN_IDS, PERMISSIONS
from database.admin_db import get_admin_db
from utils.logger import logger
from utils.log_manager import get_log_manager
from database.db import db


# States for conversations
ASK_ADMIN_ID, ASK_GROUP_ID = range(2)
ASK_SEARCH_QUERY, ASK_BROADCAST_MESSAGE, ASK_REWARD_AMOUNT = range(100, 103)
ASK_USER_ID_EDIT, ASK_EDIT_TYPE, ASK_EDIT_AMOUNT = range(103, 106)
ASK_SEARCH_EDIT_AMOUNT = 106  # برای ویرایش از جستجو


def is_super_admin(user_id: int) -> bool:
    """بررسی سوپر ادمین بودن (از کد)"""
    return user_id in SUPER_ADMIN_IDS


def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن (از دیتابیس)"""
    if is_super_admin(user_id):
        return True
    admin_db = get_admin_db()
    return admin_db.is_admin(user_id)


def has_permission(user_id: int, permission: str) -> bool:
    """بررسی دسترسی"""
    if is_super_admin(user_id):
        return True
    
    admin_db = get_admin_db()
    role = admin_db.get_admin_role(user_id)
    
    if role:
        return permission in PERMISSIONS.get(role, [])
    
    return False


# ==================== صفحه اصلی Admin Panel ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل اصلی ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ شما دسترسی به پنل ادمین ندارید!")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            InlineKeyboardButton("💰 مدیریت اقتصاد", callback_data="admin_economy")
        ],
        [
            InlineKeyboardButton("🎪 رویدادها", callback_data="admin_events"),
            InlineKeyboardButton("📊 آمار و گزارشات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings"),
            InlineKeyboardButton("📝 مدیریت محتوا", callback_data="admin_content")
        ],
        [
            InlineKeyboardButton("🔐 امنیت و لاگ", callback_data="admin_security"),
            InlineKeyboardButton("🗄️ بکاپ و بازیابی", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی آمار", callback_data="admin_refresh")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # دریافت آمار سریع
    from database.db import db
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    
    text = (
        "🎮 <b>پنل مدیریت بات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 تعداد کاربران: <code>{total_users:,}</code>\n"
        f"💰 کل سکه‌ها: <code>{total_coins:,}</code>\n\n"
        "🔹 بخش مورد نظر را انتخاب کنید:"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    
    # لاگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_admin_action(
            user_id,
            "ورود به پنل ادمین"
        )


# ==================== بخش مدیریت کاربران ====================

async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کاربران با صفحه‌بندی"""
    query = update.callback_query
    await query.answer()
    
    # گرفتن شماره صفحه از callback_data
    page = 0
    if ":" in query.data:
        page = int(query.data.split(":")[-1])
    
    from database.db import db
    from config.admin_config import ITEMS_PER_PAGE
    
    # تعداد کل کاربران
    total = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # گرفتن کاربران این صفحه
    offset = page * ITEMS_PER_PAGE
    users = db.fetchall(
        "SELECT user_id, username FROM users ORDER BY user_id DESC LIMIT ? OFFSET ?",
        (ITEMS_PER_PAGE, offset)
    )
    
    # ساخت متن
    text = (
        f"📋 <b>لیست کاربران</b> (صفحه {page + 1}/{total_pages})\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 تعداد کل: <code>{total}</code>\n\n"
    )
    
    for i, user in enumerate(users, start=1):
        username = f"@{user['username']}" if user['username'] else "بدون یوزرنیم"
        text += f"{offset + i}. {username} (<code>{user['user_id']}</code>)\n"
    
    # دکمه‌های صفحه‌بندی
    keyboard = []
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️ قبلی", callback_data=f"admin_list_users:{page-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin_noop")
    )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton("بعدی ▶️", callback_data=f"admin_list_users:{page+1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کاربران"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    from datetime import datetime, timedelta
    
    # آمارهای کلی
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    
    # کاربران جدید امروز (فرض: created_at وجود داره، اگر نه همه رو حساب می‌کنیم)
    today = datetime.now().date()
    
    # آمار منابع
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    total_iron = db.fetchone("SELECT SUM(iron) as total FROM resources")['total'] or 0
    total_silver = db.fetchone("SELECT SUM(silver) as total FROM resources")['total'] or 0
    
    # ثروتمندترین کاربر
    richest = db.fetchone(
        "SELECT u.user_id, u.username, r.coins FROM users u "
        "JOIN resources r ON u.user_id = r.user_id "
        "ORDER BY r.coins DESC LIMIT 1"
    )
    
    text = (
        "📊 <b>آمار کاربران</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 تعداد کل کاربران: <code>{total_users}</code>\n\n"
        f"💰 <b>منابع کل:</b>\n"
        f"  💵 سکه: <code>{total_coins:,}</code>\n"
        f"  🛠️ آهن: <code>{total_iron:,}</code>\n"
        f"  ⚪ نقره: <code>{total_silver:,}</code>\n\n"
    )
    
    if richest:
        username = f"@{richest['username']}" if richest['username'] else "بدون یوزرنیم"
        text += f"🏆 ثروتمندترین: {username}\n"
        text += f"   💰 دارایی: <code>{richest['coins']:,}</code> سکه\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def show_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش کاربران برتر"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    # 10 کاربر برتر از نظر سکه
    top_users = db.fetchall(
        "SELECT u.user_id, u.username, r.coins, r.iron, r.silver "
        "FROM users u "
        "JOIN resources r ON u.user_id = r.user_id "
        "ORDER BY r.coins DESC LIMIT 10"
    )
    
    text = (
        "🏆 <b>کاربران برتر</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(top_users, start=1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        username = f"@{user['username']}" if user['username'] else f"User {user['user_id']}"
        text += (
            f"{medal} {username}\n"
            f"   💰 {user['coins']:,} سکه | "
            f"🛠️ {user['iron']:,} آهن | "
            f"⚪ {user['silver']:,} نقره\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def show_banned_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش کاربران بن شده"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    # چک کردن آیا جدول ban وجود داره یا نه
    try:
        banned = db.fetchall(
            "SELECT user_id, username, ban_reason, ban_date FROM banned_users ORDER BY ban_date DESC"
        )
    except:
        # اگر جدول نداشتیم، خالی برمی‌گردونیم
        banned = []
    
    text = (
        "🔒 <b>کاربران بن شده</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if banned:
        text += f"📊 تعداد: <code>{len(banned)}</code>\n\n"
        for user in banned[:10]:  # فقط 10 تا اول
            username = f"@{user['username']}" if user['username'] else f"User {user['user_id']}"
            reason = user.get('ban_reason', 'نامشخص')
            text += f"👤 {username}\n"
            text += f"   ⚠️ دلیل: {reason}\n\n"
    else:
        text += "✅ هیچ کاربری بن نشده است!"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت حالت تعمیر و نگهداری"""
    query = update.callback_query
    
    admin_db = get_admin_db()
    current = admin_db.is_maintenance_mode()
    new_status = not current
    
    admin_db.set_maintenance_mode(new_status)
    
    status_text = "فعال ✅" if new_status else "غیرفعال ❌"
    await query.answer(f"حالت تعمیر و نگهداری: {status_text}", show_alert=True)
    
    # بروزرسانی منوی تنظیمات
    await admin_settings_menu(update, context)


async def show_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت سیستم"""
    query = update.callback_query
    await query.answer()
    
    import psutil
    import platform
    from datetime import datetime
    
    # اطلاعات سیستم
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # اطلاعات بات
    from database.db import db
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    
    text = (
        "📊 <b>وضعیت سیستم</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🖥️ <b>سیستم عامل:</b> {platform.system()} {platform.release()}\n"
        f"🐍 <b>Python:</b> {platform.python_version()}\n\n"
        f"⚡ <b>CPU:</b> {cpu_percent}%\n"
        f"🧠 <b>RAM:</b> {memory.percent}% ({memory.used // (1024**2)} MB / {memory.total // (1024**2)} MB)\n"
        f"💾 <b>Disk:</b> {disk.percent}% ({disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB)\n\n"
        f"👥 <b>کاربران:</b> {total_users}\n"
        f"🕐 <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def optimize_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بهینه‌سازی دیتابیس"""
    query = update.callback_query
    
    try:
        from database.db import db
        with db.get_cursor() as cursor:
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
        
        await query.answer("✅ دیتابیس بهینه‌سازی شد!", show_alert=True)
        
        # لاگ
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(
                query.from_user.id,
                "بهینه‌سازی دیتابیس"
            )
    except Exception as e:
        await query.answer(f"❌ خطا: {str(e)}", show_alert=True)
        logger.error(f"Database optimization error: {e}")


async def clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک‌سازی کش"""
    query = update.callback_query
    
    # این یک تابع ساده است، می‌تونید بسته به نیاز توسعه بدید
    import gc
    gc.collect()
    
    await query.answer("✅ کش پاک شد!", show_alert=True)
    
    # لاگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_admin_action(
            query.from_user.id,
            "پاک‌سازی کش"
        )


# ==================== جستجوی کاربر ====================

async def start_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع جستجوی کاربر"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔍 <b>جستجوی کاربر</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً یکی از موارد زیر را ارسال کنید:\n\n"
        "🔹 User ID (عدد)\n"
        "🔹 Username (@username یا username)\n\n"
        "مثال: <code>123456789</code> یا <code>@john</code>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_SEARCH_QUERY


async def process_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش جستجو"""
    query_text = update.message.text.strip()
    
    # جستجو با User ID
    if query_text.isdigit():
        user_id = int(query_text)
        user = db.fetchone(
            "SELECT u.user_id, u.username, r.coins, r.iron, r.silver, "
            "COALESCE(r.wins, 0) as wins, COALESCE(r.losses, 0) as losses "
            "FROM users u LEFT JOIN resources r ON u.user_id = r.user_id "
            "WHERE u.user_id = ?",
            (user_id,)
        )
    # جستجو با Username
    else:
        username = query_text.replace("@", "")
        user = db.fetchone(
            "SELECT u.user_id, u.username, r.coins, r.iron, r.silver, "
            "COALESCE(r.wins, 0) as wins, COALESCE(r.losses, 0) as losses "
            "FROM users u LEFT JOIN resources r ON u.user_id = r.user_id "
            "WHERE u.username = ? COLLATE NOCASE",
            (username,)
        )
    
    if user:
        # ذخیره اطلاعات کاربر برای عملیات بعدی
        context.user_data['searched_user_id'] = user['user_id']
        
        # دکمه‌های شیشه‌ای برای مدیریت کاربر
        keyboard = [
            [
                InlineKeyboardButton("💰 ویرایش سکه", callback_data=f"usermng_{user['user_id']}_coins"),
                InlineKeyboardButton("🛠️ ویرایش آهن", callback_data=f"usermng_{user['user_id']}_iron")
            ],
            [
                InlineKeyboardButton("⚪ ویرایش نقره", callback_data=f"usermng_{user['user_id']}_silver"),
                InlineKeyboardButton("🔋 ویرایش قدرت", callback_data=f"usermng_{user['user_id']}_power")
            ],
            [
                InlineKeyboardButton("🚫 بن کاربر", callback_data=f"usermng_{user['user_id']}_ban"),
                InlineKeyboardButton("✅ آنبن کاربر", callback_data=f"usermng_{user['user_id']}_unban")
            ],
            [
                InlineKeyboardButton("📊 مشاهده زرادخانه", callback_data=f"usermng_{user['user_id']}_armory"),
                InlineKeyboardButton("⚔️ آمار جنگ", callback_data=f"usermng_{user['user_id']}_warstats")
            ],
            [
                InlineKeyboardButton("🗑️ حذف کاربر", callback_data=f"usermng_{user['user_id']}_delete"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "✅ <b>کاربر پیدا شد</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User ID: <code>{user['user_id']}</code>\n"
            f"📝 Username: @{user['username'] or 'ندارد'}\n\n"
            f"💰 <b>دارایی:</b>\n"
            f"  💵 سکه: <code>{user['coins']:,}</code>\n"
            f"  🛠️ آهن: <code>{user['iron']:,}</code>\n"
            f"  ⚪ نقره: <code>{user['silver']:,}</code>\n\n"
            f"⚔️ <b>آمار جنگ:</b>\n"
            f"  ✅ برد: <code>{user['wins']}</code>\n"
            f"  ❌ باخت: <code>{user['losses']}</code>\n\n"
            "🔽 عملیات مورد نظر را انتخاب کنید:"
        )
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        text = (
            "❌ <b>کاربر پیدا نشد!</b>\n\n"
            "لطفاً User ID یا Username صحیح وارد کنید.\n\n"
            "برای بازگشت: /admin"
        )
        await update.message.reply_text(text, parse_mode="HTML")
    
    return ConversationHandler.END


# ==================== ارسال پیام همگانی ====================

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ارسال پیام همگانی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 <b>ارسال پیام همگانی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ پیام شما به تمام کاربران ارسال خواهد شد!\n\n"
        "لطفاً پیام خود را ارسال کنید:\n"
        "(می‌تونید از HTML استفاده کنید)",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_BROADCAST_MESSAGE


async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام به همه کاربران"""
    message_text = update.message.text
    user_id = update.effective_user.id
    
    # گرفتن لیست کاربران
    users = db.fetchall("SELECT user_id FROM users")
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text(
        f"⏳ در حال ارسال به {len(users)} کاربر...\n"
        "لطفاً صبر کنید..."
    )
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 <b>پیام از ادمین:</b>\n\n{message_text}",
                parse_mode="HTML"
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.debug(f"Failed to send to {user['user_id']}: {e}")
    
    # لاگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_admin_action(
            user_id,
            f"ارسال پیام همگانی: {success_count} موفق، {fail_count} ناموفق"
        )
    
    await update.message.reply_text(
        f"✅ <b>ارسال کامل شد!</b>\n\n"
        f"✅ موفق: {success_count}\n"
        f"❌ ناموفق: {fail_count}\n\n"
        f"برای بازگشت: /admin",
        parse_mode="HTML"
    )
    
    return ConversationHandler.END


# ==================== پاداش همگانی ====================

async def start_broadcast_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع اعطای پاداش همگانی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎁 <b>پاداش همگانی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "مقدار سکه را وارد کنید:\n"
        "(این مقدار به تمام کاربران داده می‌شود)\n\n"
        "مثال: <code>1000</code>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_REWARD_AMOUNT


async def process_broadcast_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اعطای پاداش به همه"""
    amount_text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if not amount_text.isdigit():
        await update.message.reply_text(
            "❌ لطفاً فقط عدد وارد کنید!\n\n"
            "مثال: <code>1000</code>",
            parse_mode="HTML"
        )
        return ASK_REWARD_AMOUNT
    
    amount = int(amount_text)
    
    if amount <= 0:
        await update.message.reply_text("❌ مقدار باید بیشتر از 0 باشد!")
        return ASK_REWARD_AMOUNT
    
    # اعطای پاداش به همه
    users = db.fetchall("SELECT user_id FROM users")
    
    await update.message.reply_text(
        f"⏳ در حال اعطای {amount:,} سکه به {len(users)} کاربر...\n"
        "لطفاً صبر کنید..."
    )
    
    with db.get_cursor() as cursor:
        cursor.execute(
            "UPDATE resources SET coins = coins + ?",
            (amount,)
        )
    
    # ارسال پیام به کاربران
    success_count = 0
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"🎁 شما {amount:,} سکه پاداش دریافت کردید! 🎉"
            )
            success_count += 1
        except:
            pass
    
    # لاگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_admin_action(
            user_id,
            f"پاداش همگانی: {amount:,} سکه به {len(users)} کاربر"
        )
    
    await update.message.reply_text(
        f"✅ <b>پاداش اعطا شد!</b>\n\n"
        f"💰 مقدار: {amount:,} سکه\n"
        f"👥 تعداد: {len(users)} کاربر\n"
        f"📢 اطلاع‌رسانی: {success_count} نفر\n\n"
        f"برای بازگشت: /admin",
        parse_mode="HTML"
    )
    
    return ConversationHandler.END


# ==================== ویرایش دارایی کاربر ====================

async def start_direct_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش مستقیم دارایی"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_economy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💸 <b>اصلاح مستقیم دارایی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "User ID کاربر را وارد کنید:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_USER_ID_EDIT


async def ask_edit_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب نوع ویرایش"""
    user_id_text = update.message.text.strip()
    
    if not user_id_text.isdigit():
        await update.message.reply_text("❌ User ID باید عدد باشد!")
        return ASK_USER_ID_EDIT
    
    target_user_id = int(user_id_text)
    
    # بررسی وجود کاربر
    user = db.fetchone("SELECT user_id, username FROM users WHERE user_id = ?", (target_user_id,))
    
    if not user:
        await update.message.reply_text("❌ کاربر پیدا نشد!")
        return ASK_USER_ID_EDIT
    
    # ذخیره در context
    context.user_data['edit_target_user'] = target_user_id
    
    keyboard = [
        [
            InlineKeyboardButton("💵 سکه", callback_data="edit_coins"),
            InlineKeyboardButton("🛠️ آهن", callback_data="edit_iron")
        ],
        [
            InlineKeyboardButton("⚪ نقره", callback_data="edit_silver"),
            InlineKeyboardButton("❌ لغو", callback_data="admin_economy")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    username = f"@{user['username']}" if user['username'] else f"User {target_user_id}"
    
    await update.message.reply_text(
        f"👤 کاربر: {username}\n\n"
        f"کدام دارایی را ویرایش می‌کنید؟",
        reply_markup=reply_markup
    )
    
    return ASK_EDIT_TYPE


async def ask_edit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پرسش مقدار ویرایش"""
    query = update.callback_query
    await query.answer()
    
    edit_type = query.data.replace("edit_", "")
    context.user_data['edit_type'] = edit_type
    
    type_emoji = {
        "coins": "💵 سکه",
        "iron": "🛠️ آهن",
        "silver": "⚪ نقره"
    }
    
    await query.edit_message_text(
        f"ویرایش {type_emoji.get(edit_type, edit_type)}\n\n"
        f"مقدار جدید را وارد کنید:\n"
        f"(برای اضافه کردن از + استفاده کنید)\n\n"
        f"مثال: <code>5000</code> یا <code>+1000</code>",
        parse_mode="HTML"
    )
    
    return ASK_EDIT_AMOUNT


async def process_edit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اعمال ویرایش"""
    amount_text = update.message.text.strip()
    user_id = update.effective_user.id
    
    target_user = context.user_data.get('edit_target_user')
    edit_type = context.user_data.get('edit_type')
    
    # پردازش مقدار
    is_add = amount_text.startswith('+')
    amount_text = amount_text.replace('+', '').replace('-', '')
    
    if not amount_text.isdigit():
        await update.message.reply_text("❌ مقدار باید عدد باشد!")
        return ASK_EDIT_AMOUNT
    
    amount = int(amount_text)
    
    # اعمال تغییرات
    with db.get_cursor() as cursor:
        if is_add:
            cursor.execute(
                f"UPDATE resources SET {edit_type} = {edit_type} + ? WHERE user_id = ?",
                (amount, target_user)
            )
            action = "افزایش"
        else:
            cursor.execute(
                f"UPDATE resources SET {edit_type} = ? WHERE user_id = ?",
                (amount, target_user)
            )
            action = "تنظیم"
    
    # لاگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_admin_action(
            user_id,
            f"{action} {edit_type} کاربر {target_user}: {amount:,}"
        )
    
    type_emoji = {
        "coins": "💵",
        "iron": "🛠️",
        "silver": "⚪"
    }
    
    await update.message.reply_text(
        f"✅ <b>ویرایش انجام شد!</b>\n\n"
        f"👤 کاربر: <code>{target_user}</code>\n"
        f"{type_emoji.get(edit_type, '')} {edit_type}: {action} به {amount:,}\n\n"
        f"برای بازگشت: /admin",
        parse_mode="HTML"
    )
    
    return ConversationHandler.END


# ==================== تنظیم قیمت‌ها ====================

async def show_price_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات قیمت"""
    query = update.callback_query
    await query.answer()
    
    from handlers.shop import CRUISE_PRICES, BALLISTIC_PRICES
    
    text = (
        "💰 <b>تنظیم قیمت‌ها</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "قیمت‌های فعلی:\n\n"
        "💥 <b>موشک‌های کروز:</b>\n"
    )
    
    for name, price in list(CRUISE_PRICES.items())[:3]:
        text += f"  • {name}: {price:,} سکه\n"
    
    text += "\n🎯 <b>موشک‌های بالستیک:</b>\n"
    for name, price in list(BALLISTIC_PRICES.items())[:3]:
        text += f"  • {name}: {price:,} سکه\n"
    
    text += (
        "\n\n💡 برای تغییر قیمت‌ها:\n"
        "فایل <code>handlers/shop.py</code> را ویرایش کنید."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_economy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== لیست گزارشات ====================

async def show_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش گزارشات کاربران"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚠️ <b>گزارشات کاربران</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "در حال حاضر سیستم گزارش‌گیری فعال نیست.\n\n"
        "برای فعال‌سازی این قابلیت:\n"
        "1. جدول reports در دیتابیس ایجاد شود\n"
        "2. فرم گزارش به بات اضافه شود\n"
        "3. سیستم مدیریت گزارشات پیاده‌سازی شود\n\n"
        "این قابلیت به زودی اضافه خواهد شد."
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی مدیریت کاربران"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user"),
            InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_user_stats")
        ],
        [
            InlineKeyboardButton("🏆 کاربران برتر", callback_data="admin_top_users"),
            InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_list_users:0")
        ],
        [
            InlineKeyboardButton("🎁 پاداش همگانی", callback_data="admin_broadcast_reward"),
            InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("🔒 کاربران بن شده", callback_data="admin_banned_users"),
            InlineKeyboardButton("⚠️ گزارشات کاربران", callback_data="admin_reports")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "👥 <b>مدیریت کاربران</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 عملیات مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== بخش مدیریت اقتصاد ====================

async def admin_economy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی مدیریت اقتصاد"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    # آمار اقتصادی
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    total_iron = db.fetchone("SELECT SUM(iron) as total FROM resources")['total'] or 0
    total_silver = db.fetchone("SELECT SUM(silver) as total FROM resources")['total'] or 0
    
    keyboard = [
        [
            InlineKeyboardButton("💰 تنظیم قیمت‌ها", callback_data="admin_set_prices"),
            InlineKeyboardButton("🛡️ تنظیم قدرت سلاح", callback_data="admin_set_power")
        ],
        [
            InlineKeyboardButton("📈 نمودار اقتصاد", callback_data="admin_economy_chart"),
            InlineKeyboardButton("🏦 تراکنش‌ها", callback_data="admin_transactions")
        ],
        [
            InlineKeyboardButton("🎁 ایجاد کد هدیه", callback_data="admin_create_code"),
            InlineKeyboardButton("🎟️ مدیریت کدها", callback_data="admin_manage_codes")
        ],
        [
            InlineKeyboardButton("⚡ تنظیم تخفیف", callback_data="admin_set_discount"),
            InlineKeyboardButton("💸 اصلاح مستقیم", callback_data="admin_direct_edit")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "💰 <b>مدیریت اقتصاد</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 کل سکه‌ها: <code>{total_coins:,}</code>\n"
        f"🛠️ کل آهن: <code>{total_iron:,}</code>\n"
        f"⚪ کل نقره: <code>{total_silver:,}</code>\n\n"
        "🔹 عملیات مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== بخش رویدادها ====================

async def admin_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی مدیریت رویدادها"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("🎯 ایجاد رویداد", callback_data="admin_create_event"),
            InlineKeyboardButton("📋 رویدادهای فعال", callback_data="admin_active_events")
        ],
        [
            InlineKeyboardButton("👹 فعال‌سازی باس", callback_data="admin_spawn_boss"),
            InlineKeyboardButton("🏆 ایجاد تورنمنت", callback_data="admin_create_tournament")
        ],
        [
            InlineKeyboardButton("⏱️ برنامه‌ریزی", callback_data="admin_schedule_event"),
            InlineKeyboardButton("🎁 تنظیم پاداش", callback_data="admin_event_rewards")
        ],
        [
            InlineKeyboardButton("📊 آمار رویدادها", callback_data="admin_event_stats"),
            InlineKeyboardButton("❌ پایان رویداد", callback_data="admin_end_event")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🎪 <b>مدیریت رویدادها</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 عملیات مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== بخش آمار ====================

async def admin_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی آمار و گزارشات"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [
            InlineKeyboardButton("📈 آمار امروز", callback_data="admin_stats_today"),
            InlineKeyboardButton("📊 آمار هفته", callback_data="admin_stats_week")
        ],
        [
            InlineKeyboardButton("💹 نمودار فعالیت", callback_data="admin_activity_chart"),
            InlineKeyboardButton("⚔️ آمار جنگ‌ها", callback_data="admin_war_stats")
        ],
        [
            InlineKeyboardButton("🏅 لیدربرد", callback_data="admin_leaderboard"),
            InlineKeyboardButton("🏛️ آمار کلن‌ها", callback_data="admin_clan_stats")
        ],
        [
            InlineKeyboardButton("📉 بررسی اقتصاد", callback_data="admin_economy_analysis"),
            InlineKeyboardButton("🔥 محبوب‌ترین آیتم‌ها", callback_data="admin_popular_items")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "📊 <b>آمار و گزارشات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 نوع آمار را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== بخش تنظیمات ====================

async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی تنظیمات سیستم"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not has_permission(user_id, "maintenance"):
        await query.answer("❌ شما دسترسی به این بخش ندارید!", show_alert=True)
        return
    
    admin_db = get_admin_db()
    log_group = admin_db.get_log_group()
    maintenance = admin_db.is_maintenance_mode()
    
    keyboard = [
        [
            InlineKeyboardButton("🔧 حالت تعمیر", callback_data="admin_toggle_maintenance"),
            InlineKeyboardButton("🧹 پاک‌سازی کش", callback_data="admin_clear_cache")
        ],
        [
            InlineKeyboardButton("⚡ بهینه‌سازی DB", callback_data="admin_optimize_db"),
            InlineKeyboardButton("📊 وضعیت سیستم", callback_data="admin_system_status")
        ],
        [
            InlineKeyboardButton("📢 ارسال اعلان", callback_data="admin_send_announcement"),
            InlineKeyboardButton("🎨 تنظیم پیام‌ها", callback_data="admin_edit_messages")
        ],
        [
            InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data="admin_manage_admins"),
            InlineKeyboardButton("📍 تنظیم گروه لاگ", callback_data="admin_set_log_group")
        ],
        [
            InlineKeyboardButton("⚙️ پیکربندی بات", callback_data="admin_bot_config")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    log_status = f"✅ {log_group}" if log_group else "❌ تنظیم نشده"
    maintenance_status = "🔴 فعال" if maintenance else "🟢 غیرفعال"
    
    text = (
        "⚙️ <b>تنظیمات سیستم</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 گروه لاگ: <code>{log_status}</code>\n"
        f"🔧 حالت تعمیر: {maintenance_status}\n\n"
        "🔹 عملیات مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


# ==================== بخش بکاپ ====================

# ==================== بخش بکاپ ====================

async def admin_backup_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی مدیریت بکاپ"""
    query = update.callback_query
    await query.answer()
    
    import os
    from datetime import datetime
    
    # بررسی فایل‌های بکاپ
    backup_dir = "backups/"
    backup_files = []
    if os.path.exists(backup_dir):
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        backup_files.sort(reverse=True)
    
    last_backup = backup_files[0] if backup_files else "هیچ بکاپی وجود ندارد"
    
    keyboard = [
        [
            InlineKeyboardButton("💾 بکاپ فوری", callback_data="admin_backup_now"),
            InlineKeyboardButton("📋 لیست بکاپ‌ها", callback_data="admin_backup_list")
        ],
        [
            InlineKeyboardButton("📤 ارسال دیتابیس", callback_data="admin_backup_send"),
            InlineKeyboardButton("🗑️ حذف بکاپ‌های قدیمی", callback_data="admin_backup_cleanup")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🗄️ <b>بکاپ و بازیابی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💾 آخرین بکاپ: <code>{last_backup}</code>\n"
        f"📊 تعداد بکاپ‌ها: <code>{len(backup_files)}</code>\n"
        f"⏱️ فاصله بکاپ خودکار: <code>6 ساعت</code>\n\n"
        "🔹 عملیات مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def backup_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ایجاد بکاپ فوری"""
    query = update.callback_query
    
    try:
        from utils.backup_manager import get_backup_manager
        backup_manager = get_backup_manager()
        
        if backup_manager:
            await query.answer("⏳ در حال ایجاد بکاپ...", show_alert=False)
            
            # ایجاد بکاپ
            backup_file = backup_manager.create_backup()
            
            # ارسال به گروه لاگ
            log_manager = get_log_manager()
            if log_manager:
                await log_manager.send_backup(backup_file, "💾 بکاپ دستی")
            
            await query.answer("✅ بکاپ با موفقیت ایجاد شد!", show_alert=True)
            
            # لاگ
            if log_manager:
                await log_manager.log_admin_action(
                    query.from_user.id,
                    "ایجاد بکاپ دستی"
                )
        else:
            await query.answer("❌ سیستم بکاپ در دسترس نیست!", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ خطا: {str(e)}", show_alert=True)
        logger.error(f"Backup error: {e}")
    
    # بازگشت به منوی بکاپ
    await admin_backup_menu(update, context)


async def show_backup_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست بکاپ‌ها"""
    query = update.callback_query
    await query.answer()
    
    import os
    from datetime import datetime
    
    backup_dir = "backups/"
    backup_files = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db'):
                filepath = os.path.join(backup_dir, filename)
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                backup_files.append({
                    'name': filename,
                    'size': size,
                    'time': datetime.fromtimestamp(mtime)
                })
        
        backup_files.sort(key=lambda x: x['time'], reverse=True)
    
    text = (
        "📋 <b>لیست بکاپ‌ها</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if backup_files:
        for i, backup in enumerate(backup_files[:10], start=1):
            size_mb = backup['size'] / (1024 * 1024)
            time_str = backup['time'].strftime('%Y-%m-%d %H:%M')
            text += f"{i}. <code>{backup['name']}</code>\n"
            text += f"   📊 {size_mb:.2f} MB | 🕐 {time_str}\n\n"
    else:
        text += "❌ هیچ بکاپی یافت نشد!"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_backup")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def cleanup_old_backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف بکاپ‌های قدیمی"""
    query = update.callback_query
    
    try:
        from utils.backup_manager import get_backup_manager
        backup_manager = get_backup_manager()
        
        if backup_manager:
            deleted_count = backup_manager.cleanup_old_backups(keep_last=10)
            await query.answer(f"✅ {deleted_count} بکاپ قدیمی حذف شد!", show_alert=True)
            
            # لاگ
            log_manager = get_log_manager()
            if log_manager:
                await log_manager.log_admin_action(
                    query.from_user.id,
                    f"حذف {deleted_count} بکاپ قدیمی"
                )
        else:
            await query.answer("❌ سیستم بکاپ در دسترس نیست!", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ خطا: {str(e)}", show_alert=True)
        logger.error(f"Cleanup error: {e}")
    
    # بازگشت به منوی بکاپ
    await admin_backup_menu(update, context)


async def send_backup_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال فایل بکاپ به ادمین"""
    query = update.callback_query
    await query.answer()
    
    try:
        import os
        from datetime import datetime
        
        # مسیر دیتابیس
        db_path = "users.db"
        
        if not os.path.exists(db_path):
            await query.edit_message_text(
                "❌ فایل دیتابیس پیدا نشد!",
                parse_mode="HTML"
            )
            return
        
        file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        
        await query.edit_message_text(
            f"⏳ در حال ارسال بکاپ...\n"
            f"📦 حجم: {file_size:.2f} MB",
            parse_mode="HTML"
        )
        
        # ارسال فایل
        with open(db_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                caption=(
                    f"📦 <b>بکاپ دیتابیس</b>\n"
                    f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"💾 حجم: {file_size:.2f} MB"
                ),
                parse_mode="HTML"
            )
        
        # لاگ
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(
                query.from_user.id,
                f"دانلود بکاپ دیتابیس ({file_size:.2f} MB)"
            )
        
        await query.message.reply_text(
            "✅ بکاپ با موفقیت ارسال شد!\n\n"
            "برای بازگشت: /admin",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await query.message.reply_text(
            f"❌ خطا در ارسال بکاپ:\n<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        logger.error(f"Backup send error: {e}")


async def handle_user_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مقدار ویرایش از جستجوی کاربر"""
    if 'edit_target_user' not in context.user_data or 'edit_type' not in context.user_data:
        return
    
    amount_text = update.message.text.strip()
    target_user = context.user_data.get('edit_target_user')
    edit_type = context.user_data.get('edit_type')
    admin_id = update.effective_user.id
    
    # بررسی /start برای لغو
    if amount_text.startswith('/'):
        context.user_data.clear()
        return
    
    # پردازش مقدار
    is_add = amount_text.startswith('+')
    amount_text = amount_text.replace('+', '').replace('-', '')
    
    if not amount_text.isdigit():
        await update.message.reply_text("❌ مقدار باید عدد باشد!")
        return
    
    amount = int(amount_text)
    
    # اعمال تغییرات
    try:
        with db.get_cursor() as cursor:
            if is_add:
                cursor.execute(
                    f"UPDATE resources SET {edit_type} = {edit_type} + ? WHERE user_id = ?",
                    (amount, target_user)
                )
                action = "افزایش"
            else:
                cursor.execute(
                    f"UPDATE resources SET {edit_type} = ? WHERE user_id = ?",
                    (amount, target_user)
                )
                action = "تنظیم"
        
        # لاگ
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(
                admin_id,
                f"{action} {edit_type} کاربر {target_user}: {amount:,}"
            )
        
        type_emoji = {
            "coins": "💵",
            "iron": "🛠️",
            "silver": "⚪",
            "power": "🔋"
        }
        
        emoji = type_emoji.get(edit_type, "📝")
        
        await update.message.reply_text(
            f"✅ <b>عملیات موفق!</b>\n\n"
            f"{emoji} {action} {edit_type}\n"
            f"👤 کاربر: <code>{target_user}</code>\n"
            f"🔢 مقدار: <code>{amount:,}</code>\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )
        
        # پاک کردن context
        context.user_data.pop('edit_target_user', None)
        context.user_data.pop('edit_type', None)
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ویرایش:\n<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        logger.error(f"Edit error: {e}")


# ==================== Handler اصلی Callbacks ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های ادمین پنل"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    data = query.data
    
    # مسیریابی به بخش‌های مختلف
    if data == "admin_users":
        await admin_users_menu(update, context)
    elif data == "admin_economy":
        await admin_economy_menu(update, context)
    elif data == "admin_events":
        await admin_events_menu(update, context)
    elif data == "admin_stats":
        await admin_stats_menu(update, context)
    elif data == "admin_settings":
        await admin_settings_menu(update, context)
    elif data == "admin_backup":
        await admin_backup_menu(update, context)
    elif data == "admin_manage_admins":
        await show_manage_admins(update, context)
    elif data == "admin_set_log_group":
        return await start_set_log_group(update, context)
    elif data == "admin_back":
        # بازگشت به صفحه اصلی
        await admin_panel_callback(update, context)
    elif data == "admin_refresh":
        # بروزرسانی
        await admin_panel_callback(update, context)
        await query.answer("✅ آمار بروزرسانی شد!")
    elif data.startswith("admin_add_admin"):
        return await start_add_admin(update, context)
    elif data.startswith("admin_remove_admin_"):
        user_to_remove = int(data.split("_")[-1])
        await remove_admin_confirm(update, context, user_to_remove)


# ==================== مدیریت ادمین‌ها ====================

async def show_manage_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست ادمین‌ها"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط سوپر ادمین می‌تواند ادمین‌ها را مدیریت کند!", show_alert=True)
        return
    
    admin_db = get_admin_db()
    admins = admin_db.get_all_admins()
    
    keyboard = [[InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="admin_add_admin")]]
    
    for admin in admins:
        role_emoji = "👑" if admin['role'] == "super_admin" else "⭐" if admin['role'] == "admin" else "👤"
        username = f"@{admin['username']}" if admin['username'] else "بدون یوزرنیم"
        keyboard.append([
            InlineKeyboardButton(
                f"{role_emoji} {username} ({admin['user_id']})",
                callback_data=f"admin_remove_admin_{admin['user_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "👥 <b>مدیریت ادمین‌ها</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 تعداد ادمین‌ها: <code>{len(admins)}</code>\n\n"
        "🔹 برای حذف، روی ادمین کلیک کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def start_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند اضافه کردن ادمین"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_manage_admins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👤 <b>اضافه کردن ادمین جدید</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📝 لطفاً User ID عددی ادمین جدید را ارسال کنید:\n\n"
        "💡 برای دریافت User ID:\n"
        "  • به @userinfobot پیام بدهید\n"
        "  • User ID شما نمایش داده می‌شود",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_ADMIN_ID


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ID ادمین جدید"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ لطفاً فقط عدد وارد کنید!\n\n"
            "مثال: <code>123456789</code>",
            parse_mode="HTML"
        )
        return ASK_ADMIN_ID
    
    new_admin_id = int(text)
    
    if new_admin_id == user_id:
        await update.message.reply_text("❌ شما خودتان سوپر ادمین هستید!")
        return ConversationHandler.END
    
    # اضافه کردن به دیتابیس
    admin_db = get_admin_db()
    success = admin_db.add_admin(
        user_id=new_admin_id,
        username="",
        role="admin",
        added_by=user_id
    )
    
    if success:
        admin_db.log_admin_action(user_id, f"اضافه کردن ادمین", str(new_admin_id))
        
        # لاگ
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(
                user_id,
                f"اضافه کردن ادمین جدید: {new_admin_id}"
            )
        
        await update.message.reply_text(
            f"✅ <b>ادمین جدید اضافه شد!</b>\n\n"
            f"👤 User ID: <code>{new_admin_id}</code>\n"
            f"⭐ نقش: Admin\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ خطا در اضافه کردن ادمین!")
    
    return ConversationHandler.END


async def remove_admin_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_id: int):
    """تایید حذف ادمین"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_super_admin(user_id):
        await query.answer("❌ فقط سوپر ادمین می‌تواند ادمین‌ها را حذف کند!", show_alert=True)
        return
    
    admin_db = get_admin_db()
    success = admin_db.remove_admin(admin_id)
    
    if success:
        admin_db.log_admin_action(user_id, f"حذف ادمین", str(admin_id))
        await query.answer("✅ ادمین حذف شد!", show_alert=True)
        
        # لاگ
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(
                user_id,
                f"حذف ادمین: {admin_id}"
            )
    else:
        await query.answer("❌ خطا در حذف ادمین!", show_alert=True)
    
    # نمایش مجدد لیست
    await show_manage_admins(update, context)


# ==================== تنظیم گروه لاگ ====================

async def start_set_log_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تنظیم گروه لاگ"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_super_admin(user_id):
        await query.answer("❌ فقط سوپر ادمین می‌تواند گروه لاگ را تنظیم کند!", show_alert=True)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="admin_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📍 <b>تنظیم گروه لاگ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📝 لطفاً Group ID عددی گروه لاگ را ارسال کنید:\n\n"
        "💡 نحوه دریافت Group ID:\n"
        "1. بات @userinfobot را به گروه اضافه کنید\n"
        "2. یک پیام بفرستید\n"
        "3. Group ID با <code>-</code> شروع می‌شود\n"
        "   مثال: <code>-1001234567890</code>\n\n"
        "⚠️ توجه:\n"
        "  • بات باید Admin گروه باشد\n"
        "  • Topics باید فعال باشد",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return ASK_GROUP_ID


async def receive_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ID گروه لاگ"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # بررسی فرمت
    if not text.lstrip('-').isdigit():
        await update.message.reply_text(
            "❌ فرمت نادرست!\n\n"
            "Group ID باید عدد باشد و با <code>-</code> شروع شود\n"
            "مثال: <code>-1001234567890</code>",
            parse_mode="HTML"
        )
        return ASK_GROUP_ID
    
    group_id = int(text)
    
    if group_id > 0:
        await update.message.reply_text(
            "❌ Group ID باید منفی باشد!\n\n"
            "مثال: <code>-1001234567890</code>",
            parse_mode="HTML"
        )
        return ASK_GROUP_ID
    
    # ذخیره در دیتابیس
    admin_db = get_admin_db()
    success = admin_db.set_log_group(group_id)
    
    if success:
        admin_db.log_admin_action(user_id, f"تنظیم گروه لاگ", str(group_id))
        
        # راه‌اندازی مجدد log manager
        from utils.log_manager import init_log_manager
        log_manager = init_log_manager(context.bot, group_id)
        
        try:
            # ایجاد Topic ها
            await log_manager.ensure_topics()
            await log_manager.log_system("🟢 گروه لاگ جدید تنظیم شد")
            
            await update.message.reply_text(
                f"✅ <b>گروه لاگ تنظیم شد!</b>\n\n"
                f"📍 Group ID: <code>{group_id}</code>\n"
                f"✅ Topic ها ایجاد شدند\n\n"
                f"برای بازگشت: /admin",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error setting up log group: {e}")
            await update.message.reply_text(
                f"⚠️ گروه تنظیم شد اما خطا در ایجاد Topic ها:\n\n"
                f"<code>{str(e)}</code>\n\n"
                f"مطمئن شوید:\n"
                f"  • بات Admin گروه است\n"
                f"  • Topics فعال است\n\n"
                f"برای بازگشت: /admin",
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text("❌ خطا در تنظیم گروه!")
    
    return ConversationHandler.END


# ==================== توابع اضافی Admin ====================

async def show_set_power_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیم قدرت سلاح‌ها"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🚀 قدرت موشک‌ها", callback_data="power_missiles")],
        [InlineKeyboardButton("🛡️ قدرت پدافندها", callback_data="power_defenses")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_economy")]
    ]
    
    await query.edit_message_text(
        "⚙️ <b>تنظیم قدرت سلاح‌ها</b>\n\n"
        "⚠️ این قسمت به زودی فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تراکنش‌های اخیر"""
    query = update.callback_query
    await query.answer()
    
    # لاگ‌های اخیر admin
    admin_db = get_admin_db()
    logs = admin_db.get_recent_logs(limit=20)
    
    if not logs:
        text = "📋 <b>تراکنش‌های اخیر</b>\n\n" "هیچ تراکنشی ثبت نشده است."
    else:
        text = "📋 <b>تراکنش‌های اخیر</b>\n" "━━━━━━━━━━━━━━━━━━\n\n"
        for log in logs[:15]:
            text += f"• {log[2]} | {log[3]}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_economy")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def start_create_gift_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ایجاد کد هدیه"""
    query = update.callback_query
    await query.answer("⚠️ این قسمت به زودی فعال می‌شود!", show_alert=True)


async def show_manage_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کدهای هدیه"""
    query = update.callback_query
    await query.answer("⚠️ این قسمت به زودی فعال می‌شود!", show_alert=True)


async def show_stats_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار امروز"""
    query = update.callback_query
    await query.answer()
    
    from datetime import datetime, timedelta
    from database.db import db
    
    # کل کاربران
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    
    # کل جنگ‌ها (برد + باخت)
    total_wins = db.fetchone("SELECT SUM(wins) as total FROM resources")['total'] or 0
    total_losses = db.fetchone("SELECT SUM(losses) as total FROM resources")['total'] or 0
    total_wars = total_wins + total_losses
    
    # کل سکه‌ها
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    
    text = (
        "📊 <b>آمار کلی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 کل کاربران: <code>{total_users}</code>\n"
        f"💰 کل سکه‌ها: <code>{total_coins:,}</code>\n"
        f"⚔️ کل جنگ‌ها: <code>{total_wars}</code>\n"
        f"  ✅ برد: <code>{total_wins}</code>\n"
        f"  ❌ باخت: <code>{total_losses}</code>\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_stats_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار هفته"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    total_wins = db.fetchone("SELECT SUM(wins) as total FROM resources")['total'] or 0
    
    text = (
        "📊 <b>آمار هفته</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 کل کاربران: <code>{total_users}</code>\n"
        f"💰 کل سکه‌ها: <code>{total_coins:,}</code>\n"
        f"⚔️ کل پیروزی‌ها: <code>{total_wins}</code>\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_war_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار جنگ‌ها"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    total_wins = db.fetchone("SELECT SUM(wins) as total FROM resources")['total'] or 0
    total_losses = db.fetchone("SELECT SUM(losses) as total FROM resources")['total'] or 0
    total_wars = total_wins + total_losses
    
    # بهترین جنگجو
    best_warrior = db.fetchone(
        "SELECT u.user_id, u.username, r.wins FROM users u "
        "JOIN resources r ON u.user_id = r.user_id "
        "ORDER BY r.wins DESC LIMIT 1"
    )
    
    text = (
        "⚔️ <b>آمار جنگ‌ها</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 کل جنگ‌ها: <code>{total_wars}</code>\n"
        f"✅ کل پیروزی‌ها: <code>{total_wins}</code>\n"
        f"❌ کل شکست‌ها: <code>{total_losses}</code>\n\n"
    )
    
    if best_warrior:
        username = best_warrior['username'] or "ناشناس"
        text += f"🏆 بهترین جنگجو: @{username} ({best_warrior['wins']} برد)\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_economy_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحلیل اقتصادی"""
    query = update.callback_query
    await query.answer()
    
    from database.db import db
    
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    total_iron = db.fetchone("SELECT SUM(iron) as total FROM resources")['total'] or 0
    total_silver = db.fetchone("SELECT SUM(silver) as total FROM resources")['total'] or 0
    avg_coins = db.fetchone("SELECT AVG(coins) as avg FROM resources")['avg'] or 0
    
    # ثروتمندترین کاربر
    richest = db.fetchone(
        "SELECT u.user_id, u.username, r.coins FROM users u "
        "JOIN resources r ON u.user_id = r.user_id "
        "ORDER BY r.coins DESC LIMIT 1"
    )
    
    text = (
        "💰 <b>تحلیل اقتصادی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 کل سکه‌ها: <code>{total_coins:,}</code>\n"
        f"⚒️ کل آهن: <code>{total_iron:,}</code>\n"
        f"🥈 کل نقره: <code>{total_silver:,}</code>\n"
        f"📊 میانگین سکه: <code>{int(avg_coins):,}</code>\n\n"
    )
    
    if richest:
        username = richest['username'] or "ناشناس"
        text += f"👑 ثروتمندترین: @{username} ({richest['coins']:,} سکه)\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def start_send_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال اطلاعیه (مشابه broadcast اما با قالب متفاوت)"""
    return await start_broadcast(update, context)


# ==================== مدیریت کاربر از جستجو ====================

async def handle_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت عملیات روی کاربر پیدا شده"""
    query = update.callback_query
    await query.answer()
    
    data = query.data  # usermng_{user_id}_{action}
    parts = data.split("_")
    
    if len(parts) < 3:
        await query.answer("❌ خطا در پردازش!", show_alert=True)
        return
    
    target_user_id = int(parts[1])
    action = parts[2]
    
    admin_id = query.from_user.id
    
    if action in ["coins", "iron", "silver", "power"]:
        # ویرایش دارایی
        context.user_data['edit_target_user'] = target_user_id
        context.user_data['edit_type'] = action
        
        type_names = {
            "coins": "💰 سکه",
            "iron": "🛠️ آهن",
            "silver": "⚪ نقره",
            "power": "🔋 قدرت"
        }
        
        await query.message.reply_text(
            f"✏️ <b>ویرایش {type_names[action]}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 کاربر: <code>{target_user_id}</code>\n\n"
            f"لطفاً مقدار جدید را وارد کنید:\n"
            f"• برای افزایش: <code>+100</code>\n"
            f"• برای تنظیم مستقیم: <code>500</code>\n\n"
            f"برای لغو: /start",
            parse_mode="HTML"
        )
    
    elif action == "ban":
        # بن کاربر
        # TODO: نیاز به جدول bans در دیتابیس
        with db.get_cursor() as cursor:
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY, banned_at REAL, reason TEXT)"
            )
            cursor.execute(
                "INSERT OR REPLACE INTO banned_users (user_id, banned_at, reason) VALUES (?, ?, ?)",
                (target_user_id, time.time(), f"Banned by admin {admin_id}")
            )
        
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(admin_id, f"🚫 بن کاربر {target_user_id}")
        
        await query.edit_message_text(
            f"✅ کاربر <code>{target_user_id}</code> بن شد!\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )
    
    elif action == "unban":
        # آنبن کاربر
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (target_user_id,))
        
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(admin_id, f"✅ آنبن کاربر {target_user_id}")
        
        await query.edit_message_text(
            f"✅ کاربر <code>{target_user_id}</code> آنبن شد!\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )
    
    elif action == "armory":
        # نمایش زرادخانه
        from database.models import get_armory_list
        armory = get_armory_list(target_user_id)
        
        if not armory:
            text = f"📦 زرادخانه کاربر <code>{target_user_id}</code> خالی است!"
        else:
            text = f"📦 <b>زرادخانه کاربر {target_user_id}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            for item in armory:
                text += f"• {item['weapon_name']}: <code>{item['quantity']}</code>\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "warstats":
        # آمار جنگ
        user = db.fetchone(
            "SELECT wins, losses, power FROM resources WHERE user_id = ?",
            (target_user_id,)
        )
        
        if user:
            total_wars = user['wins'] + user['losses']
            win_rate = (user['wins'] / total_wars * 100) if total_wars > 0 else 0
            
            text = (
                f"⚔️ <b>آمار جنگ کاربر {target_user_id}</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ برد: <code>{user['wins']}</code>\n"
                f"❌ باخت: <code>{user['losses']}</code>\n"
                f"📊 کل جنگ‌ها: <code>{total_wars}</code>\n"
                f"🎯 نرخ برد: <code>{win_rate:.1f}%</code>\n"
                f"🔋 قدرت: <code>{user['power']}</code>\n"
            )
        else:
            text = "❌ اطلاعات کاربر یافت نشد!"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "delete":
        # حذف کاربر
        keyboard = [
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_delete_{target_user_id}"),
                InlineKeyboardButton("❌ لغو", callback_data="admin_users")
            ]
        ]
        
        await query.edit_message_text(
            f"⚠️ <b>هشدار!</b>\n\n"
            f"آیا مطمئن هستید که می‌خواهید کاربر <code>{target_user_id}</code> را حذف کنید؟\n\n"
            f"⚠️ این عمل برگشت‌ناپذیر است!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید حذف کاربر"""
    query = update.callback_query
    await query.answer()
    
    data = query.data  # confirm_delete_{user_id}
    target_user_id = int(data.split("_")[2])
    admin_id = query.from_user.id
    
    try:
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id = ?", (target_user_id,))
            cursor.execute("DELETE FROM resources WHERE user_id = ?", (target_user_id,))
            cursor.execute("DELETE FROM armory WHERE user_id = ?", (target_user_id,))
            cursor.execute("DELETE FROM armory_meta WHERE user_id = ?", (target_user_id,))
        
        log_manager = get_log_manager()
        if log_manager:
            await log_manager.log_admin_action(admin_id, f"🗑️ حذف کاربر {target_user_id}")
        
        await query.edit_message_text(
            f"✅ کاربر <code>{target_user_id}</code> با موفقیت حذف شد!\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )
    except Exception as e:
        await query.edit_message_text(
            f"❌ خطا در حذف کاربر:\n<code>{str(e)}</code>\n\n"
            f"برای بازگشت: /admin",
            parse_mode="HTML"
        )


# ==================== Handler اصلی Callbacks ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های ادمین پنل"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    data = query.data
    
    # مسیریابی به بخش‌های اصلی
    if data == "admin_users":
        await admin_users_menu(update, context)
    elif data == "admin_economy":
        await admin_economy_menu(update, context)
    elif data == "admin_events":
        await admin_events_menu(update, context)
    elif data == "admin_stats":
        await admin_stats_menu(update, context)
    elif data == "admin_settings":
        await admin_settings_menu(update, context)
    elif data == "admin_backup":
        await admin_backup_menu(update, context)
    elif data == "admin_manage_admins":
        await show_manage_admins(update, context)
    elif data == "admin_set_log_group":
        return await start_set_log_group(update, context)
    elif data == "admin_back":
        await admin_panel_callback(update, context)
    elif data == "admin_refresh":
        await admin_panel_callback(update, context)
        await query.answer("✅ آمار بروزرسانی شد!")
    elif data.startswith("admin_add_admin"):
        return await start_add_admin(update, context)
    elif data.startswith("admin_remove_admin_"):
        user_to_remove = int(data.split("_")[-1])
        await remove_admin_confirm(update, context, user_to_remove)
    
    # ==================== مدیریت کاربر از جستجو ====================
    elif data.startswith("usermng_"):
        await handle_user_management(update, context)
    elif data.startswith("confirm_delete_"):
        await confirm_delete_user(update, context)
    
    # ==================== لیست کاربران ====================
    elif data.startswith("admin_list_users"):
        await show_user_list(update, context)
    elif data == "admin_noop":
        await query.answer()  # فقط dismiss می‌کنه
    
    # ==================== آمار کاربران ====================
    elif data == "admin_user_stats":
        await show_user_stats(update, context)
    elif data == "admin_top_users":
        await show_top_users(update, context)
    elif data == "admin_banned_users":
        await show_banned_users(update, context)
    elif data == "admin_search_user":
        return await start_search_user(update, context)
    elif data == "admin_broadcast":
        return await start_broadcast(update, context)
    elif data == "admin_broadcast_reward":
        return await start_broadcast_reward(update, context)
    elif data == "admin_reports":
        await show_reports(update, context)
    
    # ==================== اقتصاد ====================
    elif data == "admin_set_prices":
        await show_price_settings(update, context)
    elif data == "admin_direct_edit":
        return await start_direct_edit(update, context)
    elif data.startswith("edit_"):
        return await ask_edit_amount(update, context)
    
    # ==================== تنظیمات سیستم ====================
    elif data == "admin_toggle_maintenance":
        await toggle_maintenance(update, context)
    elif data == "admin_system_status":
        await show_system_status(update, context)
    elif data == "admin_optimize_db":
        await optimize_database(update, context)
    elif data == "admin_clear_cache":
        await clear_cache(update, context)
    
    # ==================== بکاپ ====================
    elif data == "admin_backup_now":
        await backup_now(update, context)
    elif data == "admin_backup_list":
        await show_backup_list(update, context)
    elif data == "admin_backup_cleanup":
        await cleanup_old_backups(update, context)
    elif data == "admin_backup_send":
        await send_backup_file(update, context)
    
    # ==================== زیرمنوهای دیگر ====================
    elif data == "admin_set_power":
        await show_set_power_menu(update, context)
    elif data == "admin_transactions":
        await show_transactions(update, context)
    elif data == "admin_create_code":
        await start_create_gift_code(update, context)
    elif data == "admin_manage_codes":
        await show_manage_codes(update, context)
    elif data == "admin_stats_today":
        await show_stats_today(update, context)
    elif data == "admin_stats_week":
        await show_stats_week(update, context)
    elif data == "admin_war_stats":
        await show_war_stats(update, context)
    elif data == "admin_economy_analysis":
        await show_economy_analysis(update, context)
    elif data == "admin_send_announcement":
        return await start_send_announcement(update, context)
    
    # باقی اپشن‌های موقت
    elif data in [
        "admin_economy_chart", "admin_set_discount",
        "admin_create_event", "admin_active_events", "admin_spawn_boss",
        "admin_create_tournament", "admin_schedule_event", "admin_event_rewards",
        "admin_event_stats", "admin_end_event",
        "admin_activity_chart", "admin_leaderboard", "admin_clan_stats",
        "admin_popular_items", "admin_edit_messages", "admin_content", "admin_security",
        "admin_backup_download", "admin_backup_settings", "admin_backup_stats"
    ]:
        # این‌ها به زودی اضافه میشن
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]
        await query.edit_message_text(
            "⚠️ <b>این قسمت در حال توسعه است</b>\n\n"
            "🔜 به زودی قابلیت‌های زیر اضافه می‌شود:\n"
            "• نمودار اقتصادی\n"
            "• سیستم رویدادها\n"
            "• تورنمنت‌ها\n"
            "• کدهای تخفیف\n"
            "• و بیشتر...\n\n"
            "منتظر آپدیت بعدی باشید! 🚀",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query.answer("❓ دستور ناشناخته!", show_alert=True)


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پنل اصلی از طریق callback"""
    query = update.callback_query
    
    keyboard = [
        [
            InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            InlineKeyboardButton("💰 مدیریت اقتصاد", callback_data="admin_economy")
        ],
        [
            InlineKeyboardButton("🎪 رویدادها", callback_data="admin_events"),
            InlineKeyboardButton("📊 آمار و گزارشات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings"),
            InlineKeyboardButton("📝 مدیریت محتوا", callback_data="admin_content")
        ],
        [
            InlineKeyboardButton("🔐 امنیت و لاگ", callback_data="admin_security"),
            InlineKeyboardButton("🗄️ بکاپ و بازیابی", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی آمار", callback_data="admin_refresh")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    from database.db import db
    total_users = db.fetchone("SELECT COUNT(*) as count FROM users")['count']
    total_coins = db.fetchone("SELECT SUM(coins) as total FROM resources")['total'] or 0
    
    text = (
        "🎮 <b>پنل مدیریت بات</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 تعداد کاربران: <code>{total_users:,}</code>\n"
        f"💰 کل سکه‌ها: <code>{total_coins:,}</code>\n\n"
        "🔹 بخش مورد نظر را انتخاب کنید:"
    )
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
