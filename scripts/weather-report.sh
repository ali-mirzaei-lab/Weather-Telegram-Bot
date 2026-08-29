#!/bin/bash
# Daily Weather Report for Qaem Shahr, Mazandaran, Iran
# Data source: Open-Meteo API (no web search, no LLM guessing)
# Schedule: GitHub Actions cron '30 6 * * *' UTC (= 10:00 AM Asia/Tehran)

set -euo pipefail

# ── Location ──────────────────────────────────────────
LATITUDE="36.463"
LONGITUDE="52.858"
TIMEZONE="Asia/Tehran"

# ── Paths (portable: resolves relative to this script) ─
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
LOG="$BASE_DIR/weather.log"
MSG_FILE="$BASE_DIR/weather_message.txt"
API_FILE="$BASE_DIR/weather_api.json"

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" >> "$LOG"
}

log "=== Starting weather report ==="

# ──────────────────────────────────────────────────────
# Step 1: Fetch weather from Open-Meteo API
# ──────────────────────────────────────────────────────
log "Fetching from Open-Meteo..."

API_URL="https://api.open-meteo.com/v1/forecast?latitude=${LATITUDE}&longitude=${LONGITUDE}&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,precipitation&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset,wind_speed_10m_max&timezone=${TIMEZONE}&forecast_days=2"

MAX_RETRIES=3
for attempt in $(seq 1 $MAX_RETRIES); do
  HTTP_CODE=$(curl -s -o "$API_FILE" -w "%{http_code}" "$API_URL")
  if [ "$HTTP_CODE" = "200" ] && [ -f "$API_FILE" ] && [ -s "$API_FILE" ]; then
    log "Open-Meteo API success (attempt $attempt)"
    break
  else
    log "Open-Meteo attempt $attempt failed (HTTP $HTTP_CODE)"
    if [ $attempt -lt $MAX_RETRIES ]; then
      sleep $((attempt * 3))
    else
      log "ERROR: All Open-Meteo attempts failed"
      echo "گزارش آب‌وهوا در دسترس نیست. فردا تلاش مجدد خواهد شد." > "$MSG_FILE"
      exit 1
    fi
  fi
done

# ──────────────────────────────────────────────────────
# Step 2: Format the Persian weather report
# ──────────────────────────────────────────────────────
log "Formatting message..."

python3 "$BASE_DIR/format_weather.py" "$API_FILE" "$MSG_FILE" "$LOG"
PY_EXIT=$?

rm -f "$API_FILE"

if [ $PY_EXIT -ne 0 ]; then
  log "ERROR: Formatting failed (exit $PY_EXIT)"
  exit 1
fi

log "=== Weather report completed ==="

# ──────────────────────────────────────────────────────
# Step 3: Send to Telegram
# ──────────────────────────────────────────────────────
send_telegram() {
  local token="${TELEGRAM_TOKEN:-}"
  local chat_ids="${TELEGRAM_CHAT_IDS:-}"

  if [ -z "$token" ]; then
    log "ERROR: TELEGRAM_TOKEN is not set."
    echo "ERROR: TELEGRAM_TOKEN environment variable is not set."
    return 1
  fi

if [ -z "$chat_ids" ]; then
  log "ERROR: TELEGRAM_CHAT_IDS is not set."
  echo "ERROR: TELEGRAM_CHAT_IDS environment variable is not set."
  return 1
fi

  if [ ! -f "$MSG_FILE" ] || [ ! -s "$MSG_FILE" ]; then
    log "ERROR: No message file."
    echo "ERROR: Weather report was not generated."
    return 1
  fi

  log "Sending to Telegram..."

  local success_count=0
local failure_count=0

IFS=',' read -ra recipients <<< "$chat_ids"

for chat_id in "${recipients[@]}"; do
  chat_id="$(echo "$chat_id" | xargs)"

  if [ -z "$chat_id" ]; then
    continue
  fi

  log "Sending to Telegram chat ID: $chat_id"

  local json_payload
  json_payload=$(python3 -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    text = f.read()
payload = {'chat_id': int(sys.argv[2]), 'text': text}
print(json.dumps(payload, ensure_ascii=False))
" "$MSG_FILE" "$chat_id")

  local response
  response=$(curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "$json_payload")

  local curl_exit=$?

  if [ $curl_exit -ne 0 ]; then
    log "ERROR: curl failed for chat $chat_id"
    failure_count=$((failure_count + 1))
    continue
  fi

  local ok
  ok=$(echo "$response" | python3 -c \
    "import sys,json; print(json.load(sys.stdin).get('ok',''))" \
    2>/dev/null || echo "")

  if [ "$ok" = "True" ]; then
    log "Sent successfully to chat $chat_id"
    success_count=$((success_count + 1))
  else
    local err_desc
    err_desc=$(echo "$response" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    print(r.get('description', 'Unknown error'))
except:
    print('Could not parse Telegram response')
" 2>/dev/null || echo "Could not parse response")

    log "ERROR: Telegram API error for $chat_id: $err_desc"
    failure_count=$((failure_count + 1))
  fi
done

log "Telegram results: $success_count successful, $failure_count failed"

if [ "$success_count" -gt 0 ]; then
  echo "Weather report sent to $success_count Telegram recipient(s)."
  return 0
else
  echo "ERROR: Failed to send weather report to any Telegram recipient."
  return 1
fi
}

send_telegram

# ── Send weekly forecast ──────────────────────────────
echo "Sending weekly forecast..."
python3 "$BASE_DIR/weekly_report.py"
WEEKLY_EXIT=$?

if [ $WEEKLY_EXIT -ne 0 ]; then
    log "ERROR: Weekly forecast failed (exit $WEEKLY_EXIT)"
fi

exit 0