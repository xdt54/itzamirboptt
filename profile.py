from telegram import Update
from telegram.ext import ContextTypes
from database.models import get_resources, get_armory_meta, is_mining_active, get_armory_count
from utils.logger import logger
from keyboards.menus import main_markup


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    name = user.first_name or "کاربر ناشناس"

    # دریافت داده‌ها از دیتابیس
    iron, silver, coins = get_resources(user_id)
    armory_level, armory_capacity = get_armory_meta(user_id)
    total_armory_used = get_armory_count(user_id)  # ظرفیت پرشده زرادخانه
    mining_level = 2  # فعلاً ثابت تا سیستم ارتقا معدن اضافه بشه
    mining_active = is_mining_active(user_id)

    # وضعیت معدن
    status = "فعال ⌛ (در حال استخراج)" if mining_active else "غیرفعال ❌"

    # متن پروفایل
    profile_text = (
        f"👤 <b>پروفایل شما</b>\n\n"
        f"🪪 <b>نام:</b> {name}\n"
        f"🆔 <b>شناسه:</b> <code>{user_id}</code>\n"
        f"🏅 <b>سطح:</b> (فعلاً سیستم سطح‌بندی فعال نیست)\n\n"
        f"💵 <b>سکه:</b> {coins}\n"
        f"🛠️ <b>آهن:</b> {iron}\n"
        f"⚪ <b>نقره:</b> {silver}\n\n"
        f"⚙️ <b>سطح زرادخانه:</b> {armory_level}\n"
        f"📦 <b>ظرفیت زرادخانه:</b> {total_armory_used} / {armory_capacity}\n\n"
        f"⛏️ <b>سطح معدن:</b> {mining_level}\n"
        f"⛏️ <b>وضعیت معدن:</b> {status}"
    )

    # ارسال پیام
    await update.message.reply_text(
        profile_text,
        parse_mode="HTML",
        reply_markup=main_markup
    )

    logger.info(f"User {user_id} viewed profile.")
