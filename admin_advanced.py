# handlers/admin_advanced.py
"""
قابلیت‌های پیشرفته پنل ادمین
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.db import db
from database.admin_db import get_admin_db
from utils.logger import logger
from utils.log_manager import get_log_manager

# States for conversations
ASK_SEARCH_QUERY = 100
ASK_BROADCAST_MESSAGE = 101
ASK_REWARD_AMOUNT = 102
ASK_USER_ID_EDIT = 103
ASK_EDIT_TYPE = 104
ASK_EDIT_AMOUNT = 105


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
            "SELECT u.user_id, u.username, r.coins, r.iron, r.silver "
            "FROM users u LEFT JOIN resources r ON u.user_id = r.user_id "
            "WHERE u.user_id = ?",
            (user_id,)
        )
    # جستجو با Username
    else:
        username = query_text.replace("@", "")
        user = db.fetchone(
            "SELECT u.user_id, u.username, r.coins, r.iron, r.silver "
            "FROM users u LEFT JOIN resources r ON u.user_id = r.user_id "
            "WHERE u.username = ? COLLATE NOCASE",
            (username,)
        )
    
    if user:
        text = (
            "✅ <b>کاربر پیدا شد</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User ID: <code>{user['user_id']}</code>\n"
            f"📝 Username: @{user['username'] or 'ندارد'}\n\n"
            f"💰 <b>دارایی:</b>\n"
            f"  💵 سکه: <code>{user['coins']:,}</code>\n"
            f"  🛠️ آهن: <code>{user['iron']:,}</code>\n"
            f"  ⚪ نقره: <code>{user['silver']:,}</code>\n\n"
            "برای بازگشت: /admin"
        )
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
