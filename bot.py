import logging
import os
import math
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7288739341"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_ids = set()
user_data = {}

# =============================================
# MAMLAKAT VA SHAHARLAR
# =============================================
COUNTRIES = {
    "uz": {"name": "🇺🇿 O'zbekiston", "api": "Uzbekistan"},
    "ru": {"name": "🇷🇺 Rossiya", "api": "Russia"},
    "kz": {"name": "🇰🇿 Qozog'iston", "api": "Kazakhstan"},
    "tr": {"name": "🇹🇷 Turkiya", "api": "Turkey"},
    "ae": {"name": "🇦🇪 BAA", "api": "UAE"},
    "de": {"name": "🇩🇪 Germaniya", "api": "Germany"},
    "us": {"name": "🇺🇸 AQSH", "api": "United States"},
    "gb": {"name": "🇬🇧 Buyuk Britaniya", "api": "United Kingdom"},
}

CITIES = {
    "uz": ["Toshkent", "Samarqand", "Buxoro", "Namangan", "Andijon", "Farg'ona", "Qo'qon", "Nukus", "Termiz", "Qarshi", "Jizzax", "Navoiy"],
    "ru": ["Moskva", "Sankt-Peterburg", "Kazan", "Ufa", "Novosibirsk", "Yekaterinburg"],
    "kz": ["Olmaota", "Astana", "Shymkent"],
    "tr": ["Istanbul", "Anqara", "Izmir", "Bursa"],
    "ae": ["Dubay", "Abu-Dabi", "Sharjah"],
    "de": ["Berlin", "Myunxen", "Frankfurt", "Gamburg"],
    "us": ["Nyu-York", "Los-Anjeles", "Chikago", "Xouston"],
    "gb": ["London", "Manchester", "Birmingham"],
}

CITY_API_NAME = {
    "Toshkent": "Tashkent", "Samarqand": "Samarkand", "Buxoro": "Bukhara",
    "Namangan": "Namangan", "Andijon": "Andijan", "Farg'ona": "Fergana",
    "Qo'qon": "Kokand", "Nukus": "Nukus", "Termiz": "Termez",
    "Qarshi": "Karshi", "Jizzax": "Jizzakh", "Navoiy": "Navoi",
    "Moskva": "Moscow", "Sankt-Peterburg": "Saint Petersburg",
    "Kazan": "Kazan", "Ufa": "Ufa", "Novosibirsk": "Novosibirsk",
    "Yekaterinburg": "Yekaterinburg", "Olmaota": "Almaty",
    "Astana": "Astana", "Shymkent": "Shymkent",
    "Istanbul": "Istanbul", "Anqara": "Ankara", "Izmir": "Izmir", "Bursa": "Bursa",
    "Dubay": "Dubai", "Abu-Dabi": "Abu Dhabi", "Sharjah": "Sharjah",
    "Berlin": "Berlin", "Myunxen": "Munich", "Frankfurt": "Frankfurt", "Gamburg": "Hamburg",
    "Nyu-York": "New York", "Los-Anjeles": "Los Angeles", "Chikago": "Chicago", "Xouston": "Houston",
    "London": "London", "Manchester": "Manchester", "Birmingham": "Birmingham",
}

PRAYER_NAMES = {
    "Fajr": "🌅 Bomdod",
    "Sunrise": "🌄 Quyosh",
    "Dhuhr": "☀️  Peshin",
    "Asr": "🌇 Asr",
    "Maghrib": "🌆 Shom",
    "Isha": "🌙 Xufton",
}

HIJRI_MONTHS = [
    "Muharram", "Safar", "Rabi ul-avval", "Rabi ul-oxir",
    "Jumad ul-avval", "Jumad ul-oxir", "Rajab", "Sha'bon",
    "Ramazon", "Shavvol", "Zul-qa'da", "Zul-hijja"
]


# =============================================
# KLAVIATURALAR
# =============================================
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🕌 Namoz vaqtlari"), KeyboardButton("🧭 Qibla tomoni")],
        [KeyboardButton("⚙️ Shaharni o'zgartirish"), KeyboardButton("ℹ️ Bot haqida")],
    ], resize_keyboard=True)


def get_country_keyboard():
    buttons = []
    row = []
    for code, info in COUNTRIES.items():
        row.append(InlineKeyboardButton(info["name"], callback_data=f"country_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def get_city_keyboard(country_code):
    cities = CITIES.get(country_code, [])
    buttons = []
    row = []
    for city in cities:
        row.append(InlineKeyboardButton(city, callback_data=f"city_{country_code}_{city}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_countries")])
    return InlineKeyboardMarkup(buttons)


# =============================================
# API FUNKSIYALAR
# =============================================
async def fetch_prayer_times(city: str, country: str):
    api_city = CITY_API_NAME.get(city, city)
    url = f"https://api.aladhan.com/v1/timingsByCity?city={api_city}&country={country}&method=3"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {})
    except Exception as e:
        logger.error(f"API xatosi: {e}")
    return None


async def fetch_coordinates(city: str, country: str):
    data = await fetch_prayer_times(city, country)
    if data and "meta" in data:
        meta = data["meta"]
        return float(meta.get("latitude", 0)), float(meta.get("longitude", 0))
    return None, None


def calculate_qibla(lat1, lon1):
    lat2 = math.radians(21.3891)
    lon2 = math.radians(39.8579)
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    bearing = (bearing + 360) % 360
    return round(bearing, 1)


def get_compass_direction(angle):
    directions = [
        (22.5, "Shimol ⬆️"), (67.5, "Shimoli-sharq ↗️"),
        (112.5, "Sharq ➡️"), (157.5, "Janubi-sharq ↘️"),
        (202.5, "Janub ⬇️"), (247.5, "Janubi-g'arb ↙️"),
        (292.5, "G'arb ⬅️"), (337.5, "Shimoli-g'arb ↖️"),
    ]
    for limit, name in directions:
        if angle < limit:
            return name
    return "Shimol ⬆️"


def get_compass_visual(angle):
    a = angle
    if a < 22.5 or a >= 337.5:
        return "     🟢\n⬅️  •  ➡️\n     ⬇️\n(Shimol — to'g'ri oldinga)"
    elif a < 67.5:
        return "     ⬆️\n⬅️  •  🟢\n     ⬇️\n(Shimoli-sharq — o'ng-old)"
    elif a < 112.5:
        return "     ⬆️\n⬅️  •  🟢\n     ⬇️\n(Sharq — to'g'ri o'ngga)"
    elif a < 157.5:
        return "     ⬆️\n⬅️  •  ➡️\n     🟢\n(Janubi-sharq — o'ng-orqa)"
    elif a < 202.5:
        return "     ⬆️\n⬅️  •  ➡️\n     🟢\n(Janub — to'g'ri orqaga)"
    elif a < 247.5:
        return "     ⬆️\n🟢  •  ➡️\n     ⬇️\n(Janubi-g'arb — chap-orqa)"
    elif a < 292.5:
        return "     ⬆️\n🟢  •  ➡️\n     ⬇️\n(G'arb — to'g'ri chapga)"
    else:
        return "     🟢\n⬅️  •  ➡️\n     ⬇️\n(Shimoli-g'arb — chap-old)"


def get_next_prayer(timings):
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    prayers = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    for prayer in prayers:
        t = timings.get(prayer, "")
        if t[:5] > current_time:
            h, m = map(int, t[:5].split(":"))
            ch, cm = map(int, current_time.split(":"))
            diff = (h * 60 + m) - (ch * 60 + cm)
            hours = diff // 60
            mins = diff % 60
            name = PRAYER_NAMES.get(prayer, prayer)
            if hours > 0:
                return f"{name} — {hours} soat {mins} daqiqadan keyin"
            else:
                return f"{name} — {mins} daqiqadan keyin"
    return "🌙 Barcha namozlar o'qildi. Ertangi Bomdod kutilmoqda."


# =============================================
# /start
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_ids.add(user.id)

    await update.message.reply_text(
        f"🕌 Assalomu alaykum, {user.first_name}!\n\n"
        "Namoz vaqtlari botiga xush kelibsiz!\n\n"
        "Avval qaysi mamlakatda ekanligingizni tanlang 👇",
        reply_markup=get_country_keyboard()
    )


# =============================================
# CALLBACK HANDLER
# =============================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_ids.add(user.id)
    data = query.data

    if data == "back_countries":
        await query.message.edit_text(
            "🌍 Mamlakatni tanlang:",
            reply_markup=get_country_keyboard()
        )

    elif data.startswith("country_"):
        country_code = data.replace("country_", "")
        context.user_data["selecting_country"] = country_code
        country_name = COUNTRIES[country_code]["name"]
        await query.message.edit_text(
            f"{country_name} tanlandi!\n\nEndi shahringizni tanlang 👇",
            reply_markup=get_city_keyboard(country_code)
        )

    elif data.startswith("city_"):
        parts = data.split("_", 2)
        country_code = parts[1]
        city = parts[2]
        country_info = COUNTRIES[country_code]

        user_data[user.id] = {
            "city": city,
            "country": country_info["api"],
            "country_code": country_code,
            "city_name": city,
        }

        await query.message.edit_text(
            f"✅ {country_info['name']} — {city}\n\nManzil saqlandi!"
        )
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"🕌 *Namoz Vaqtlari Bot*\n\n"
                f"📍 Shahar: *{city}*\n\n"
                "Quyidagi tugmalardan foydalaning:"
            ),
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

    elif data == "user_count":
        if user.id != ADMIN_ID:
            return
        await query.message.reply_text(
            f"👥 Jami foydalanuvchilar: *{len(user_ids)}* ta",
            parse_mode="Markdown"
        )

    elif data == "broadcast":
        if user.id != ADMIN_ID:
            return
        context.user_data["waiting_broadcast"] = True
        await query.message.reply_text(
            "✍️ Hammaga yubormoqchi bo'lgan xabaringizni yozing:\n"
            "_(Bekor qilish: /cancel)_",
            parse_mode="Markdown"
        )


# =============================================
# MATN XABARLAR HANDLER
# =============================================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_ids.add(user.id)

    # Admin broadcast
    if user.id == ADMIN_ID and context.user_data.get("waiting_broadcast"):
        context.user_data["waiting_broadcast"] = False
        await update.message.reply_text(f"⏳ Yuborilmoqda... ({len(user_ids)} ta foydalanuvchi)")
        success, failed = 0, 0
        for uid in list(user_ids):
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                success += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"✅ *Yuborish yakunlandi!*\n\n"
            f"✔️ Muvaffaqiyatli: *{success}* ta\n"
            f"❌ Xatolik: *{failed}* ta",
            parse_mode="Markdown"
        )
        return

    # Foydalanuvchi ma'lumoti yo'q
    if user.id not in user_data and text not in ["⚙️ Shaharni o'zgartirish"]:
        await update.message.reply_text(
            "Iltimos, avval shaharni tanlang 👇",
            reply_markup=get_country_keyboard()
        )
        return

    udata = user_data.get(user.id, {})

    # ---- NAMOZ VAQTLARI ----
    if text == "🕌 Namoz vaqtlari":
        await update.message.reply_text("⏳ Namoz vaqtlari yuklanmoqda...")
        data = await fetch_prayer_times(udata["city"], udata["country"])

        if not data:
            await update.message.reply_text("❌ Ma'lumot olishda xatolik. Qayta urinib ko'ring.")
            return

        timings = data.get("timings", {})
        date_info = data.get("date", {})
        gregorian = date_info.get("gregorian", {})
        hijri = date_info.get("hijri", {})

        hijri_day = hijri.get("day", "")
        hijri_month_num = int(hijri.get("month", {}).get("number", 1)) - 1
        hijri_month = HIJRI_MONTHS[hijri_month_num] if 0 <= hijri_month_num < 12 else ""
        hijri_year = hijri.get("year", "")

        greg_date = gregorian.get("date", "")
        weekday = gregorian.get("weekday", {}).get("en", "")

        WEEKDAYS = {
            "Monday": "Dushanba", "Tuesday": "Seshanba", "Wednesday": "Chorshanba",
            "Thursday": "Payshanba", "Friday": "Juma", "Saturday": "Shanba", "Sunday": "Yakshanba"
        }
        weekday_uz = WEEKDAYS.get(weekday, weekday)

        next_prayer = get_next_prayer(timings)

        msg = (
            f"🕌 *Namoz Vaqtlari*\n"
            f"📍 {udata['city_name']}\n\n"
            f"📅 {weekday_uz}, {greg_date}\n"
            f"🌙 {hijri_day} {hijri_month} {hijri_year} h.\n\n"
            f"{PRAYER_NAMES['Fajr']}: *{timings.get('Fajr', '')[:5]}*\n"
            f"{PRAYER_NAMES['Sunrise']}: *{timings.get('Sunrise', '')[:5]}*\n"
            f"{PRAYER_NAMES['Dhuhr']}: *{timings.get('Dhuhr', '')[:5]}*\n"
            f"{PRAYER_NAMES['Asr']}: *{timings.get('Asr', '')[:5]}*\n"
            f"{PRAYER_NAMES['Maghrib']}: *{timings.get('Maghrib', '')[:5]}*\n"
            f"{PRAYER_NAMES['Isha']}: *{timings.get('Isha', '')[:5]}*\n\n"
            f"⏰ *Keyingi namoz:*\n{next_prayer}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    # ---- QIBLA TOMONI ----
    elif text == "🧭 Qibla tomoni":
        await update.message.reply_text("⏳ Qibla tomoni hisoblanmoqda...")
        lat, lon = await fetch_coordinates(udata["city"], udata["country"])

        if lat is None:
            await update.message.reply_text("❌ Koordinatalarni olishda xatolik.")
            return

        angle = calculate_qibla(lat, lon)
        direction = get_compass_direction(angle)
        compass = get_compass_visual(angle)

        msg = (
            f"🧭 *Qibla Tomoni*\n"
            f"📍 {udata['city_name']}\n\n"
            f"📐 Qibla burchagi: *{angle}°*\n"
            f"🧭 Yo'nalish: *{direction}*\n\n"
            f"```\n{compass}\n```\n\n"
            f"🟢 — Qibla tomoni (Ka'ba)\n"
            f"📍 Koordinatlar: {round(lat,4)}°N, {round(lon,4)}°E"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    # ---- SHAHARNI O'ZGARTIRISH ----
    elif text == "⚙️ Shaharni o'zgartirish":
        await update.message.reply_text(
            "🌍 Yangi mamlakatni tanlang:",
            reply_markup=get_country_keyboard()
        )

    # ---- BOT HAQIDA ----
    elif text == "ℹ️ Bot haqida":
        city = udata.get("city_name", "Tanlanmagan")
        msg = (
            "🕌 *Namoz Vaqtlari Bot*\n\n"
            "Bu bot sizga har kuni namoz vaqtlarini va\n"
            "qibla yo'nalishini ko'rsatib beradi.\n\n"
            f"📍 Hozirgi shahar: *{city}*\n\n"
            "📡 Ma'lumot manbai: Aladhan API\n"
            "🔄 Vaqtlar har kuni yangilanadi\n\n"
            "Savollar uchun: @TolibDev"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")


# =============================================
# ADMIN PANEL
# =============================================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q!")
        return

    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="user_count")],
        [InlineKeyboardButton("📨 Hammaga xabar yuborish", callback_data="broadcast")],
    ]
    await update.message.reply_text(
        f"⚙️ *Admin Panel*\n\n"
        f"👥 Foydalanuvchilar: *{len(user_ids)}* ta",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["waiting_broadcast"] = False
    await update.message.reply_text("❌ Bekor qilindi.")


# =============================================
# MAIN
# =============================================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Namoz Vaqtlari Bot ishga tushdi ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
