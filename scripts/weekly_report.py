import json
import requests
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Load .env file ─────────────────────────────────────

def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value.strip())

load_env()

# ── Config ─────────────────────────────────────────────

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS", "")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

LATITUDE = "36.463"
LONGITUDE = "52.858"
TIMEZONE = "Asia/Tehran"

# ── WMO Codes & Emojis ─────────────────────────────────

WMO_CONDITIONS = {
    0: ("آسمان صاف", "☀️"),
    1: ("عمدتاً صاف", "🌤️"),
    2: ("نیمه‌ابری", "⛅"),
    3: ("ابری", "☁️"),
    45: ("مه‌آلود", "🌫️"),
    48: ("مه‌آلود با یخبندان", "🌫️"),
    51: ("نم‌باران سبک", "🌧️"),
    53: ("نم‌باران متوسط", "🌧️"),
    55: ("نم‌باران شدید", "🌧️"),
    61: ("بارش سبک", "🌧️"),
    63: ("بارش متوسط", "🌧️"),
    65: ("بارش شدید", "🌧️"),
    71: ("برف سبک", "❄️"),
    73: ("برف متوسط", "❄️"),
    75: ("برف شدید", "❄️"),
    80: ("رگبار سبک", "🌧️"),
    81: ("رگبار متوسط", "🌧️"),
    82: ("رگبار شدید", "🌧️"),
    95: ("رعد و برق", "⛈️"),
    96: ("رعد و برق با تگرگ", "⛈️"),
    99: ("رعد و برق شدید با تگرگ", "⛈️"),
}

FA_DAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}

def fa_num(n):
    digits = {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴",
              "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"}
    return "".join(digits.get(c, c) for c in str(n))

# ── Fetch Weather ──────────────────────────────────────

def fetch_weather():
    url = (f"https://api.open-meteo.com/v1/forecast?"
           f"latitude={LATITUDE}&longitude={LONGITUDE}"
           f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           f"&timezone={TIMEZONE}&forecast_days=7")
    
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()

# ── Build Weekly Forecast Text ─────────────────────────

def build_weekly_text(data):
    daily = data.get("daily", {})
    days = daily.get("time", [])
    codes = daily.get("weather_code", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    rain_probs = daily.get("precipitation_probability_max", [])
    
    lines = ["📅 پیش‌بینی هفته آینده:\n"]
    
    for i in range(len(days)):
        dt = datetime.fromisoformat(days[i])
        day_name = FA_DAYS.get(dt.strftime("%A"), dt.strftime("%A"))
        
        wmo = codes[i] if i < len(codes) else None
        emoji = WMO_CONDITIONS.get(wmo, ("", "🌡️"))[1]
        
        low = lows[i] if i < len(lows) else None
        high = highs[i] if i < len(highs) else None
        rain = rain_probs[i] if i < len(rain_probs) else None
        
        line = f"{emoji} {day_name}: "
        if low is not None:
            line += f"{fa_num(round(low))}°"
        line += " / "
        if high is not None:
            line += f"{fa_num(round(high))}°"
        
        if rain is not None and rain >= 20:
            line += f" ({fa_num(rain)}% 🌧️)"
        
        lines.append(line)
    
    return "\n".join(lines)

# ── Send to Telegram ───────────────────────────────────

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_ids = os.environ.get("TELEGRAM_CHAT_IDS", "")
    
    if not token or not chat_ids:
        print("ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_IDS")
        sys.exit(1)
    
    for chat_id in chat_ids.split(","):
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        
        payload = {
            "chat_id": int(chat_id),
            "text": text,
            "parse_mode": "HTML"
        }
        
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=30
        )
        
        if resp.status_code == 200:
            print(f"Sent to {chat_id}")
        else:
            print(f"Failed to send to {chat_id}: {resp.text}")

# ── Main ───────────────────────────────────────────────

def main():
    print("Fetching weekly forecast...")
    data = fetch_weather()
    text = build_weekly_text(data)
    print(text)
    send_telegram(text)
    print("Weekly forecast sent!")

if __name__ == "__main__":
    main()