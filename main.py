from telegram import Update
from telegram.ext import ContextTypes

from database.models import add_user, get_resources
from keyboards.menus import main_markup, get_main_keyboard
from utils.logger import logger
from utils.log_manager import get_log_manager
from config.admin_config import SUPER_ADMIN_IDS
from database.admin_db import get_admin_db


def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن کاربر"""
    # بررسی سوپر ادمین
    if user_id in SUPER_ADMIN_IDS:
        return True
    # بررسی ادمین از دیتابیس
    admin_db = get_admin_db()
    return admin_db.is_admin(user_id)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    chat = update.effective_chat
    
    # کنسل کردن کانورسیشن قبلی اگر وجود داره
    context.user_data.clear()
    
    # ثبت کاربر
    is_new = add_user(user_id, username)
    
    # لاگ کاربر جدید
    if is_new:
        log_manager = get_log_manager()
        if log_manager:
            username_display = f"@{username}" if username else "❌ بدون یوزرنیم"
            await log_manager.log_user_action(
                user_id,
                username_display,
                f"✅ کاربر جدید | ID: {user_id} | Username: {username_display}"
            )
    
    if chat.type != "private":
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "🤖✨ سلام به همه اعضای گروه!\n\n"
                "برای اینکه بات بتونه درست کار کنه:\n"
                "🔹 لطفاً به من <b>دسترسی ادمین</b> بدین.\n"
                "🔹 مخصوصاً دسترسی ارسال پیام و پاسخ دادن به پیام‌ها.\n\n"
                "⚙️ بدون این دسترسی‌ها بعضی قابلیت‌ها غیرفعال می‌شن."
            ),
            parse_mode="HTML"
        )
        logger.info(f"Bot added to group {chat.id}")
    else:
        # کیبورد بر اساس نقش کاربر
        keyboard = get_main_keyboard(is_admin=is_admin(user_id))
        
        await update.message.reply_text(
            "🌟 خوش‌آمدید به ربات بازی اقتصادی!\nاز دکمه‌ها استفاده کنید:",
            reply_markup=keyboard
        )
        logger.info(f"/start by user {user_id} in private chat")


async def welcome_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    new_status = update.my_chat_member.new_chat_member.status
    
    if new_status in ("member", "administrator"):
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "🤖✨ سلام به همه اعضای گروه!\n\n"
                "برای اینکه بات بتونه درست کار کنه:\n"
                "🔹 لطفاً به من <b>دسترسی ادمین</b> بدین.\n"
                "🔹 مخصوصاً دسترسی ارسال پیام و پاسخ دادن به پیام‌ها.\n\n"
                "⚙️ بدون این دسترسی‌ها بعضی قابلیت‌ها غیرفعال می‌شن."
            ),
            parse_mode="HTML"
        )


async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    
    await update.message.reply_text(
        f"💰 دارایی‌های شما:\n"
        f"🛠️ آهن: {iron}\n"
        f"⚪ نقره: {silver}\n"
        f"💵 سکه: {coins}",
        reply_markup=main_markup
    )
    logger.info(f"User {user_id} viewed inventory")
