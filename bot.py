import os
import requests
from datetime import datetime
from collections import defaultdict
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8744874796:AAFI8MT0C6w_1bhGRo8ppxYsmQTfISoPA6U")
OWM_API_KEY = os.environ.get("OWM_API_KEY", "a90a46dc178142b299baaa5eb82c179b")

# Rate limiting: max 10 requests per minute per user
user_requests = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 60

WEATHER_EMOJI = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️",
    "Drizzle": "🌦️", "Thunderstorm": "⛈️", "Snow": "❄️",
    "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️", "Smoke": "🌫️",
    "Dust": "🌪️", "Sand": "🌪️", "Ash": "🌋", "Squall": "🌬️",
    "Tornado": "🌪️",
}

def check_rate_limit(user_id: int) -> bool:
    now = datetime.now().timestamp()
    reqs = user_requests[user_id]
    # Remove old requests outside window
    user_requests[user_id] = [t for t in reqs if now - t < RATE_WINDOW]
    if len(user_requests[user_id]) >= RATE_LIMIT:
        return False
    user_requests[user_id].append(now)
    return True

def format_weather(d: dict, location_label: str) -> str:
    temp = round(d["main"]["temp"])
    feels = round(d["main"]["feels_like"])
    humidity = d["main"]["humidity"]
    desc = d["weather"][0]["description"].capitalize()
    main = d["weather"][0]["main"]
    wind = round(d["wind"]["speed"] * 3.6)
    visibility = d.get("visibility", 0) // 1000
    clouds = d["clouds"]["all"]
    emoji = WEATHER_EMOJI.get(main, "🌡️")

    tz_offset = d.get("timezone", 0)
    sunrise = datetime.utcfromtimestamp(d["sys"]["sunrise"] + tz_offset).strftime("%H:%M")
    sunset = datetime.utcfromtimestamp(d["sys"]["sunset"] + tz_offset).strftime("%H:%M")

    # UV & air quality rough estimate from clouds
    uv_hint = "Thấp ☁️" if clouds > 70 else ("Cao ⚠️" if clouds < 20 else "Trung bình")

    return (
        f"{emoji} *Thời tiết tại {location_label}*\n"
        f"{'─' * 30}\n"
        f"🌡️ Nhiệt độ: *{temp}°C* (cảm giác *{feels}°C*)\n"
        f"💧 Độ ẩm: *{humidity}%*\n"
        f"💨 Gió: *{wind} km/h*\n"
        f"☁️ Mây phủ: *{clouds}%*\n"
        f"👁️ Tầm nhìn: *{visibility} km*\n"
        f"☀️ UV: *{uv_hint}*\n"
        f"📋 Mô tả: *{desc}*\n"
        f"{'─' * 30}\n"
        f"🌅 Bình minh: {sunrise}  |  🌇 Hoàng hôn: {sunset}\n"
        f"\n_📡 Dữ liệu thực từ OpenWeatherMap_"
    )

def get_weather_by_city(city: str) -> str:
    # Map common Vietnamese city names to English
    vn_map = {
        "hà nội": "Hanoi", "ha noi": "Hanoi",
        "hồ chí minh": "Ho Chi Minh", "ho chi minh": "Ho Chi Minh",
        "sài gòn": "Ho Chi Minh", "sai gon": "Ho Chi Minh", "saigon": "Ho Chi Minh",
        "đà nẵng": "Da Nang", "da nang": "Da Nang",
        "huế": "Hue", "hue": "Hue",
        "cần thơ": "Can Tho", "can tho": "Can Tho",
        "nha trang": "Nha Trang",
        "đà lạt": "Da Lat", "da lat": "Da Lat", "dalat": "Da Lat",
        "phú quốc": "Phu Quoc", "phu quoc": "Phu Quoc",
        "sapa": "Sa Pa", "sa pa": "Sa Pa",
        "hải phòng": "Hai Phong", "hai phong": "Hai Phong",
        "vũng tàu": "Vung Tau", "vung tau": "Vung Tau",
        "quảng ninh": "Quang Ninh", "quang ninh": "Quang Ninh",
        "bình dương": "Binh Duong", "binh duong": "Binh Duong",
        "đồng nai": "Dong Nai", "dong nai": "Dong Nai",
        # Quận/huyện TPHCM
        "quận 1": "Ho Chi Minh", "quan 1": "Ho Chi Minh", "q1": "Ho Chi Minh",
        "quận 2": "Ho Chi Minh", "quan 2": "Ho Chi Minh", "q2": "Ho Chi Minh",
        "quận 3": "Ho Chi Minh", "quan 3": "Ho Chi Minh", "q3": "Ho Chi Minh",
        "quận 4": "Ho Chi Minh", "quan 4": "Ho Chi Minh", "q4": "Ho Chi Minh",
        "quận 5": "Ho Chi Minh", "quan 5": "Ho Chi Minh", "q5": "Ho Chi Minh",
        "quận 6": "Ho Chi Minh", "quan 6": "Ho Chi Minh", "q6": "Ho Chi Minh",
        "quận 7": "Ho Chi Minh", "quan 7": "Ho Chi Minh", "q7": "Ho Chi Minh",
        "quận 8": "Ho Chi Minh", "quan 8": "Ho Chi Minh", "q8": "Ho Chi Minh",
        "quận 9": "Ho Chi Minh", "quan 9": "Ho Chi Minh", "q9": "Ho Chi Minh",
        "quận 10": "Ho Chi Minh", "quan 10": "Ho Chi Minh", "q10": "Ho Chi Minh",
        "quận 11": "Ho Chi Minh", "quan 11": "Ho Chi Minh", "q11": "Ho Chi Minh",
        "quận 12": "Ho Chi Minh", "quan 12": "Ho Chi Minh", "q12": "Ho Chi Minh",
        "thủ đức": "Thu Duc", "thu duc": "Thu Duc",
        "bình thạnh": "Ho Chi Minh", "binh thanh": "Ho Chi Minh",
        "tân bình": "Ho Chi Minh", "tan binh": "Ho Chi Minh",
        "gò vấp": "Ho Chi Minh", "go vap": "Ho Chi Minh",
        "phú nhuận": "Ho Chi Minh", "phu nhuan": "Ho Chi Minh",
        "bình tân": "Ho Chi Minh", "binh tan": "Ho Chi Minh",
        "tân phú": "Ho Chi Minh", "tan phu": "Ho Chi Minh",
        "hóc môn": "Ho Chi Minh", "hoc mon": "Ho Chi Minh",
        "củ chi": "Ho Chi Minh", "cu chi": "Ho Chi Minh",
        "nhà bè": "Ho Chi Minh", "nha be": "Ho Chi Minh",
        "bình chánh": "Ho Chi Minh", "binh chanh": "Ho Chi Minh",
        "cần giờ": "Ho Chi Minh", "can gio": "Ho Chi Minh",
    }
    
    city_en = vn_map.get(city.lower().strip(), city)
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_en, "appid": OWM_API_KEY, "units": "metric", "lang": "vi"}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 404:
            return (
                f"❌ Không tìm thấy *{city}*.\n\n"
                f"💡 *Thử:*\n"
                f"• Tên tiếng Anh: `Hanoi`, `Ho Chi Minh`, `Da Nang`\n"
                f"• Hoặc nhấn 📍 gửi vị trí GPS để chính xác nhất!\n"
                f"Gõ /location để hiện nút GPS"
            )
        if r.status_code == 401:
            return "❌ API key lỗi. Liên hệ admin."
        r.raise_for_status()
        d = r.json()
        label = f"{d['name']}, {d['sys']['country']}"
        # If user searched by district, note that it's city-level data
        if city_en != city and city_en == "Ho Chi Minh":
            label += f"\n_(khu vực {city})_"
        return format_weather(d, label)
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

def get_weather_by_coords(lat: float, lon: float) -> tuple[str, str]:
    """Returns (weather_text, area_name)"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric", "lang": "vi"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        d = r.json()

        # Reverse geocode for detailed address
        geo_url = "https://api.openweathermap.org/geo/1.0/reverse"
        geo_params = {"lat": lat, "lon": lon, "limit": 1, "appid": OWM_API_KEY}
        geo_r = requests.get(geo_url, params=geo_params, timeout=10)
        
        area_name = d["name"]
        if geo_r.status_code == 200:
            geo_data = geo_r.json()
            if geo_data:
                g = geo_data[0]
                parts = []
                # Try to get local names
                local = g.get("local_names", {})
                name = local.get("vi") or local.get("en") or g.get("name", "")
                if name:
                    parts.append(name)
                state = g.get("state", "")
                if state:
                    parts.append(state)
                country = g.get("country", "")
                if country:
                    parts.append(country)
                if parts:
                    area_name = ", ".join(parts)

        label = f"📍 {area_name}\n_(tọa độ: {lat:.4f}, {lon:.4f})_"
        return format_weather(d, label), area_name
    except Exception as e:
        return f"❌ Lỗi: {str(e)}", ""

def get_forecast_by_city(city: str) -> str:
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": OWM_API_KEY, "units": "metric", "lang": "vi", "cnt": 24}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 404:
            return f"❌ Không tìm thấy *{city}*."
        r.raise_for_status()
        d = r.json()
        name = d["city"]["name"]
        country = d["city"]["country"]
        return format_forecast(d["list"], f"{name}, {country}")
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

def get_forecast_by_coords(lat: float, lon: float) -> str:
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"lat": lat, "lon": lon, "appid": OWM_API_KEY, "units": "metric", "lang": "vi", "cnt": 24}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        d = r.json()
        name = d["city"]["name"]
        return format_forecast(d["list"], f"📍 {name}")
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

def format_forecast(items: list, label: str) -> str:
    lines = [f"📅 *Dự báo 3 ngày — {label}*\n{'─'*30}"]
    seen = {}
    for item in items:
        dt = datetime.utcfromtimestamp(item["dt"])
        day_key = dt.strftime("%Y-%m-%d")
        if day_key in seen or len(seen) >= 3:
            continue
        seen[day_key] = True
        day_label = dt.strftime("%A, %d/%m")
        temp_min = round(item["main"]["temp_min"])
        temp_max = round(item["main"]["temp_max"])
        desc = item["weather"][0]["description"].capitalize()
        main = item["weather"][0]["main"]
        emoji = WEATHER_EMOJI.get(main, "🌡️")
        rain = round(item.get("pop", 0) * 100)
        wind = round(item["wind"]["speed"] * 3.6)
        lines.append(
            f"{emoji} *{day_label}*\n"
            f"   🌡️ {temp_min}–{temp_max}°C  |  {desc}\n"
            f"   🌧️ Mưa: {rain}%  |  💨 Gió: {wind} km/h"
        )
    return "\n\n".join(lines)

# ── Handlers ────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Show location button
    kb = [[KeyboardButton("📍 Gửi vị trí của tôi", request_location=True)]]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text(
        "🌤️ *Bot Thời Tiết AI*\n\n"
        "Bạn có thể:\n"
        "• Gõ tên thành phố/quận: `Hanoi`, `Quan 7`\n"
        "• Nhấn 📍 bên dưới để gửi vị trí GPS *chính xác đến từng km*\n\n"
        "📋 *Lệnh:*\n"
        "/weather `<nơi>` — Thời tiết hiện tại\n"
        "/forecast `<nơi>` — Dự báo 3 ngày\n"
        "/location — Hiện nút gửi vị trí GPS",
        parse_mode="Markdown",
        reply_markup=markup
    )

async def location_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("📍 Gửi vị trí của tôi", request_location=True)]]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text(
        "📍 Nhấn nút bên dưới để gửi vị trí GPS — bot sẽ báo thời tiết *chính xác khu vực bạn đang đứng!*",
        parse_mode="Markdown",
        reply_markup=markup
    )

async def handle_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Bạn hỏi quá nhiều! Thử lại sau 1 phút.")
        return

    lat = update.message.location.latitude
    lon = update.message.location.longitude

    msg = await update.message.reply_text("🔍 Đang lấy thời tiết tại vị trí của bạn...")
    weather_text, area_name = get_weather_by_coords(lat, lon)
    
    # Offer forecast follow-up
    kb = [[KeyboardButton("📍 Gửi vị trí của tôi", request_location=True)]]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    await msg.edit_text(weather_text, parse_mode="Markdown")
    
    if area_name:
        await update.message.reply_text(
            f"📅 Xem dự báo 3 ngày: /forecast\\_gps\nHoặc gõ: `/forecast {area_name}`",
            parse_mode="Markdown",
            reply_markup=markup
        )

async def weather_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Bạn hỏi quá nhiều! Thử lại sau 1 phút.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "📍 Dùng: `/weather <thành phố>`\nVí dụ: `/weather Hanoi`\n\nHoặc gửi vị trí GPS để chính xác hơn! /location",
            parse_mode="Markdown"
        )
        return
    city = " ".join(ctx.args)
    msg = await update.message.reply_text(f"🔍 Đang tìm *{city}*...", parse_mode="Markdown")
    result = get_weather_by_city(city)
    await msg.edit_text(result, parse_mode="Markdown")

async def forecast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Bạn hỏi quá nhiều! Thử lại sau 1 phút.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "📍 Dùng: `/forecast <thành phố>`\nHoặc gửi vị trí GPS /location",
            parse_mode="Markdown"
        )
        return
    city = " ".join(ctx.args)
    msg = await update.message.reply_text(f"📅 Đang lấy dự báo *{city}*...", parse_mode="Markdown")
    result = get_forecast_by_city(city)
    await msg.edit_text(result, parse_mode="Markdown")

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Bạn hỏi quá nhiều! Thử lại sau 1 phút.")
        return
    msg = await update.message.reply_text(f"🔍 Đang tìm *{text}*...", parse_mode="Markdown")
    result = get_weather_by_city(text)
    await msg.edit_text(result, parse_mode="Markdown")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("location", location_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(CommandHandler("forecast", forecast_cmd))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Bot đang chạy...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
