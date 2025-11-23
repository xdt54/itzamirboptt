from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from datetime import datetime
import os, json
from threading import Lock
from database.db import db
from utils.logger import logger

# ------------------ تنظیمات ------------------
MAX_DAILY_TRANSFER = 2000  # سقف روزانه
MAX_SINGLE_TRANSFER = 2000  # سقف هر تراکنش

# مراحل گفت‌وگو
ASK_AMOUNT, ASK_RECIPIENT, CONFIRM = range(3)

# ------------------ Tracker انتقال روزانه ------------------
_TRACK_FILE = os.path.join(os.path.dirname(__file__), "../data/transfer_log.json")
_LOCK = Lock()
os.makedirs(os.path.dirname(_TRACK_FILE), exist_ok=True)

def _read_log():
    if not os.path.exists(_TRACK_FILE):
        return {}
    try:
        with open(_TRACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _write_log(data):
    with open(_TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_transferred_today(user_id: int) -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _LOCK:
        data = _read_log()
        return data.get(str(user_id), {}).get(today, 0)

def add_transfer(user_id: int, amount: int):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with _LOCK:
        data = _read_log()
        user_data = data.setdefault(str(user_id), {})
        user_data[today] = user_data.get(today, 0) + amount
        _write_log(data)

# ------------------ توابع دیتابیس ------------------

def get_user_by_tg_id(tg_id: int):
    result = db.fetchone("SELECT * FROM resources WHERE user_id = ?", (tg_id,))
    return result

def add_coins(tg_id: int, amount: int):
    db.execute("UPDATE resources SET coins = coins + ? WHERE user_id = ?", (amount, tg_id))
    logger.debug(f"Added {amount} coins to user {tg_id}")

def remove_coins(tg_id: int, amount: int):
    user = db.fetchone("SELECT coins FROM resources WHERE user_id = ?", (tg_id,))
    if not user or user["coins"] < amount:
        return False
    db.execute("UPDATE resources SET coins = coins - ? WHERE user_id = ?", (amount, tg_id))
    logger.debug(f"Removed {amount} coins from user {tg_id}")
    return True

# ------------------ منوی بانک ------------------

async def bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی بانک با موجودی و اطلاعات کاربر"""
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "❌ ندارد"

    result = db.fetchone("SELECT coins FROM resources WHERE user_id = ?", (user_id,))
    balance = result["coins"] if result else 0

    text = (
        "🏦 <b>بانک مرکزی موشکی</b>\n\n"
        f"👤 <b>کاربر:</b> {username}\n"
        f"🆔 <b>شناسه:</b> <code>{user_id}</code>\n"
        f"💰 <b>موجودی:</b> <code>{balance}</code> 💵\n\n"
        "از دکمه زیر برای انتقال وجه استفاده کنید 👇"
    )

    keyboard = [[InlineKeyboardButton("💸 انتقال وجه", callback_data="bank_transfer")]]
    markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# ------------------ فرآیند انتقال وجه ------------------

async def start_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 مقدار سکه‌ای که می‌خواهید انتقال دهید را بنویسید (حداکثر 2000):")
    return ASK_AMOUNT

async def ask_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ لطفاً عدد وارد کنید:")
        return ASK_AMOUNT
    amount = int(text)
    if not (1 <= amount <= MAX_SINGLE_TRANSFER):
        await update.message.reply_text(f"❌ مقدار باید بین 1 تا {MAX_SINGLE_TRANSFER} باشد.")
        return ASK_AMOUNT

    user_id = update.effective_user.id
    transferred = get_transferred_today(user_id)
    if transferred + amount > MAX_DAILY_TRANSFER:
        await update.message.reply_text(
            f"🚫 سقف روزانه ({MAX_DAILY_TRANSFER}) پر شده است.\n"
            f"امروز {transferred} سکه منتقل کرده‌اید."
        )
        return ConversationHandler.END

    context.user_data["amount"] = amount
    await update.message.reply_text("🎯 آیدی عددی کاربری که می‌خواهید به او سکه بدهید را وارد کنید:")
    return ASK_RECIPIENT

async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipient_id = update.message.text.strip()
    if not recipient_id.isdigit():
        await update.message.reply_text("❌ آیدی باید عددی باشد:")
        return ASK_RECIPIENT

    recipient_id = int(recipient_id)
    sender_id = update.effective_user.id
    amount = context.user_data["amount"]

    recipient = get_user_by_tg_id(recipient_id)
    if not recipient:
        await update.message.reply_text("🚫 چنین کاربری در بات ثبت نشده است.")
        return ConversationHandler.END

    context.user_data["recipient"] = recipient_id
    msg = (
        "📜 <b>رسید انتقال</b>\n\n"
        f"👤 فرستنده: <code>{sender_id}</code>\n"
        f"🎯 گیرنده: <code>{recipient_id}</code>\n"
        f"💰 مقدار: <b>{amount}</b> سکه\n\n"
        "آیا تایید می‌کنید؟"
    )
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data="confirm_transfer_yes"),
            InlineKeyboardButton("❌ لغو", callback_data="confirm_transfer_no"),
        ]
    ])
    await update.message.reply_text(msg, reply_markup=markup, parse_mode="HTML")
    return CONFIRM

async def do_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "confirm_transfer_no":
        await query.edit_message_text("❌ انتقال لغو شد.")
        return ConversationHandler.END

    sender_id = query.from_user.id
    recipient_id = context.user_data["recipient"]
    amount = context.user_data["amount"]

    sender = get_user_by_tg_id(sender_id)
    recipient = get_user_by_tg_id(recipient_id)

    if not sender or not recipient:
        await query.edit_message_text("❌ کاربر یافت نشد.")
        return ConversationHandler.END

    if not remove_coins(sender_id, amount):
        await query.edit_message_text("💸 موجودی کافی نیست.")
        return ConversationHandler.END

    add_coins(recipient_id, amount)
    add_transfer(sender_id, amount)

    await query.edit_message_text("✅ انتقال با موفقیت انجام شد.")
    try:
        await context.bot.send_message(recipient_id, f"🎉 {amount} سکه از {sender_id} دریافت کردید!")
    except:
        pass
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END

# ConversationHandler
bank_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_transfer, pattern="^bank_transfer$")],
    states={
        ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_recipient)],
        ASK_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_transfer)],
        CONFIRM: [CallbackQueryHandler(do_transfer, pattern="^confirm_transfer_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Handler برای ورود به منوی بانک
bank_menu_handler = CallbackQueryHandler(bank_menu, pattern="^bank_menu$")
