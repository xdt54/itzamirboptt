from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_armory_list, get_armory_meta, get_armory_count,
    upgrade_armory as db_upgrade_armory,
    get_armory_upgrade_price
)
from keyboards.menus import armory_markup, main_markup
from utils.logger import logger


async def show_armory_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧰 گزینه‌های زرادخانه:",
        reply_markup=armory_markup
    )


async def view_armory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    weapons = get_armory_list(user_id)
    level, capacity = get_armory_meta(user_id)
    total = get_armory_count(user_id)
    
    if not weapons:
        await update.message.reply_text(
            "🧰 زرادخانه شما خالی است.",
            reply_markup=armory_markup
        )
    else:
        lines = [f"• {weapon}: {amount}" for (weapon, amount) in weapons]
        message = (
            "🧰 زرادخانه شما:\n\n" +
            "\n".join(lines) +
            f"\n\n📊 جمع کل تسلیحات: {total}\n"
            f"📦 ظرفیت: {total}/{capacity}\n"
            f"⭐ سطح: {level}"
        )
        await update.message.reply_text(message, reply_markup=armory_markup)
    
    logger.info(f"User {user_id} viewed armory ({total}/{capacity})")


async def upgrade_armory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    current_level, current_capacity = get_armory_meta(user_id)
    price = get_armory_upgrade_price(current_level)
    
    success, new_level, new_capacity = db_upgrade_armory(user_id)
    
    if success:
        await update.message.reply_text(
            f"🎉 زرادخانه شما ارتقا یافت!\n\n"
            f"⭐ سطح جدید: {new_level}\n"
            f"📦 ظرفیت جدید: {new_capacity}\n"
            f"💰 هزینه شده: {price} سکه",
            reply_markup=main_markup
        )
    else:
        await update.message.reply_text(
            f"❌ سکه کافی ندارید.\n\n"
            f"💰 قیمت ارتقا به سطح {current_level + 1}: {price} سکه",
            reply_markup=armory_markup
        )
