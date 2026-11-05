#!/usr/bin/env bash
# Smoke test: запускає uvicorn на випадковому порту, перевіряє головні ендпоінти,
# завершує сервер і виводить PASS/FAIL. Без Docker, тільки python + curl.
set -u
cd "$(dirname "$0")/.."

PORT=${SMOKE_PORT:-$(( (RANDOM % 2000) + 8000 ))}
BASE="http://127.0.0.1:$PORT"

python -m uvicorn app.main:app --port "$PORT" --log-level warning &
PID=$!
trap 'kill $PID 2>/dev/null; wait $PID 2>/dev/null' EXIT

# чекаємо на готовність (до 15 с)
ready=0
for _ in $(seq 1 30); do
  if curl -sf "$BASE/api/stats" >/dev/null 2>&1; then ready=1; break; fi
  sleep 0.5
done
if [ "$ready" -ne 1 ]; then
  echo "SMOKE: FAIL (server did not start on port $PORT)"
  exit 1
fi

fail=0
check() { # $1 = path, $2 = очікуваний текст
  if curl -sf "$BASE$1" | grep -q "$2"; then
    echo "PASS $1"
  else
    echo "FAIL $1"
    fail=1
  fi
}

check "/" "HabitQuest"
check "/manifest.json" "HabitQuest"
check "/static/app.js" "serviceWorker"
check "/static/icons/favicon.svg" "svg"
check "/api/state" "player"
check "/api/stats" "longest_streak"
check "/api/heatmap" "weeks"
check "/api/achievements" "first_checkin"
check "/api/dashboard" "xp_by_day"
check "/api/weekly-quests" "weekly_quests"
check "/api/settings" "sound"
check "/api/shop" "shield_price"

if [ "$fail" -eq 0 ]; then
  echo "SMOKE: PASS"
else
  echo "SMOKE: FAIL"
fi
exit $fail
