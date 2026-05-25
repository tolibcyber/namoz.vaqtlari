import os
import math
import json
import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
from dotenv import load_dotenv

from telegram import (
Update,
InlineKeyboardButton,
InlineKeyboardMarkup,
ReplyKeyboardMarkup,
KeyboardButton,
WebAppInfo,
)

from telegram.ext import (
ApplicationBuilder,
CommandHandler,
CallbackQueryHandler,
MessageHandler,
ContextTypes,
filters,
)

# =========================

# LOAD ENV

# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")

# =========================

# LOGGING

# =========================

logging.basicConfig(
format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================

# STORAGE

# =========================

DATA_FILE = "users.json"

user_ids = set()
user_data = {}

CACHE = {}

# =========================

# COUNTRIES

# =========================

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
"Toshkent": "Tashkent",
"Samarqand": "Samarkand",
"Buxoro": "Bukhara",
"Namangan": "Namangan",
"Andijon": "Andijan",
"Farg'ona": "Fergana",
"Qo'qon": "Kokand",
"Nukus": "Nukus",
"Termiz": "Termez",
"Qarshi": "Karshi",
"Jizzax": "Jizzakh",
"Navoiy": "Navoi",
"Moskva": "Moscow",
"Sankt-Peterburg": "Saint Petersburg",
"Kazan": "Kazan",
"Ufa": "Ufa",
"Novosibirsk": "Novosibirsk",
"Yekaterinburg": "Yekaterinburg",
"Olmaota": "Almaty",
"Astana": "Astana",
"Shymkent": "Shymkent",
"Anqara": "Ankara",
"Dubay": "Dubai",
"Abu-Dabi": "Abu Dhabi",
"Myunxen": "Munich",
"Gamburg": "Hamburg",
"Nyu-York": "New York",
"Los-Anjeles": "Los Angeles",
"Chikago": "Chicago",
"Xouston": "Houston",
}

HIJRI_MONTHS = [
"Muharram",
"Safar",
"Rabi ul-avval",
"Rabi ul-oxir",
"Jumad ul-avval",
"Jumad ul-oxir",
"Rajab",
"Sha'bon",
"Ramazon",
"Shavvol",
"Zul-qa'da",
"Zul-hijja",
]

WEEKDAYS = {
"Monday": "Dushanba",
"Tuesday": "Seshanba",
"Wednesday": "Chorshanba",
"Thursday": "Payshanba",
"Friday": "Juma ✨",
"Saturday": "Shanba",
"Sunday": "Yakshanba",
}

# =========================

# SAVE / LOAD

# =========================

def save_data():
try:
data = {
"user_ids": list(user_ids),
"user_data": user_data,
}

```
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

except Exception as e:
    logger.error(f"Save error: {e}")
```

def load_data():
global user_ids, user_data

```
if not os.path.exists(DATA_FILE):
    return

try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

        user_ids = set(data.get("user_ids", []))
        user_data = data.get("user_data", {})

except Exception as e:
    logger.error(f"Load error: {e}")
```

# =========================

# KEYBOARDS

# =========================

def main_keyboard():
return ReplyKeyboardMarkup(
[
[
KeyboardButton("🕌 Namoz vaqtlari"),
KeyboardButton("🧭 Qibla tomoni"),
],
[
KeyboardButton("📱 Mini App", web_app=WebAppInfo(url=WEBAPP_URL)),
],
[
KeyboardButton("⚙️ Shaharni o'zgartirish"),
KeyboardButton("ℹ️ Bot haqida"),
],
],
resize_keyboard=True,
)

def countries_keyboard():
keyboard = []

```
row = []

for code, data in COUNTRIES.items():
    row.append(
        InlineKeyboardButton(
            data["name"],
            callback_data=f"country_{code}",
        )
    )

    if len(row) == 2:
        keyboard.append(row)
        row = []

if row:
    keyboard.append(row)

return InlineKeyboardMarkup(keyboard)
```

def cities_keyboard(code):
keyboard = []

```
row = []

for city in CITIES.get(code, []):
    row.append(
        InlineKeyboardButton(
            city,
            callback_data=f"city_{code}_{city}",
        )
    )

    if len(row) == 2:
        keyboard.append(row)
        row = []

if row:
    keyboard.append(row)

keyboard.append(
    [
        InlineKeyboardButton(
            "⬅️ Orqaga",
            callback_data="back",
        )
    ]
)

return InlineKeyboardMarkup(keyboard)
```

# =========================

# API

# =========================

session = None

async def get_session():
global session

```
if session is None:
    timeout = aiohttp.ClientTimeout(total=10)

    session = aiohttp.ClientSession(timeout=timeout)

return session
```

async def fetch_prayer_times(city, country):
cache_key = f"{city}_{country}"

```
if cache_key in CACHE:
    cached = CACHE[cache_key]

    if datetime.now() - cached["time"] < timedelta(minutes=30):
        return cached["data"]

try:
    api_city = CITY_API_NAME.get(city, city)

    url = (
        "https://api.aladhan.com/v1/timingsByCity"
        f"?city={api_city}&country={country}&method=3"
    )

    session = await get_session()

    async with session.get(url) as resp:
        if resp.status != 200:
            return None

        result = await resp.json()

        data = result.get("data")

        CACHE[cache_key] = {
            "time": datetime.now(),
            "data": data,
        }

        return data

except Exception as e:
    logger.error(f"Prayer API error: {e}")
    return None
```

# =========================

# UTILITIES

# =========================

def clean_time(value):
return value.split(" ")[0][:5]

def calculate_next_prayer(timings):
prayers = [
("🌅 Bomdod", clean_time(timings["Fajr"])),
("☀️ Peshin", clean_time(timings["Dhuhr"])),
("🌇 Asr", clean_time(timings["Asr"])),
("🌆 Shom", clean_time(timings["Maghrib"])),
("🌙 Xufton", clean_time(timings["Isha"])),
]

```
now = datetime.now()

for name, time_str in prayers:
    prayer_time = datetime.strptime(time_str, "%H:%M")

    prayer_time = prayer_time.replace(
        year=now.year,
        month=now.month,
        day=now.day,
    )

    if prayer_time > now:
        diff = prayer_time - now

        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60

        return f"{name} — {hours} soat {minutes} daqiqa"

return "🌙 Ertangi Bomdod kutilmoqda"
```

def calculate_qibla(lat, lon):
makkah_lat = math.radians(21.3891)
makkah_lon = math.radians(39.8579)

```
lat = math.radians(lat)
lon = math.radians(lon)

dlon = makkah_lon - lon

x = math.sin(dlon)
y = (
    math.cos(lat) * math.tan(makkah_lat)
    - math.sin(lat) * math.cos(dlon)
)

bearing = math.degrees(math.atan2(x, y))

return round((bearing + 360) % 360, 2)
```

# =========================

# START

# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user

```
user_ids.add(user.id)

save_data()

await update.message.reply_text(
    "🕌 Assalomu alaykum!\n\n"
    "Namoz Vaqtlari Botga xush kelibsiz.\n\n"
    "🌍 Davlatni tanlang:",
    reply_markup=countries_keyboard(),
)
```

# =========================

# CALLBACKS

# =========================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query

```
await query.answer()

data = query.data

user_id = query.from_user.id

if data == "back":
    await query.message.edit_text(
        "🌍 Davlatni tanlang:",
        reply_markup=countries_keyboard(),
    )

elif data.startswith("country_"):
    code = data.replace("country_", "")

    await query.message.edit_text(
        "🏙 Shaharni tanlang:",
        reply_markup=cities_keyboard(code),
    )

elif data.startswith("city_"):
    parts = data.split("_", 2)

    code = parts[1]
    city = parts[2]

    country = COUNTRIES[code]

    user_data[str(user_id)] = {
        "city": city,
        "country": country["api"],
        "country_name": country["name"],
    }

    save_data()

    await query.message.edit_text(
        f"✅ Sizning shahringiz: {city}"
    )

    await context.bot.send_message(
        chat_id=user_id,
        text="📍 Manzil saqlandi.",
        reply_markup=main_keyboard(),
    )
```

# =========================

# NAMOZ

# =========================

async def prayer_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = str(update.effective_user.id)

```
if user_id not in user_data:
    await update.message.reply_text(
        "❌ Avval /start bosing."
    )
    return

info = user_data[user_id]

loading = await update.message.reply_text(
    "⏳ Yuklanmoqda..."
)

data = await fetch_prayer_times(
    info["city"],
    info["country"],
)

if not data:
    await loading.edit_text(
        "❌ API bilan bog'lanishda xatolik."
    )
    return

timings = data["timings"]

gregorian = data["date"]["gregorian"]
hijri = data["date"]["hijri"]

hijri_month = HIJRI_MONTHS[
    int(hijri["month"]["number"]) - 1
]

weekday = WEEKDAYS.get(
    gregorian["weekday"]["en"],
    ""
)

text = f'''
```

🕌 NAMOZ VAQTLARI

📍 {info["city"]}

📅 {weekday}
📆 {gregorian["date"]}
🌙 {hijri["day"]} {hijri_month} {hijri["year"]}

━━━━━━━━━━━━━━

🌅 Bomdod: {clean_time(timings["Fajr"])}
🌄 Quyosh: {clean_time(timings["Sunrise"])}
☀️ Peshin: {clean_time(timings["Dhuhr"])}
🌇 Asr: {clean_time(timings["Asr"])}
🌆 Shom: {clean_time(timings["Maghrib"])}
🌙 Xufton: {clean_time(timings["Isha"])}

━━━━━━━━━━━━━━

⏳ Keyingi namoz:
{calculate_next_prayer(timings)}
'''

```
await loading.edit_text(text)
```

# =========================

# QIBLA

# =========================

async def qibla(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = str(update.effective_user.id)

```
if user_id not in user_data:
    await update.message.reply_text(
        "❌ Avval /start bosing."
    )
    return

info = user_data[user_id]

loading = await update.message.reply_text(
    "🧭 Qibla hisoblanmoqda..."
)

data = await fetch_prayer_times(
    info["city"],
    info["country"],
)

if not data:
    await loading.edit_text(
        "❌ Xatolik yuz berdi."
    )
    return

meta = data["meta"]

lat = float(meta["latitude"])
lon = float(meta["longitude"])

angle = calculate_qibla(lat, lon)

text = f'''
```

🧭 QIBLA TOMONI

📍 {info["city"]}

📐 Burchak: {angle}°

🕋 Ka'ba tomoni:
↖️ Shimoli-g'arb

━━━━━━━━━━━━━━

📍 Latitude: {lat}
📍 Longitude: {lon}
'''

```
await loading.edit_text(text)
```

# =========================

# ABOUT

# =========================

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = str(update.effective_user.id)

```
city = "Tanlanmagan"

if user_id in user_data:
    city = user_data[user_id]["city"]

text = f'''
```

ℹ️ BOT HAQIDA

🕌 Namoz Vaqtlari Bot

📍 Sizning shahringiz:
{city}

⚡ Imkoniyatlar:

• Namoz vaqtlari
• Qibla tomoni
• Hijriy sana
• Mini App
• Tezkor ishlash
'''

```
await update.message.reply_text(text)
```

# =========================

# ADMIN

# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
if update.effective_user.id != ADMIN_ID:
return

```
keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "👥 Foydalanuvchilar",
                callback_data="users",
            )
        ],
        [
            InlineKeyboardButton(
                "📨 Broadcast",
                callback_data="broadcast",
            )
        ],
    ]
)

await update.message.reply_text(
    "⚙️ ADMIN PANEL",
    reply_markup=keyboard,
)
```

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query

```
await query.answer()

if query.from_user.id != ADMIN_ID:
    return

if query.data == "users":
    await query.message.reply_text(
        f"👥 Jami: {len(user_ids)}"
    )

elif query.data == "broadcast":
    context.user_data["broadcast"] = True

    await query.message.reply_text(
        "✍️ Xabar yuboring:"
    )
```

# =========================

# TEXTS

# =========================

async def texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text

```
user_id = update.effective_user.id

user_ids.add(user_id)

save_data()

if context.user_data.get("broadcast"):
    if user_id != ADMIN_ID:
        return

    context.user_data["broadcast"] = False

    success = 0
    failed = 0

    msg = await update.message.reply_text(
        "⏳ Yuborilmoqda..."
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=text,
            )

            success += 1

            await asyncio.sleep(0.05)

        except:
            failed += 1

    await msg.edit_text(
        f"✅ Yuborildi: {success}\n"
        f"❌ Xato: {failed}"
    )

    return

if text == "🕌 Namoz vaqtlari":
    await prayer_times(update, context)

elif text == "🧭 Qibla tomoni":
    await qibla(update, context)

elif text == "⚙️ Shaharni o'zgartirish":
    await update.message.reply_text(
        "🌍 Davlatni tanlang:",
        reply_markup=countries_keyboard(),
    )

elif text == "ℹ️ Bot haqida":
    await about(update, context)
```

# =========================

# ERROR

# =========================

async def error_handler(update, context):
logger.error(f"ERROR: {context.error}")

# =========================

# MAIN

# =========================

async def shutdown():
global session

```
if session:
    await session.close()
```

def main():
load_data()

```
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(
    CallbackQueryHandler(
        admin_callbacks,
        pattern="^(users|broadcast)$",
    )
)

app.add_handler(
    CallbackQueryHandler(callbacks)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        texts,
    )
)

app.add_error_handler(error_handler)

print("✅ Namoz Vaqtlari Bot ishga tushdi")

app.run_polling()
```

if __name__ == "__main__":
main()
