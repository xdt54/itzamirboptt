import time
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database.models import (
    add_user, get_resources, add_resources,
    start_mining, is_mining_active
)
from keyboards.menus import mine_markup, sell_markup, main_markup
from config.settings import IRON_SELL_PRICE, SILVER_SELL_PRICE
from utils.logger import logger


SELL_IRON, SELL_SILVER = range(2)


async def show_mine_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⛏️ گزینه‌های معدن:",
        reply_markup=mine_markup
    )


async def enter_mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_mining_active(user_id):
        start_mining(user_id)
        add_resources(user_id, iron=1, silver=1)
        await update.message.reply_text(
            "⛏️ شما وارد معدن شدید! +1 آهن و +1 نقره\n"
            "منابع به‌صورت خودکار اضافه خواهند شد.",
            reply_markup=mine_markup
        )
        logger.info(f"User {user_id} entered mine")
    else:
        await update.message.reply_text(
            "⛏️ معدن شما در حال فعالیت است.",
            reply_markup=mine_markup
        )


async def show_sell_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    
    await update.message.reply_text(
        f"💰 موجودی شما:\n"
        f"🛠️ آهن: {iron}\n"
        f"⚪ نقره: {silver}\n"
        f"💵 سکه: {coins}\n\n"
        f"چه چیزی می‌خواهید بفروشید?",
        reply_markup=sell_markup
    )


async def start_sell_iron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    
    await update.message.reply_text(
        f"💰 موجودی شما:\n"
        f"🛠️ آهن: {iron}\n"
        f"⚪ نقره: {silver}\n"
        f"💵 سکه: {coins}\n\n"
        f"🛠️ چند عدد آهن می‌خوای بفروشی?\n"
        f"(قیمت هر آهن: {IRON_SELL_PRICE} سکه)",
        reply_markup=sell_markup
    )
    return SELL_IRON


async def sell_iron_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text == "🔙 بازگشت به معدن":
        await update.message.reply_text("بازگشت به معدن.", reply_markup=mine_markup)
        return ConversationHandler.END
    
    iron, silver, coins = get_resources(user_id)
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ لطفاً فقط عدد وارد کنید.",
            reply_markup=sell_markup
        )
        return SELL_IRON
    
    amount = int(text)
    
    if amount <= 0:
        await update.message.reply_text(
            "❌ مقدار باید بزرگتر از صفر باشد.",
            reply_markup=sell_markup
        )
        return SELL_IRON
    
    if amount > iron:
        await update.message.reply_text(
            f"❌ شما فقط {iron} آهن دارید.",
            reply_markup=sell_markup
        )
        return SELL_IRON
    
    coins_earned = amount * IRON_SELL_PRICE
    add_resources(user_id, iron=-amount, coins=coins_earned)
    
    await update.message.reply_text(
        f"✅ {amount} آهن فروخته شد و {coins_earned} سکه دریافت کردید.",
        reply_markup=mine_markup
    )
    logger.info(f"User {user_id} sold {amount} iron for {coins_earned} coins")
    
    return ConversationHandler.END


async def start_sell_silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    
    await update.message.reply_text(
        f"💰 موجودی شما:\n"
        f"🛠️ آهن: {iron}\n"
        f"⚪ نقره: {silver}\n"
        f"💵 سکه: {coins}\n\n"
        f"⚪ چند عدد نقره می‌خوای بفروشی?\n"
        f"(قیمت هر نقره: {SILVER_SELL_PRICE} سکه)",
        reply_markup=sell_markup
    )
    return SELL_SILVER


async def sell_silver_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text == "🔙 بازگشت به معدن":
        await update.message.reply_text("بازگشت به معدن.", reply_markup=mine_markup)
        return ConversationHandler.END
    
    iron, silver, coins = get_resources(user_id)
    
    if not text.isdigit():
        await update.message.reply_text(
            "❌ لطفاً فقط عدد وارد کنید.",
            reply_markup=sell_markup
        )
        return SELL_SILVER
    
    amount = int(text)
    
    if amount <= 0:
        await update.message.reply_text(
            "❌ مقدار باید بزرگتر از صفر باشد.",
            reply_markup=sell_markup
        )
        return SELL_SILVER
    
    if amount > silver:
        await update.message.reply_text(
            f"❌ شما فقط {silver} نقره دارید.",
            reply_markup=sell_markup
        )
        return SELL_SILVER
    
    coins_earned = amount * SILVER_SELL_PRICE
    add_resources(user_id, silver=-amount, coins=coins_earned)
    
    await update.message.reply_text(
        f"✅ {amount} نقره فروخته شد و {coins_earned} سکه دریافت کردید.",
        reply_markup=mine_markup
    )
    logger.info(f"User {user_id} sold {amount} silver for {coins_earned} coins")
    
    return ConversationHandler.END
