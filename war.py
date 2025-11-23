# handlers/war.py
import time
import random
from typing import Dict, List, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    add_user, get_armory_list, get_user_money, update_user_money
)
from database.db import db
from utils.logger import logger
from utils.log_manager import get_log_manager

# Cooldown (ثانیه)
ATTACK_COOLDOWN = 300  # 5 دقیقه
_last_attack_time: Dict[int, float] = {}

WEAPON_STATS = {
    # موشک‌ها
    "💥 نور": {"attack": 50, "defense": 0},
    "💥 قدر": {"attack": 65, "defense": 0},
    "💥 سومار": {"attack": 78, "defense": 0},
    "💥 کالیبر": {"attack": 90, "defense": 0},
    "💥 زیرکان": {"attack": 120, "defense": 0},
    "💥 تاماهاک": {"attack": 110, "defense": 0},
    "🎯 شهاب": {"attack": 140, "defense": 0},
    "🎯 سجیل": {"attack": 160, "defense": 0},
    "🎯 خرمشهر": {"attack": 180, "defense": 0},
    "🎯 فاتح-۱۱۰": {"attack": 400, "defense": 0},
    "🎯 خیبر شکن": {"attack": 450, "defense": 0},
    "🎯 ذوالفقار": {"attack": 500, "defense": 0},
    "🎯 واردن": {"attack": 550, "defense": 0},
    "🎯 یارس": {"attack": 600, "defense": 0},
    "🎯 شیطان": {"attack": 700, "defense": 0},
    "⚡ فتاح": {"attack": 800, "defense": 0},
    "⚡ وانگارد": {"attack": 900, "defense": 0},
    "⚡ دانگ فنگ": {"attack": 1000, "defense": 0},
    "⚡ هایپر۱": {"attack": 1100, "defense": 0},
    "⚡ هایپر۲": {"attack": 1200, "defense": 0},
    "⚡ هایپر۳": {"attack": 1300, "defense": 0},
    "⚡ هایپر۴": {"attack": 1400, "defense": 0},
    "⚡ هایپر۵": {"attack": 1500, "defense": 0},
    "⚡ هایپر۶": {"attack": 1600, "defense": 0},
    "☢️ تزار": {"attack": 2000, "defense": 0},
    "☢️ موشک۲": {"attack": 2200, "defense": 0},
    "☢️ موشک۳": {"attack": 2400, "defense": 0},
    "☢️ موشک۴": {"attack": 2600, "defense": 0},
    "☢️ موشک۵": {"attack": 2800, "defense": 0},
    "☢️ موشک۶": {"attack": 3000, "defense": 0},
    "☢️ موشک۷": {"attack": 3200, "defense": 0},
    "☢️ موشک۸": {"attack": 3400, "defense": 0},
    "☢️ موشک۹": {"attack": 4000, "defense": 0},
    # پدافند
    "🪖 مرصاد": {"attack": 0, "defense": 100},
    "🛰️ باور-۳۷۳": {"attack": 0, "defense": 180},
    "☢️ S-300": {"attack": 0, "defense": 160},
    "🛡️ گنبد آهنین": {"attack": 0, "defense": 80},
    "🧨 باراک": {"attack": 0, "defense": 100},
    "🧱 تاد": {"attack": 0, "defense": 150},
    "⚙️ فلاخان داوود": {"attack": 0, "defense": 70},
    "🪖 S-400": {"attack": 0, "defense": 200},
}

STEAL_RATIO = 0.08


def get_now() -> float:
    return time.time()


def can_attack(user_id: int) -> Tuple[bool, int]:
    last = _last_attack_time.get(user_id, 0)
    elapsed = get_now() - last
    if elapsed >= ATTACK_COOLDOWN:
        return True, 0
    return False, int(ATTACK_COOLDOWN - elapsed)


def set_attack_time(user_id: int):
    _last_attack_time[user_id] = get_now()


def compute_power_from_armory(armory: List[Tuple[str, int]]) -> Tuple[int, int]:
    atk = 0
    dfs = 0
    for name, qty in armory:
        stats = WEAPON_STATS.get(name)
        if not stats:
            continue
        atk += stats.get("attack", 0) * qty
        dfs += stats.get("defense", 0) * qty
    return int(atk), int(dfs)


def remove_weapons_from_armory(user_id: int, weapon_losses: Dict[str, int]):
    try:
        with db.get_cursor() as cursor:
            for w, lost in weapon_losses.items():
                if lost <= 0:
                    continue
                row = cursor.execute(
                    "SELECT count FROM armory WHERE user_id=? AND weapon_name=?",
                    (user_id, w)
                ).fetchone()
                if not row:
                    continue
                cur = row["count"]
                new_amount = max(0, cur - lost)
                if new_amount == 0:
                    cursor.execute(
                        "DELETE FROM armory WHERE user_id=? AND weapon_name=?",
                        (user_id, w)
                    )
                else:
                    cursor.execute(
                        "UPDATE armory SET count=? WHERE user_id=? AND weapon_name=?",
                        (new_amount, user_id, w)
                    )
        logger.info(f"Removed weapons from user {user_id}: {weapon_losses}")
    except Exception as e:
        logger.error(f"Error removing weapons for user {user_id}: {e}")


# 🎯 هندلر دستور "حمله [موشک]"
async def attack_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    attacker = msg.from_user
    attacker_id = attacker.id
    
    # رد کردن پیام‌های ارسال شده توسط Anonymous Admin
    if attacker.username == "GroupAnonymousBot" or attacker_id == 1087968824:
        await msg.reply_text(
            "⚠️ برای حمله، باید به عنوان خودت (نه Admin Anonymous) پیام بفرستی!\n\n"
            "💡 در تنظیمات گروه، گزینه 'Remain Anonymous' رو خاموش کن."
        )
        return
    
    attacker_username = msg.from_user.username
    add_user(attacker_id, attacker_username)

    # باید ریپلای کرده باشه
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await msg.reply_text("❗ برای حمله باید پیام یکی رو ریپلای کنی و بنویسی 'حمله [نام موشک]'.\n\nمثال: حمله نور")
        return

    target_user = msg.reply_to_message.from_user
    target_id = target_user.id

    if target_id == attacker_id:
        await msg.reply_text("❌ نمی‌تونی به خودت حمله کنی.")
        return

    # استخراج نام موشک از متن
    text = msg.text.strip()
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        await msg.reply_text("❌ نام موشک رو مشخص نکردی!\n\nمثال: حمله نور")
        return
    
    missile_name = parts[1].strip()
    
    # بررسی موشک در زرادخانه مهاجم
    attacker_armory = get_armory_list(attacker_id)
    
    if not attacker_armory:
        await msg.reply_text("❌ تو هیچ سلاحی نداری که حمله کنی.")
        return
    
    # پیدا کردن موشک مورد نظر در زرادخانه
    missile_found = None
    missile_qty = 0
    
    # نرمال‌سازی نام موشک (حذف فاصله‌های اضافی)
    missile_name_clean = missile_name.strip().lower()
    
    # چک کردن با emoji و بدون emoji
    for weapon, qty in attacker_armory:
        weapon_clean = weapon.lower()
        
        # بررسی نام کامل
        if missile_name_clean == weapon_clean:
            missile_found = weapon
            missile_qty = qty
            break
        
        # بررسی نام بدون emoji (مثلاً "نور" در "💥 نور")
        weapon_without_emoji = weapon.split()[-1].lower()  # آخرین کلمه
        if missile_name_clean == weapon_without_emoji:
            missile_found = weapon
            missile_qty = qty
            break
        
        # بررسی اینکه نام موشک در نام سلاح وجود دارد
        if missile_name_clean in weapon_clean:
            missile_found = weapon
            missile_qty = qty
            break
    
    if not missile_found:
        await msg.reply_text(f"❌ موشک '{missile_name}' در زرادخانه‌ات پیدا نشد!\n\nبرای مشاهده موشک‌هایت به زرادخانه برو.")
        return
    
    # بررسی اینکه موشک انتخابی یک سلاح تهاجمی است (نه پدافند)
    stats = WEAPON_STATS.get(missile_found)
    if not stats or stats.get("attack", 0) <= 0:
        await msg.reply_text(f"❌ {missile_found} یک موشک تهاجمی نیست!")
        return

    # Cooldown
    ok, wait = can_attack(attacker_id)
    if not ok:
        await msg.reply_text(f"⏳ باید {wait} ثانیه صبر کنی تا دوباره حمله کنی.")
        return

    target_username = target_user.username
    add_user(target_id, target_username)
    target_armory = get_armory_list(target_id)

    # محاسبه قدرت حمله فقط بر اساس موشک انتخابی
    atk_power = stats.get("attack", 0)
    _, def_power = compute_power_from_armory(target_armory)

    variance_atk = random.uniform(0.9, 1.1)
    variance_def = random.uniform(0.9, 1.1)
    final_atk = int(atk_power * variance_atk)
    final_def = int(def_power * variance_def)
    damage = max(0, final_atk - final_def)

    target_balance = get_user_money(target_id)
    stolen = min(target_balance, max(0, int(damage * STEAL_RATIO)))

    try:
        if stolen > 0:
            update_user_money(target_id, target_balance - stolen)
            attacker_balance = get_user_money(attacker_id)
            update_user_money(attacker_id, attacker_balance + stolen)
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        await msg.reply_text("❌ خطا در محاسبه‌ی غنیمت.")
        return

    # استفاده از موشک (کاهش 1 عدد از زرادخانه مهاجم)
    try:
        with db.get_cursor() as cursor:
            new_qty = missile_qty - 1
            if new_qty <= 0:
                cursor.execute(
                    "DELETE FROM armory WHERE user_id=? AND weapon_name=?",
                    (attacker_id, missile_found)
                )
            else:
                cursor.execute(
                    "UPDATE armory SET count=? WHERE user_id=? AND weapon_name=?",
                    (new_qty, attacker_id, missile_found)
                )
        logger.info(f"User {attacker_id} used 1x {missile_found} in attack")
    except Exception as e:
        logger.error(f"Error using missile: {e}")

    weapon_losses = {}
    if damage > 0:
        for w_name, qty in target_armory:
            stats_def = WEAPON_STATS.get(w_name)
            if not stats_def:
                continue
            if stats_def.get("defense", 0) > 0 and qty > 0:
                loss = random.randint(0, min(2, qty))
                if loss > 0:
                    weapon_losses[w_name] = weapon_losses.get(w_name, 0) + loss
        if weapon_losses:
            remove_weapons_from_armory(target_id, weapon_losses)

    set_attack_time(attacker_id)

    attacker_name = f"@{attacker.username}" if attacker.username else attacker.first_name
    target_name = f"@{target_user.username}" if target_user.username else target_user.first_name

    result_lines = [
        "💥 نبرد انجام شد 💥",
        "━━━━━━━━━━━",
        f"🚀 مهاجم: {attacker_name}",
        f"🎯 موشک استفاده شده: {missile_found}",
        f"🛡️ مدافع: {target_name}",
        "",
        f"⚔️ قدرت حمله: {final_atk}",
        f"🛡️ قدرت دفاع: {final_def}",
        f"💣 خسارت واردشده: {damage}",
        f"💰 غنیمت: {stolen} سکه",
    ]
    if weapon_losses:
        losses_text = "، ".join([f"{v}× {k}" for k, v in weapon_losses.items()])
        result_lines.append(f"🧨 تلفات مدافع: {losses_text}")

    if damage > 0 and stolen > 0:
        result_lines.append(f"🏆 نتیجه: پیروزی برای {attacker_name} 🎉")
        result_text = "پیروزی"
    else:
        result_lines.append("🛡️ نتیجه: دفاع موفق — حمله ناکام ماند.")
        result_text = "دفاع موفق"

    await msg.reply_text("\n".join(result_lines))
    
    # لاگ جنگ
    log_manager = get_log_manager()
    if log_manager:
        await log_manager.log_war(
            attacker_id,
            target_id,
            missile_found,
            f"{result_text} | خسارت: {damage} | غنیمت: {stolen}"
        )
