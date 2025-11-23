import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from database.models import (
    add_user, add_weapon, get_armory_meta, get_armory_count,
    get_user_money, update_user_money
)
from keyboards.menus import (
    store_markup, missile_category_markup,
    cruise_markup, ballistic_markup, hypersonic_markup, nuclear_markup,
    defense_markup, main_markup
)
from utils.logger import logger
from utils.log_manager import get_log_manager


# =============== قیمت‌ها ===============
CRUISE_PRICES = {
    "💥 نور": 60,
    "💥 سومار": int(60 * 1.3),
    "💥 کالیبر": int(60 * 1.3 * 1.2),
    "💥 زیرکان": int(60 * 1.3 * 1.2 * 1.2),
    "💥 تاماهاک": int(60 * 1.3 * 1.2 * 1.2 * 1.2),
}

BALLISTIC_PRICES = {
    "🎯 شهاب": 150,
    "🎯 سجیل": int(150 * 1.3),
    "🎯 خرمشهر": int(150 * 1.3 * 1.3),
    "🎯 فاتح-۱۱۰": int(150 * 1.3 * 1.3 * 1.3),
}

HYPERSONIC_PRICES = {
    "⚡ فتاح": 400,
    "⚡ وانگارد": int(400 * 1.3),
    "⚡ دانگ فنگ": int(400 * 1.3 * 1.3),
    "⚡ هایپر۱": int(400 * 1.3 * 1.3 * 1.3),
}

NUCLEAR_PRICES = {
    "☢️ تزار": 2000,
    "☢️ موشک۲": int(2000 * 1.2),
    "☢️ موشک۳": int(2000 * 1.2 * 1.2),
    "☢️ موشک۴": int(2000 * 1.2 * 1.2 * 1.2),
}

DEFENSE_PRICES = {
    "🪖 مرصاد": 200,
    "🛰️ باور-۳۷۳": 450,
    "☢️ S-300": 400,
    "🛡️ گنبد آهنین": 250,
    "🧨 باراک": 280,
    "🧱 تاد": 380,
    "⚙️ فلاخان داوود": 220,
    "🪖 S-400": 500,
}

PRICES = {}
PRICES.update(CRUISE_PRICES)
PRICES.update(BALLISTIC_PRICES)
PRICES.update(HYPERSONIC_PRICES)
PRICES.update(NUCLEAR_PRICES)
PRICES.update(DEFENSE_PRICES)


# =============== توابع کمکی ===============
def normalize_item_name(s: str) -> str:
    """پاکسازی نام آیتم از کاراکترهای مخفی تلگرام"""
    if not s:
        return s
    s = s.replace("\u3164", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# =============== نمایش منوها ===============
async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏪 فروشگاه — دسته‌ها:", reply_markup=store_markup)


async def show_missile_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 دسته‌بندی موشک‌ها:", reply_markup=missile_category_markup)


async def show_cruise_missiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💥 موشک‌های کروز:", reply_markup=cruise_markup)


async def show_ballistic_missiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 موشک‌های بالستیک:", reply_markup=ballistic_markup)


async def show_hypersonic_missiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚡ موشک‌های هایپر سونیک:", reply_markup=hypersonic_markup)


async def show_nuclear_missiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("☢️ موشک‌های هسته‌ای:", reply_markup=nuclear_markup)


async def show_defense_systems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 پدافندها:", reply_markup=defense_markup)


# =============== مرحله ۱: رسید خرید ===============
async def show_purchase_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, weapon_name: str):
    user_id = update.effective_user.id
    username = update.effective_user.username
    add_user(user_id, username)
    weapon_name = normalize_item_name(weapon_name)

    price = PRICES.get(weapon_name)
    if not price:
        await update.message.reply_text("❌ خطا: قیمت این آیتم یافت نشد.")
        return

    balance = get_user_money(user_id)
    level, capacity = get_armory_meta(user_id)
    current = get_armory_count(user_id)
    free_slots = max(0, capacity - current)
    max_qty = min(balance // price, free_slots)

    if max_qty <= 0:
        await update.message.reply_text(
            f"❌ موجودی کافی یا ظرفیت خالی برای خرید {weapon_name} نداری.",
            reply_markup=main_markup
        )
        return

    # ذخیره وضعیت خرید
    context.user_data["pending_purchase"] = {
        "weapon_name": weapon_name,
        "max_qty": max_qty,
        "price": price
    }

    text = (
        f"🧾 <b>رسید خرید</b>\n"
        f"━━━━━━━━━━━\n"
        f"🚀 نام موشک: {weapon_name}\n"
        f"💰 قیمت واحد: {price} سکه\n"
        f"🏦 موجودی فعلی: {balance} سکه\n"
        f"📦 ظرفیت خالی: {free_slots}\n"
        f"🧮 حداکثر قابل خرید: {max_qty}\n"
        f"━━━━━━━━━━━\n"
        f"تعداد مورد نظر را بین <b>1 تا {max_qty}</b> بنویس 👇"
    )

    reply = ReplyKeyboardMarkup(
        [["⬅️ لغو"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply)


# =============== مرحله ۲: دریافت عدد و انجام خرید ===============
async def handle_purchase_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    add_user(user_id, username)

    data = context.user_data.get("pending_purchase")
    if not data:
        return

    text = update.message.text.strip()
    if text == "⬅️ لغو":
        await update.message.reply_text("❌ خرید لغو شد.", reply_markup=main_markup)
        context.user_data.pop("pending_purchase", None)
        return

    if not text.isdigit():
        await update.message.reply_text("⚠️ لطفاً فقط عدد وارد کن (مثلاً 2).")
        return

    qty = int(text)
    weapon_name = data["weapon_name"]
    max_qty = data["max_qty"]
    price = data["price"]
    total_cost = price * qty

    if qty < 1 or qty > max_qty:
        await update.message.reply_text(f"⚠️ عدد باید بین 1 تا {max_qty} باشد.")
        return

    balance = get_user_money(user_id)
    if total_cost > balance:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    level, capacity = get_armory_meta(user_id)
    current = get_armory_count(user_id)
    free_slots = max(0, capacity - current)
    if qty > free_slots:
        await update.message.reply_text("⚠️ ظرفیت زرادخانه کافی نیست.")
        return

    # کم کردن پول از حساب
    update_user_money(user_id, -total_cost)
    add_weapon(user_id, weapon_name, qty)
    context.user_data.pop("pending_purchase", None)

    await update.message.reply_text(
        f"✅ <b>خرید با موفقیت انجام شد!</b>\n\n"
        f"🚀 {qty}× {weapon_name}\n"
        f"💰 هزینه کل: {total_cost} سکه\n"
        f"🏦 مانده حساب: {get_user_money(user_id)} سکه",
        parse_mode="HTML",
        reply_markup=main_markup
    )

    logger.info(f"User {user_id} purchased {qty}x {weapon_name} for {total_cost} coins")
    
    # لاگ خرید
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_economy(
            user_id,
            f"خرید موشک",
            total_cost,
            f"{qty}× {weapon_name}"
        )
