# bot_with_armory_upgrade.py
import os
import sys
import time
import sqlite3
import asyncio
import logging
from typing import Tuple

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, ChatMemberHandler)

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


# ---------------- Config ----------------
TOKEN = ("8414150184:AAGYLR7lZ59EQtzGMjSA8bZ2vE0Jdgrn5Tk") or "YOUR_BOT_TOKEN_HERE"

# ---------------- Logging (English, colored) ----------------
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',   # Blue
        'INFO': '\033[92m',    # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[95m' # Magenta
    }
    RESET = '\033[0m'
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        formatted = f"{timestamp} | {record.levelname:<7} | {record.name:<15} | {record.getMessage()}"
        return f"{color}{formatted}{self.RESET}"

logger = logging.getLogger("telegram_bot")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(ColorFormatter())
logger.handlers.clear()
logger.addHandler(ch)

# ---------------- Database ----------------
DB_PATH = "users.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# create required tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS resources (
    user_id INTEGER PRIMARY KEY,
    iron INTEGER DEFAULT 0,
    silver INTEGER DEFAULT 0,
    coins INTEGER DEFAULT 0,
    mining_started INTEGER DEFAULT 0,
    last_iron REAL DEFAULT 0,
    last_silver REAL DEFAULT 0,
    last_daily REAL DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS armory (
    user_id INTEGER,
    weapon TEXT,
    amount INTEGER DEFAULT 0,
    PRIMARY KEY(user_id, weapon)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS armory_meta (
    user_id INTEGER PRIMARY KEY,
    level INTEGER DEFAULT 1,
    capacity INTEGER DEFAULT 5
)
""")
conn.commit()

# ---------------- DB helpers ----------------
def user_exists(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def add_user(user_id: int):
    if not user_exists(user_id):
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO resources (user_id) VALUES (?)", (user_id,))
        # ensure armory_meta row
        cursor.execute("INSERT OR IGNORE INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)",
                       (user_id, 1, 5))
        conn.commit()
        logger.info(f"New user added: {user_id}")
        
        # ---------------- Mining helpers ----------------
def start_mining_db(user_id: int):
    now = time.time()
    cursor.execute("UPDATE resources SET mining_started=1, last_iron=?, last_silver=? WHERE user_id=?",
                   (now, now, user_id))
    conn.commit()
    logger.info(f"Mining started for {user_id}")

def mining_active_db(user_id: int) -> bool:
    cursor.execute("SELECT mining_started FROM resources WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return bool(row and row[0] == 1)


def get_resources(user_id: int) -> Tuple[int, int, int]:
    cursor.execute("SELECT iron, silver, coins FROM resources WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0], row[1], row[2]
    return 0,0,0

def add_resources(user_id: int, iron=0, silver=0, coins=0):
    cursor.execute("SELECT iron, silver, coins FROM resources WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        new_iron = row[0] + iron
        new_silver = row[1] + silver
        new_coins = row[2] + coins
        cursor.execute("UPDATE resources SET iron=?, silver=?, coins=? WHERE user_id=?",
                       (new_iron, new_silver, new_coins, user_id))
    else:
        cursor.execute("INSERT OR IGNORE INTO resources (user_id, iron, silver, coins) VALUES (?, ?, ?, ?)",
                       (user_id, iron, silver, coins))
    conn.commit()
    logger.info(f"user {user_id} resources updated: +{iron} iron, +{silver} silver, +{coins} coins")

# ---------------- Armory helpers ----------------
def armory_meta_get(user_id: int) -> Tuple[int, int]:
    cursor.execute("SELECT level, capacity FROM armory_meta WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return int(row[0]), int(row[1])
    # initialize if missing
    cursor.execute("INSERT OR IGNORE INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)", (user_id,1,5))
    conn.commit()
    return 1, 5

def armory_meta_set(user_id: int, level: int, capacity: int):
    cursor.execute("INSERT OR REPLACE INTO armory_meta (user_id, level, capacity) VALUES (?, ?, ?)",
                   (user_id, level, capacity))
    conn.commit()

def armory_count_total(user_id: int) -> int:
    cursor.execute("SELECT SUM(amount) FROM armory WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return int(row[0]) if (row and row[0]) else 0

def add_weapon_to_armory(user_id: int, weapon: str, amount: int = 1) -> bool:
    """
    Try to add weapon(s). Return True if added, False if capacity full.
    """
    level, capacity = armory_meta_get(user_id)
    current = armory_count_total(user_id)
    if current + amount > capacity:
        return False
    cursor.execute("SELECT amount FROM armory WHERE user_id=? AND weapon=?", (user_id, weapon))
    row = cursor.fetchone()
    if row:
        new_amount = row[0] + amount
        cursor.execute("UPDATE armory SET amount=? WHERE user_id=? AND weapon=?", (new_amount, user_id, weapon))
    else:
        cursor.execute("INSERT INTO armory (user_id, weapon, amount) VALUES (?, ?, ?)", (user_id, weapon, amount))
    conn.commit()
    logger.info(f"user {user_id} added weapon {weapon} x{amount} to armory (now {current+amount}/{capacity})")
    return True

def get_armory_list(user_id: int):
    cursor.execute("SELECT weapon, amount FROM armory WHERE user_id=?", (user_id,))
    return cursor.fetchall()

def armory_upgrade_price_for_next_level(current_level: int) -> int:
    """
    Price to upgrade from current_level -> current_level+1.
    Rules:
      - price for upgrade to level 2 = 500
      - each subsequent level price = previous_price * 1.3
    We'll compute price for next level directly: price = round(500 * 1.3^(current_level-1))
    (because current_level=1 -> price=500*1.3^0 = 500)
    """
    base = 500.0
    exponent = max(0, current_level - 1)
    price = base * (1.3 ** exponent)
    return int(round(price))

def upgrade_armory(user_id: int) -> Tuple[bool, int, int]:
    """
    Attempt to upgrade: returns (success, new_level, new_capacity).
    Deduct coins if successful.
    """
    level, capacity = armory_meta_get(user_id)
    price = armory_upgrade_price_for_next_level(level)
    # check coins
    _, _, coins = get_resources(user_id)
    if coins < price:
        logger.info(f"user {user_id} insufficient coins for upgrade: has {coins}, needs {price}")
        return False, level, capacity
    # deduct coins
    add_resources(user_id, coins=-price)
    new_level = level + 1
    new_capacity = capacity + 2
    armory_meta_set(user_id, new_level, new_capacity)
    logger.info(f"user {user_id} upgraded armory to level {new_level}, capacity {new_capacity}, paid {price} coins")
    return True, new_level, new_capacity

# ---------------- Mining loop ----------------
_minig_task_started = False
async def mining_loop():
    global _minig_task_started
    if _minig_task_started:
        logger.warning("Mining loop already started. Skipping duplicate start.")
        return
    _minig_task_started = True
    logger.info("Mining loop started.")
    try:
        while True:
            cursor.execute("SELECT user_id, last_iron, last_silver FROM resources WHERE mining_started=1")
            rows = cursor.fetchall()
            now = time.time()
            for user_id, last_iron, last_silver in rows:
                try:
                    last_iron = last_iron or now
                    last_silver = last_silver or now
                    iron_add = silver_add = 0
                    if now - last_iron >= 600:
                        iron_add = 1
                        last_iron = now
                    if now - last_silver >= 1200:
                        silver_add = 1
                        last_silver = now
                    if iron_add or silver_add:
                        add_resources(user_id, iron=iron_add, silver=silver_add)
                        cursor.execute("UPDATE resources SET last_iron=?, last_silver=? WHERE user_id=?",
                                       (last_iron, last_silver, user_id))
                        conn.commit()
                        logger.info(f"Mining: user {user_id} +{iron_add} iron +{silver_add} silver")
                except Exception as e:
                    logger.exception(f"Error processing mining for user {user_id}: {e}")
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Mining loop cancelled.")
    except Exception as e:
        logger.exception(f"Mining loop crashed: {e}")
    finally:
        _minig_task_started = False
        logger.info("Mining loop stopped.")

# ---------------- Keyboards (Persian) ----------------
main_keyboard = [
    ["💰 دارایی‌ها", "🏪 فروشگاه", "🏭 کارخانه"],
    ["⛏️ معدن", "👥 کلن", "🍀 گردونه"],
    ["🏛️ بانک", "🎁 جایزه روزانه"],
    ["🧰 زرادخانه"]
]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

mine_keyboard = [
    ["⛏️ ورود به معدن", "⚡ ارتقا معدن"],
    ["💎 فروش منابع", "🔙 بازگشت به منوی اصلی"]
]
mine_markup = ReplyKeyboardMarkup(mine_keyboard, resize_keyboard=True)

sell_keyboard = [
    ["🛠️ فروش آهن", "⚪ فروش نقره"],
    ["🔙 بازگشت به معدن"]
]
sell_markup = ReplyKeyboardMarkup(sell_keyboard, resize_keyboard=True)

# store first-level
store_keyboard = [
    ["🚀 موشک"],
    ["🛸 پهپاد"],
    ["✈️ جنگنده"],
    ["🔙 بازگشت به منو"]
]
store_markup = ReplyKeyboardMarkup(store_keyboard, resize_keyboard=True)

# missile categories (single-button rows)
missile_category_keyboard = [
    ["💥 کروز"],
    ["🎯 بالستیک"],
    ["⚡ هایپر سونیک"],
    ["☢️ هسته‌ای"],
    ["🔙 بازگشت به فروشگاه"]
]
missile_category_markup = ReplyKeyboardMarkup(missile_category_keyboard, resize_keyboard=True)

# missile items — each as single-button row
cruise_missiles = [
    ["💥 نور"], ["💥 قدر"], ["💥 سومار"], ["💥 کالیبر"],
    ["💥 زیرکان"], ["💥 تاماهاک"], ["🔙 بازگشت به دسته‌بندی"]
]
ballistic_missiles = [
    ["🎯 شهاب"], ["🎯 سجیل"], ["🎯 خرمشهر"], ["🎯 فاتح-۱۱۰"],
    ["🎯 خیبر شکن"], ["🎯 ذوالفقار"], ["🎯 واردن"], ["🎯 یارس"],
    ["🎯 شیطان"], ["🔙 بازگشت به دسته‌بندی"]
]
hypersonic_missiles = [
    ["⚡ فتاح"], ["⚡ وانگارد"], ["⚡ دانگ فنگ"], ["⚡ هایپر۱"],
    ["⚡ هایپر۲"], ["⚡ هایپر۳"], ["⚡ هایپر۴"], ["⚡ هایپر۵"],
    ["⚡ هایپر۶"], ["🔙 بازگشت به دسته‌بندی"]
]
nuclear_missiles = [
    ["☢️ تزار"], ["☢️ موشک۲"], ["☢️ موشک۳"], ["☢️ موشک۴"],
    ["☢️ موشک۵"], ["☢️ موشک۶"], ["☢️ موشک۷"], ["☢️ موشک۸"],
    ["☢️ موشک۹"], ["🔙 بازگشت به دسته‌بندی"]
]

cruise_markup = ReplyKeyboardMarkup(cruise_missiles, resize_keyboard=True)
ballistic_markup = ReplyKeyboardMarkup(ballistic_missiles, resize_keyboard=True)
hypersonic_markup = ReplyKeyboardMarkup(hypersonic_missiles, resize_keyboard=True)
nuclear_markup = ReplyKeyboardMarkup(nuclear_missiles, resize_keyboard=True)

# drones & fighters placeholders
drone_items = [["🛸 نمونه پهپاد"], ["🔙 بازگشت به فروشگاه"]]
fighter_items = [["🛩️ نمونه جنگنده"], ["🔙 بازگشت به فروشگاه"]]
drone_markup = ReplyKeyboardMarkup(drone_items, resize_keyboard=True)
fighter_markup = ReplyKeyboardMarkup(fighter_items, resize_keyboard=True)

armory_markup = ReplyKeyboardMarkup([["ارتقا زرادخانه", "مشاهده زرادخانه"], ["🔙 بازگشت به منو"]], resize_keyboard=True)

# ---------------- Conversation states ----------------
SELL_IRON, SELL_SILVER = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    add_user(user_id)

    if chat.type != "private":
        # اگر گروه هست، فقط پیام خوش‌آمدگویی مخصوص گروه
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
        # در پیوی، منو اصلی فعال باشد
        await update.message.reply_text(
            "🌟 خوش‌آمدید به ربات بازی اقتصادی!\nاز دکمه‌ها استفاده کنید:", 
            reply_markup=main_markup
        )
        logger.info(f"/start by {user_id} in private chat")


# sell iron handlers
async def start_sell_iron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    await update.message.reply_text(f"💰 موجودی شما:\n🛠️ آهن: {iron}\n⚪ نقره: {silver}\n💵 سکه: {coins}\n\n🛠️ چند عدد آهن می‌خوای بفروشی؟", reply_markup=sell_markup)
    return SELL_IRON

async def sell_iron_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text == "🔙 بازگشت به معدن":
        await update.message.reply_text("بازگشت به معدن.", reply_markup=mine_markup)
        return ConversationHandler.END
    iron, silver, coins = get_resources(user_id)
    if not text.isdigit() or int(text) <= 0 or int(text) > iron:
        await update.message.reply_text("مقدار نامعتبر است.", reply_markup=sell_markup)
        return SELL_IRON
    amount = int(text)
    add_resources(user_id, iron=-amount, coins=amount*10)
    await update.message.reply_text(f"✅ {amount} آهن فروخته شد و {amount*10} سکه دریافت کردید.", reply_markup=mine_markup)
    logger.info(f"user {user_id} sold {amount} iron for {amount*10} coins")
    return ConversationHandler.END

# sell silver
async def start_sell_silver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    iron, silver, coins = get_resources(user_id)
    await update.message.reply_text(f"💰 موجودی شما:\n🛠️ آهن: {iron}\n⚪ نقره: {silver}\n💵 سکه: {coins}\n\n⚪ چند عدد نقره می‌خوای بفروشی؟", reply_markup=sell_markup)
    return SELL_SILVER

async def sell_silver_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text == "🔙 بازگشت به معدن":
        await update.message.reply_text("بازگشت به معدن.", reply_markup=mine_markup)
        return ConversationHandler.END
    iron, silver, coins = get_resources(user_id)
    if not text.isdigit() or int(text) <= 0 or int(text) > silver:
        await update.message.reply_text("مقدار نامعتبر است.", reply_markup=sell_markup)
        return SELL_SILVER
    amount = int(text)
    add_resources(user_id, silver=-amount, coins=amount*20)
    await update.message.reply_text(f"✅ {amount} نقره فروخته شد و {amount*20} سکه دریافت کردید.", reply_markup=mine_markup)
    logger.info(f"user {user_id} sold {amount} silver for {amount*20} coins")
    return ConversationHandler.END

# main message/button handler
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    text = update.message.text.strip()
    add_user(user_id)

    if chat.type != "private":
        # گروه: هیچ دکمه‌ای فعال نباشد
        await update.message.reply_text(
            "🤖✨ سلام به همه اعضای گروه!\n\n"
            "برای اینکه بات بتونه درست کار کنه:\n"
            "🔹 لطفاً به من <b>دسترسی ادمین</b> بدین.\n"
            "🔹 مخصوصاً دسترسی ارسال پیام و پاسخ دادن به پیام‌ها.\n\n"
            "⚙️ بدون این دسترسی‌ها بعضی قابلیت‌ها غیرفعال می‌شن.",
            parse_mode="HTML"
        )
        return

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat = update.effective_chat
    text = update.message.text.strip()
    add_user(user_id)

    if chat.type != "private":
        # گروه: فقط پیام خوش‌آمد/اخطار
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
        return  # توقف ادامه اجرای handle_buttons

    # ادامه کد handle_buttons برای پیوی اینجا قرار می‌گیرد


    # daily reward
    if text == "🎁 جایزه روزانه":
        cursor.execute("SELECT last_daily, coins FROM resources WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        last_daily = row[0] if row else 0
        coins = row[1] if row else 0
        now = time.time()
        if now - last_daily >= 86400:
            cursor.execute("UPDATE resources SET coins=coins+500, last_daily=? WHERE user_id=?", (now, user_id))
            conn.commit()
            await update.message.reply_text("🎉 شما ۵۰۰ سکه جایزه روزانه دریافت کردید.", reply_markup=main_markup)
            logger.info(f"user {user_id} received daily +500 coins")
        else:
            remaining = int(86400 - (now - last_daily))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await update.message.reply_text(f"⏱ جایزه آماده نیست.\nزمان باقی‌مانده: {hours}س {minutes}د", reply_markup=main_markup)
        return

    # inventory
    if text == "💰 دارایی‌ها":
        iron, silver, coins = get_resources(user_id)
        await update.message.reply_text(f"💰 دارایی‌های شما:\nآهن: {iron}\nنقره: {silver}\nسکه: {coins}", reply_markup=main_markup)
        return

    # shop navigation
    if text == "🏪 فروشگاه":
        await update.message.reply_text("🏪 فروشگاه — دسته‌ها:", reply_markup=store_markup)
        return
    if text == "🚀 موشک":
        await update.message.reply_text("🚀 دسته‌بندی موشک‌ها:", reply_markup=missile_category_markup)
        return
    if text == "🛸 پهپاد":
        await update.message.reply_text("🛸 دسته‌بندی پهپادها:", reply_markup=drone_markup)
        return
    if text == "✈️ جنگنده":
        await update.message.reply_text("✈️ دسته‌بندی جنگنده‌ها:", reply_markup=fighter_markup)
        return

    # missile categories -> show items
    if text == "💥 کروز":
        await update.message.reply_text("💥 موشک‌های کروز:", reply_markup=cruise_markup)
        return
    if text == "🎯 بالستیک":
        await update.message.reply_text("🎯 موشک‌های بالستیک:", reply_markup=ballistic_markup)
        return
    if text == "⚡ هایپر سونیک":
        await update.message.reply_text("⚡ موشک‌های هایپر سونیک:", reply_markup=hypersonic_markup)
        return
    if text == "☢️ هسته‌ای":
        await update.message.reply_text("☢️ موشک‌های هسته‌ای:", reply_markup=nuclear_markup)
        return

    # specific missiles/drones/fighters -> attempt to add to armory
    missile_prefixes = ("💥", "🎯", "⚡", "☢️")
    drone_prefix = "🛸"
    fighter_prefix = "🛩️"
    if any(text.startswith(p) for p in missile_prefixes) or text.startswith(drone_prefix) or text.startswith(fighter_prefix):
        added = add_weapon_to_armory(user_id, text, 1)
        if added:
            await update.message.reply_text(f"{text} به زرادخانه شما اضافه شد.", reply_markup=main_markup)
            logger.info(f"user {user_id} added {text} to armory")
        else:
            # capacity full
            level, capacity = armory_meta_get(user_id)
            await update.message.reply_text(
                f"⚠️ ظرفیت زرادخانه پر است ({armory_count_total(user_id)}/{capacity}).\nبرای افزایش ظرفیت، زرادخانه را ارتقا دهید.",
                reply_markup=armory_markup
            )
            logger.info(f"user {user_id} failed to add {text} — armory full ({armory_count_total(user_id)}/{capacity})")
        return

    # mining
    if text == "⛏️ معدن":
        await update.message.reply_text("⛏️ گزینه‌های معدن:", reply_markup=mine_markup)
        return
    if text == "⛏️ ورود به معدن":
        if not mining_active_db(user_id):
            start_mining_db(user_id)
            add_resources(user_id, iron=1, silver=1)
            await update.message.reply_text("⛏️ شما وارد معدن شدید! +1 آهن و +1 نقره\nمنابع به‌صورت خودکار اضافه خواهند شد.", reply_markup=mine_markup)
            logger.info(f"user {user_id} entered mine")
        else:
            await update.message.reply_text("⛏️ معدن شما در حال فعالیت است.", reply_markup=mine_markup)
        return
    if text == "💎 فروش منابع":
        iron, silver, coins = get_resources(user_id)
        await update.message.reply_text(f"آهن: {iron}\nنقره: {silver}\nسکه: {coins}\nچه چیزی می‌خواهید بفروشید؟", reply_markup=sell_markup)
        return

    # armory menu
    if text == "🧰 زرادخانه":
        await update.message.reply_text("🧰 گزینه‌های زرادخانه:", reply_markup=armory_markup)
        return
    if text == "مشاهده زرادخانه":
        weapons = get_armory_list(user_id)
        _, capacity = armory_meta_get(user_id)
        total = armory_count_total(user_id)
        if not weapons:
            await update.message.reply_text("زرادخانه شما خالی است.", reply_markup=armory_markup)
        else:
            lines = [f"{w}: {a}" for (w, a) in weapons]
            msg = "زرادخانه شما:\n" + "\n".join(lines) + f"\n\nجمع کل تسلیحات: {total}\nظرفیت: {total}/{capacity}"
            await update.message.reply_text(msg, reply_markup=armory_markup)
        return
    if text == "ارتقا زرادخانه":
        success, new_level, new_capacity = upgrade_armory(user_id)
        if success:
            await update.message.reply_text(f"🎉 زرادخانه شما ارتقا یافت! سطح جدید: {new_level} — ظرفیت: {new_capacity}", reply_markup=main_markup)
        else:
            price = armory_upgrade_price_for_next_level(armory_meta_get(user_id)[0])
            await update.message.reply_text(f"❌ سکه کافی ندارید. قیمت ارتقا: {price} سکه.", reply_markup=armory_markup)
        return

    # navigation back
    if text in ("🔙 بازگشت به منوی اصلی", "🔙 بازگشت به منو"):
        await update.message.reply_text("بازگشت به منوی اصلی.", reply_markup=main_markup)
        return
    if text in ("🔙 بازگشت به فروشگاه", "🔙 بازگشت به دسته‌بندی"):
        await update.message.reply_text("بازگشت به فروشگاه.", reply_markup=store_markup)
        return
    if text == "🔙 بازگشت به معدن":
        await update.message.reply_text("بازگشت به معدن.", reply_markup=mine_markup)
        return


    await update.message.reply_text(
        "⚠️ دستور ناشناخته. لطفاً از دکمه‌ها استفاده کنید.",
        reply_markup=main_markup
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler_iron = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("🛠️ فروش آهن"), start_sell_iron)],
        states={SELL_IRON: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_iron_step)]},
        fallbacks=[]
    )
    conv_handler_silver = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("⚪ فروش نقره"), start_sell_silver)],
        states={SELL_SILVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_silver_step)]},
        fallbacks=[]
    )

    app.add_handler(ChatMemberHandler(welcome_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler_iron)
    app.add_handler(conv_handler_silver)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    # start mining loop on the event loop used by run_polling
    loop = asyncio.get_event_loop()
    loop.create_task(mining_loop())

    logger.info("Bot starting (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()