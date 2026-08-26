import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

api_file = sys.argv[1]
msg_file = sys.argv[2]
log_file = sys.argv[3]


def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


# ── WMO Weather Codes → Persian ───────────────────────

WMO_CONDITIONS = {
    0: ("آسمان صاف", "sun"),
    1: ("عمدتاً صاف", "sun"),
    2: ("نیمه‌ابری", "partly_sunny"),
    3: ("ابری", "cloud"),
    45: ("مه‌آلود", "fog"),
    48: ("مه‌آلود با یخبندان", "fog"),
    51: ("نم‌باران سبک", "rain"),
    53: ("نم‌باران متوسط", "rain"),
    55: ("نم‌باران شدید", "rain"),
    56: ("نم‌باران یخ‌زده", "rain"),
    57: ("نم‌باران یخ‌زده شدید", "rain"),
    61: ("بارش سبک", "rain"),
    63: ("بارش متوسط", "rain"),
    65: ("بارش شدید", "rain"),
    66: ("باران یخ‌زده", "rain"),
    67: ("باران یخ‌زده شدید", "rain"),
    71: ("برف سبک", "snow"),
    73: ("برف متوسط", "snow"),
    75: ("برف شدید", "snow"),
    77: ("دانه‌های برف", "snow"),
    80: ("رگبار سبک", "rain"),
    81: ("رگبار متوسط", "rain"),
    82: ("رگبار شدید", "rain"),
    85: ("رگبار برف سبک", "snow"),
    86: ("رگبار برف شدید", "snow"),
    95: ("رعد و برق", "thunder"),
    96: ("رعد و برق با تگرگ", "thunder"),
    99: ("رعد و برق شدید با تگرگ", "thunder"),
}


def wmo_condition(code):
    if code in WMO_CONDITIONS:
        return WMO_CONDITIONS[code]
    return ("نامشخص", "thermometer")


# ── Wind direction degrees → Persian compass ───────────

def wind_dir_fa(deg):
    if deg is None:
        return None

    dirs = [
        ("شمال", 0, 22.5),
        ("شمال شمال شرقی", 22.5, 67.5),
        ("شرقی", 67.5, 112.5),
        ("جنوب شرقی", 112.5, 157.5),
        ("جنوب", 157.5, 202.5),
        ("جنوب غربی", 202.5, 247.5),
        ("غربی", 247.5, 292.5),
        ("شمال غربی", 292.5, 337.5),
    ]

    for name, lo, hi in dirs:
        if deg >= lo and deg < hi:
            return name

    return "شمال"


# ── Persian helpers ────────────────────────────────────

def fa_num(n):
    if n is None:
        return None

    digits = {
        "0": "۰",
        "1": "۱",
        "2": "۲",
        "3": "۳",
        "4": "۴",
        "5": "۵",
        "6": "۶",
        "7": "۷",
        "8": "۸",
        "9": "۹",
    }

    return "".join(digits.get(c, c) for c in str(n))


FA_DAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}


FA_MONTHS = {
    "January": "ژانویه",
    "February": "فوریه",
    "March": "مارس",
    "April": "آوریل",
    "May": "مه",
    "June": "ژوئن",
    "July": "جولای",
    "August": "اوت",
    "September": "سپتامبر",
    "October": "اکتبر",
    "November": "نوامبر",
    "December": "دسامبر",
}


def fa_date(dt):
    en_day = dt.strftime("%A")
    en_month = dt.strftime("%B")

    return (
        f"{FA_DAYS.get(en_day, en_day)}، "
        f"{fa_num(dt.day)} "
        f"{FA_MONTHS.get(en_month, en_month)} "
        f"{fa_num(dt.year)}"
    )


# ── Emoji map ──────────────────────────────────────────

EMOJI_MAP = {
    "thermometer": "\U0001f321",
    "sun": "\u2600",
    "cloud": "\u2601",
    "partly_sunny": "\u26c5",
    "rain": "\U0001f327",
    "thunder": "\u26c8",
    "snow": "\U0001f328",
    "fog": "\U0001f32b",
    "fire": "\U0001f525",
    "wind": "\U0001f32c",
}


# ── Parse Open-Meteo response ──────────────────────────

try:
    with open(api_file, "r", encoding="utf-8") as f:
        data = json.load(f)

except Exception as e:
    log(f"Failed to read API file: {e}")

    with open(msg_file, "w", encoding="utf-8") as f:
        f.write("گزارش آب‌وهوا در دسترس نیست. فردا تلاش مجدد خواهد شد.")

    sys.exit(1)


# ── Validate response structure ─────────────────────────

if "current" not in data or "daily" not in data:
    log("ERROR: Missing current or daily in API response")

    with open(msg_file, "w", encoding="utf-8") as f:
        f.write("داده‌های آب‌وهوا ناقص هستند.")

    sys.exit(1)


# ── Extract values from structured JSON ─────────────────

cur = data["current"]
daily = data["daily"]


# Current conditions
cur_temp = cur.get("temperature_2m")
feels_like = cur.get("apparent_temperature")
humidity = cur.get("relative_humidity_2m")
cur_wmo = cur.get("weather_code")
wind_speed = cur.get("wind_speed_10m")
wind_deg = cur.get("wind_direction_10m")
cur_precip = cur.get("precipitation")


# Today's daily forecast
today_high = (
    daily["temperature_2m_max"][0]
    if daily.get("temperature_2m_max")
    else None
)

today_low = (
    daily["temperature_2m_min"][0]
    if daily.get("temperature_2m_min")
    else None
)

rain_prob = (
    daily["precipitation_probability_max"][0]
    if daily.get("precipitation_probability_max")
    else None
)

precip_sum = (
    daily["precipitation_sum"][0]
    if daily.get("precipitation_sum")
    else None
)

daily_wmo = (
    daily["weather_code"][0]
    if daily.get("weather_code")
    else None
)

sunrise = (
    daily["sunrise"][0]
    if daily.get("sunrise")
    else None
)

sunset = (
    daily["sunset"][0]
    if daily.get("sunset")
    else None
)

max_wind = (
    daily["wind_speed_10m_max"][0]
    if daily.get("wind_speed_10m_max")
    else None
)


# ── Sanity check ────────────────────────────────────────

if cur_temp is not None and (cur_temp < -50 or cur_temp > 60):
    log(f"Temp out of range: {cur_temp}")

    with open(msg_file, "w", encoding="utf-8") as f:
        f.write("داده‌های آب‌وهوا خارج از محدوده معقول هستند.")

    sys.exit(1)


log(
    f"API data: temp={cur_temp} "
    f"feels={feels_like} "
    f"high={today_high} "
    f"low={today_low} "
    f"rain_prob={rain_prob} "
    f"precip={precip_sum} "
    f"humidity={humidity} "
    f"wind={wind_speed}@{wind_deg} "
    f"wmo_cur={cur_wmo} "
    f"wmo_daily={daily_wmo}"
)


# ── Determine condition and emoji ──────────────────────

display_wmo = cur_wmo if cur_wmo is not None else daily_wmo

condition_fa, emoji_name = wmo_condition(display_wmo)

emoji = EMOJI_MAP.get(
    emoji_name,
    EMOJI_MAP["thermometer"]
)


# ── Severe weather warnings ────────────────────────────

warnings = []

if today_high is not None and today_high >= 45:
    warnings.append(("هشدار گرمای شدید", "fire"))

if rain_prob is not None and rain_prob >= 70:
    warnings.append(("احتمال بارش شدید باران", "rain"))

if max_wind is not None and max_wind >= 60:
    warnings.append(("هشدار باد شدید", "wind"))

if display_wmo in (95, 96, 99):
    warnings.append(("هشدار رعد و برق", "thunder"))


# ── Build Persian message ──────────────────────────────

tz = ZoneInfo("Asia/Tehran")

now = datetime.now(tz)

hour = now.hour


if 5 <= hour < 12:
    greeting = "صبح بخیر"

elif 12 <= hour < 17:
    greeting = "ظهر بخیر"

elif 17 <= hour < 21:
    greeting = "عصر بخیر"

else:
    greeting = "شب بخیر"


msg = f"{emoji} {greeting}! گزارش آب‌وهوای قائم‌شهر\n"

msg += (
    f"\U0001f4c5 {fa_date(now)} · "
    f"\u23f0 {fa_num(now.strftime('%H:%M'))}\n"
)


if warnings:
    msg += "\n\u26a0 هشدار آب‌وهوایی\n"

    for text, _ in warnings:
        msg += f"\u26a0 {text}\n"

    msg += "\n"


msg += "\u2501" * 20 + "\n"


if cur_temp is not None:
    msg += f"\U0001f321 دما: {fa_num(round(cur_temp, 1))}°C"

    if feels_like is not None:
        msg += (
            f"\n\U0001f914 دمای احساس‌شده: "
            f"{fa_num(round(feels_like, 1))}°C"
        )

    msg += "\n"


msg += f"{emoji} وضعیت هوا: {condition_fa}\n"


if today_high is not None:
    msg += (
        f"\u2b06 بیشینه: "
        f"{fa_num(round(today_high, 1))}°C\n"
    )


if today_low is not None:
    msg += (
        f"\u2b07 کمینه: "
        f"{fa_num(round(today_low, 1))}°C\n"
    )


msg += "\u2501" * 20 + "\n"


if rain_prob is not None:

    if rain_prob >= 50:
        rain_e = "\U0001f327"

    elif rain_prob >= 20:
        rain_e = "\U0001f326"

    else:
        rain_e = "\U0001f324"

    msg += (
        f"{rain_e} احتمال بارش: "
        f"{fa_num(rain_prob)}٪\n"
    )


if precip_sum is not None and precip_sum > 0:
    msg += (
        f"\U0001f4a7 میزان بارش: "
        f"{fa_num(round(precip_sum, 1))} mm\n"
    )


if humidity is not None:
    msg += (
        f"\U0001f4a7 رطوبت: "
        f"{fa_num(humidity)}٪\n"
    )


fa_dir = wind_dir_fa(wind_deg)


if wind_speed is not None:

    line = (
        f"\U0001f4a8 باد: "
        f"{fa_num(round(wind_speed, 1))} km/h"
    )

    if fa_dir:
        line += f" ({fa_dir})"

    msg += line + "\n"


# ── Sunrise / Sunset ───────────────────────────────────

if sunrise and sunset:

    sr = (
        sunrise.split("T")[1]
        if "T" in sunrise
        else sunrise
    )

    ss = (
        sunset.split("T")[1]
        if "T" in sunset
        else sunset
    )

    msg += (
        f"\U0001f305 طلوع: {fa_num(sr)} · "
        f"غروب: {fa_num(ss)}\n"
    )


# ── Forecast summary & suggestion ──────────────────────

def build_forecast():

    parts = []

    if display_wmo in (0, 1):
        parts.append("آسمان صاف و آفتابی خواهد بود")

    elif display_wmo == 2:
        parts.append("هوا نیمه‌ابری پیش‌بینی می‌شود")

    elif display_wmo == 3:
        parts.append("آسمان غالباً ابری خواهد بود")

    elif display_wmo in (45, 48):
        parts.append("هوا مه‌آلود خواهد بود")

    elif display_wmo in (51, 53, 55, 56, 57):
        parts.append("نم‌باران مورد انتظار است")

    elif display_wmo in (61, 63, 65, 66, 67):
        parts.append("بارش باران پیش‌بینی می‌شود")

    elif display_wmo in (71, 73, 75, 77):
        parts.append("بارش برف مورد انتظار است")

    elif display_wmo in (80, 81, 82):
        parts.append("رگبار مورد انتظار است")

    elif display_wmo in (95, 96, 99):
        parts.append("احتمال رعد و برق وجود دارد")

    else:
        parts.append("شرایط جوی معمولی پیش‌بینی می‌شود")


    if today_high is not None and today_high >= 38:
        parts.append("و هوای بسیار گرمی در انتظار است")

    elif today_high is not None and today_high <= 5:
        parts.append("و هوا سرد خواهد بود")


    if (
        rain_prob is not None
        and rain_prob >= 50
        and display_wmo not in (
            51,
            53,
            55,
            61,
            63,
            65,
            80,
            81,
            82,
            95,
            96,
            99,
        )
    ):
        parts.append("با احتمال بالای بارش")


    return "امروز " + " و ".join(parts) + "."


def build_suggestion():

    if rain_prob is not None and rain_prob >= 50:
        return "\U0001f302 حتماً چتر همراه خود داشته باشید!"

    if display_wmo in (61, 63, 65, 80, 81, 82):
        return "\U0001f302 بهتر است چتر همراه داشته باشید."

    if today_high is not None and today_high >= 40:
        return "\U0001f375 از نوشیدن آب فراوان و ماندن در سایه غافل نشوید."

    if today_high is not None and today_high >= 35:
        return "\U0001f375 آب زیاد بنوشید و از تابش مستقیم آفتاب پرهیز کنید."

    if display_wmo in (71, 73, 75, 85, 86):
        return "\u2744 مراقب لغزندگی جاده‌ها باشید."

    if display_wmo in (45, 48):
        return "\U0001f3a2 در رانندگی احتیاط کنید، دید کاهش یافته است."

    if max_wind is not None and max_wind >= 40:
        return "\U0001f32c از فعالیت‌های فضای باز خودداری کنید."

    if (
        humidity is not None
        and humidity >= 80
        and today_high is not None
        and today_high >= 30
    ):
        return "\U0001f4a7 هوا شرجی است، لباس نخی و سبک بپوشید."

    if today_high is not None and 25 <= today_high < 35:
        return "\u2600 هوای خوبی برای بیرون رفتن است!"

    if today_high is not None and today_high < 10:
        return "\U0001f9e5 لباس گرم فراموش نشود!"

    return None


forecast_text = build_forecast()

suggestion = build_suggestion()


msg += f"\n\U0001f4dd پیش‌بینی:\n{forecast_text}\n"


if suggestion:
    msg += f"\n\U0001f4a1 پیشنهاد:\n{suggestion}\n"


# ── Write final message ────────────────────────────────

with open(msg_file, "w", encoding="utf-8") as f:
    f.write(msg)


log("Message formatted successfully")

log(msg)


print(f"Condition: {condition_fa} (WMO {display_wmo})")
print(f"Temp: {cur_temp}°C, Feels: {feels_like}°C")
print(f"High: {today_high}°C, Low: {today_low}°C")
print(f"Rain prob: {rain_prob}%, Precip: {precip_sum}mm")
print(f"Humidity: {humidity}%, Wind: {wind_speed}km/h @{wind_deg}°")
print(f"Sunrise: {sunrise}, Sunset: {sunset}")