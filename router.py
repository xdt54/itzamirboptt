import re
from telegram import Update
from telegram.ext import ContextTypes

from database.models import add_user
from keyboards.menus import main_markup, store_markup, mine_markup
from handlers.main import show_inventory
from handlers.daily import daily_reward
from handlers.admin import admin_panel
from handlers.shop import (
    show_shop, show_missile_categories,
    show_cruise_missiles, show_ballistic_missiles,
    show_hypersonic_missiles, show_nuclear_missiles,
    show_defense_systems, show_purchase_receipt,
    handle_purchase_quantity
)
from handlers.mine import show_mine_menu, enter_mine, show_sell_menu
from handlers.armory import show_armory_menu, view_armory, upgrade_armory
from handlers.bank import bank_menu
from utils.logger import logger
from handlers.profile import show_profile


# 🧩 پاک‌سازی متن از فاصله‌ها و کاراکترهای مخفی
def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u3164", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع همه پیام‌های متنی را بررسی می‌کند.
    در گروه‌ها هیچ پاسخی ارسال نمی‌کند (تا اسپم نشود).
    فقط در پیوی منوها، خرید و سایر عملیات‌ها را انجام می‌دهد.
    """
    msg = update.message
    user_id = msg.from_user.id
    username = msg.from_user.username
    chat = msg.chat
    text = normalize_text(msg.text or "")

    add_user(user_id, username)

    # ✅ جلوگیری از ارسال هر پیام در گروه
    if chat.type != "private":
        return

    # 🚫 چک کردن بن
    from database.db import db
    try:
        is_banned = db.fetchone("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        if is_banned:
            await msg.reply_text(
                "🚫 <b>شما بن شده‌اید!</b>\n\n"
                "برای اطلاعات بیشتر با ادمین تماس بگیرید.",
                parse_mode="HTML"
            )
            return
    except Exception:
        # اگر جدول وجود نداره، نادیده بگیر
        pass

    # -------------------------
    # 🎛️ منوها و دکمه‌ها
    # -------------------------
    if text == "👤 پروفایل من":
        await show_profile(update, context); return

    if text == "💰 دارایی‌ها":
        await show_inventory(update, context); return

    if text == "🎁 جایزه روزانه":
        await daily_reward(update, context); return

    if text == "🏪 فروشگاه":
        await show_shop(update, context); return

    if text == "🏛️ بانک":
        await bank_menu(update, context); return

    if text == "🔐 پنل ادمین":
        await admin_panel(update, context); return

    if text == "🚀 موشک":
        await show_missile_categories(update, context); return

    if text in ("📡 پدافند", "🛡️ پدافند"):
        await show_defense_systems(update, context); return

    if text == "💥 کروز":
        await show_cruise_missiles(update, context); return
    if text == "🎯 بالستیک":
        await show_ballistic_missiles(update, context); return
    if text == "⚡ هایپر سونیک":
        await show_hypersonic_missiles(update, context); return
    if "هسته" in text or "هست" in text:
        await show_nuclear_missiles(update, context); return

    # معدن
    if text == "⛏️ معدن":
        await show_mine_menu(update, context); return
    if text == "⛏️ ورود به معدن":
        await enter_mine(update, context); return
    if text == "💎 فروش منابع":
        await show_sell_menu(update, context); return

    # زرادخانه
    if text == "🧰 زرادخانه":
        await show_armory_menu(update, context); return
    if text == "مشاهده زرادخانه":
        await view_armory(update, context); return
    if text == "ارتقا زرادخانه":
        await upgrade_armory(update, context); return

    # ---------------------------------------
    # 🎯 خرید مستقیم موشک‌ها و پدافندها
    # ---------------------------------------
    weapon_names = [
        # موشک‌ها
        "💥 نور", "💥 قدر", "💥 سومار", "💥 کالیبر", "💥 زیرکان", "💥 تاماهاک",
        "🎯 شهاب", "🎯 سجیل", "🎯 خرمشهر", "🎯 فاتح-۱۱۰", "🎯 خیبر شکن",
        "🎯 ذوالفقار", "🎯 واردن", "🎯 یارس", "🎯 شیطان",
        "⚡ فتاح", "⚡ وانگارد", "⚡ دانگ فنگ",
        "⚡ هایپر۱", "⚡ هایپر۲", "⚡ هایپر۳", "⚡ هایپر۴", "⚡ هایپر۵", "⚡ هایپر۶",
        "☢️ تزار", "☢️ موشک۲", "☢️ موشک۳", "☢️ موشک۴", "☢️ موشک۵",
        "☢️ موشک۶", "☢️ موشک۷", "☢️ موشک۸", "☢️ موشک۹",
        # پدافندها
        "🪖 مرصاد", "🛰️ باور-۳۷۳", "☢️ S-300", "🛡️ گنبد آهنین", "🧨 باراک", "🧱 تاد", "⚙️ فلاخان داوود", "🪖 S-400"
    ]

    if text in weapon_names:
        await show_purchase_receipt(update, context, text)
        return

    # ---------------------------------------
    # 💰 بررسی عدد برای خرید بعد از رسید خرید
    # ---------------------------------------
    if context.user_data.get("pending_purchase"):
        await handle_purchase_quantity(update, context)
        return

    # -------------------------
    # 🔙 بازگشت‌ها
    # -------------------------
    if text in ("🔙 بازگشت به منوی اصلی", "🔙 بازگشت به منو"):
        await msg.reply_text("بازگشت به منوی اصلی.", reply_markup=main_markup); return

    if text in ("🔙 بازگشت به فروشگاه", "🔙 بازگشت به دسته‌بندی"):
        await msg.reply_text("بازگشت به فروشگاه.", reply_markup=store_markup); return

    if text == "🔙 بازگشت به معدن":
        await msg.reply_text("بازگشت به معدن.", reply_markup=mine_markup); return

    # -------------------------
    # ⚠️ دستور ناشناخته
    # -------------------------
    await msg.reply_text(
        "⚠️ دستور ناشناخته. لطفاً از دکمه‌ها استفاده کنید.",
        reply_markup=main_markup
    )
    logger.warning(f"Unknown command from user {user_id}: {text}")
