import time
from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_last_daily, claim_daily_reward
from config.settings import DAILY_REWARD_COINS, DAILY_REWARD_INTERVAL
from keyboards.menus import main_markup
from utils.logger import logger


async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    last_daily = get_last_daily(user_id)
    now = time.time()
    
    if now - last_daily >= DAILY_REWARD_INTERVAL:
        success = claim_daily_reward(user_id, DAILY_REWARD_COINS)
        
        if success:
            await update.message.reply_text(
                f"🎉 شما {DAILY_REWARD_COINS} سکه جایزه روزانه دریافت کردید!",
                reply_markup=main_markup
            )
            logger.info(f"User {user_id} claimed daily reward: +{DAILY_REWARD_COINS} coins")
        else:
            await update.message.reply_text(
                "❌ خطا در دریافت جایزه. لطفاً دوباره تلاش کنید.",
                reply_markup=main_markup
            )
    else:
        remaining = int(DAILY_REWARD_INTERVAL - (now - last_daily))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        
        await update.message.reply_text(
            f"⏱ جایزه روزانه آماده نیست.\n\n"
            f"⏰ زمان باقی‌مانده: {hours} ساعت و {minutes} دقیقه",
            reply_markup=main_markup
        )
