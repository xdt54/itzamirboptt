from telegram import ReplyKeyboardMarkup


# 🏠 منوی اصلی
main_keyboard = [
    ["👤 پروفایل من", "🏪 فروشگاه"],
    ["⛏️ معدن", "👥 کلن"],
    ["🏛️ بانک", "🎁 جایزه روزانه"],
    ["🧰 زرادخانه"]
]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)


def get_main_keyboard(is_admin: bool = False):
    """دریافت کیبورد اصلی با/بدون دکمه ادمین"""
    keyboard = [
        ["👤 پروفایل من", "🏪 فروشگاه"],
        ["⛏️ معدن", "👥 کلن"],
        ["🏛️ بانک", "🎁 جایزه روزانه"],
        ["🧰 زرادخانه"]
    ]
    
    if is_admin:
        keyboard.append(["🔐 پنل ادمین"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ⚒️ منوی معدن
mine_keyboard = [
    ["⛏️ ورود به معدن", "⚡ ارتقا معدن"],
    ["💎 فروش منابع", "🔙 بازگشت به منوی اصلی"]
]
mine_markup = ReplyKeyboardMarkup(mine_keyboard, resize_keyboard=True)


# 💎 فروش منابع
sell_keyboard = [
    ["🛠️ فروش آهن", "⚪ فروش نقره"],
    ["🔙 بازگشت به معدن"]
]
sell_markup = ReplyKeyboardMarkup(sell_keyboard, resize_keyboard=True)


# 🏪 فروشگاه (فقط موشک و پدافند)
store_keyboard = [
    ["🚀 موشک"],
    ["📡 پدافند"],
    ["🔙 بازگشت به منو"]
]
store_markup = ReplyKeyboardMarkup(store_keyboard, resize_keyboard=True)


# 🚀 دسته‌بندی موشک‌ها
missile_category_keyboard = [
    ["💥 کروز"],
    ["🎯 بالستیک"],
    ["⚡ هایپر سونیک"],
    ["☢️ هسته‌ای"],
    ["🔙 بازگشت به فروشگاه"]
]
missile_category_markup = ReplyKeyboardMarkup(missile_category_keyboard, resize_keyboard=True)


# 💥 موشک‌های کروز
cruise_missiles = [
    ["💥 نور"], ["💥 قدر"], ["💥 سومار"], ["💥 کالیبر"],
    ["💥 زیرکان"], ["💥 تاماهاک"],
    ["🔙 بازگشت به دسته‌بندی"]
]
cruise_markup = ReplyKeyboardMarkup(cruise_missiles, resize_keyboard=True)


# 🎯 موشک‌های بالستیک
ballistic_missiles = [
    ["🎯 شهاب"], ["🎯 سجیل"], ["🎯 خرمشهر"], ["🎯 فاتح-۱۱۰"],
    ["🎯 خیبر شکن"], ["🎯 ذوالفقار"], ["🎯 واردن"], ["🎯 یارس"],
    ["🎯 شیطان"], ["🔙 بازگشت به دسته‌بندی"]
]
ballistic_markup = ReplyKeyboardMarkup(ballistic_missiles, resize_keyboard=True)


# ⚡ موشک‌های هایپرسونیک
hypersonic_missiles = [
    ["⚡ فتاح"], ["⚡ وانگارد"], ["⚡ دانگ فنگ"], ["⚡ هایپر۱"],
    ["⚡ هایپر۲"], ["⚡ هایپر۳"], ["⚡ هایپر۴"], ["⚡ هایپر۵"],
    ["⚡ هایپر۶"], ["🔙 بازگشت به دسته‌بندی"]
]
hypersonic_markup = ReplyKeyboardMarkup(hypersonic_missiles, resize_keyboard=True)


# ☢️ موشک‌های هسته‌ای
nuclear_missiles = [
    ["☢️ تزار"], ["☢️ موشک۲"], ["☢️ موشک۳"], ["☢️ موشک۴"],
    ["☢️ موشک۵"], ["☢️ موشک۶"], ["☢️ موشک۷"], ["☢️ موشک۸"],
    ["☢️ موشک۹"], ["🔙 بازگشت به دسته‌بندی"]
]
nuclear_markup = ReplyKeyboardMarkup(nuclear_missiles, resize_keyboard=True)


# 🛡️ پدافند
defense_items = [
    ["🪖 مرصاد"],
    ["🛰️ باور-۳۷۳"],
    ["☢️ S-300"],
    ["🛡️ گنبد آهنین"],
    ["🧨 باراک"],
    ["🧱 تاد"],
    ["⚙️ فلاخان داوود"],
    ["🪖 S-400"],
    ["🔙 بازگشت به فروشگاه"]
]
defense_markup = ReplyKeyboardMarkup(defense_items, resize_keyboard=True)


# 🧰 زرادخانه
armory_keyboard = [
    ["ارتقا زرادخانه", "مشاهده زرادخانه"],
    ["🔙 بازگشت به منو"]
]
armory_markup = ReplyKeyboardMarkup(armory_keyboard, resize_keyboard=True)
