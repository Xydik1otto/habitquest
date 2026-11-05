# PLAN — habitquest (local-first gamified habit tracker)

## 1. Аудиторія

- Люди, які будують звички (спорт, вода, читання, медитація) і кинули 2–3 підписки на трекери.
- Геймери, яких мотивують XP/рівні/стрики (аудиторія Habitica, що не хоче хмару).
- Privacy-conscious користувачі: дані мають залишатися на своїй машині.

Біль: найкращі геймфіковані трекери — підписки або хмара; локальні — без гри.

## 2. MVP scope (цей реліз)

| Функція | Стан |
|---|---|
| Habit: name, icon, schedule (daily/weekly), target_per_period | ✅ |
| CheckIn: habit_id, date, note | ✅ |
| Player: xp, level | ✅ |
| XP за чек-ін зі стрік-множителем | ✅ |
| Рівні з кумулятивними порогами | ✅ |
| Стрик-вогник + freeze token (1/тиждень) | ✅ |
| Досягнення: first week, 30 days, comeback | ✅ |
| Day view з чекбоксами | ✅ |
| Week heatmap (SVG-сітка) | ✅ |
| Stats: найдовша серія, % за 30 днів | ✅ |
| Export/Import JSON | ✅ |

Поза MVP: повторювані звички з часом доби, соцфункції, мобільний додаток, sync між пристроями.

## 3. Архітектура

```
browser (vanilla JS, без build)
   │  fetch /api/*
   ▼
FastAPI (app/main.py)
   ├── db.py            → sqlite3: habits, checkins, freezes, player
   ├── gamification.py  → чисті функції: xp, рівні, серії, досягнення
   └── service.py       → оркестрація чек-інів (bonus XP, freeze, досягнення)
   ▼
static/ (index.html, app.js, style.css)
```

Ключове рішення: вся гейміфікація — чисті функції над `(dates, freezes, today)`,
тому логіка перевіряється тестами без HTTP і без БД.

### Схема БД

- `habits(id, name, icon, schedule, target_per_period, created_at)`
- `checkins(id, habit_id, date, note, UNIQUE(habit_id, date))`
- `freezes(habit_id, date, UNIQUE(habit_id, date))`
- `player(id=1, xp)` — один гравець (локальний single-user застосунок)

## 4. Правила гейміфікації

- **XP**: base 10 × множник `1 + min(streak, 30) × 0.1` (стрик 10 днів → ×2.0).
- **Рівні**: поріг рівня n = `50 × (n-1) × n / 2` XP кумулятивно (L2=50, L3=150, L4=300…).
- **Стрик (daily)**: рахуємо назад від сьогодні (якщо сьогодні ще без чек-іну — від учорашнього дня); freeze-день пропускається, серію не ламає.
- **Стрик (weekly)**: послідовні ISO-тижні, де кількість чек-інів ≥ target_per_period.
- **Freeze token**: 1 на тиждень (ISO-тиждень), списується автоматично при обчисленні серії, якщо день пропущено.
- **Досягнення**: first_week (стрик ≥7), thirty_days (≥30), comeback (чек-ін після паузи ≥3 днів).

## 5. API

- `GET /api/state` — гравець + звички + статус сьогодні/тижня.
- `POST /api/habits`, `DELETE /api/habits/{id}`.
- `POST /api/checkin` {habit_id, date?, note?} / `DELETE /api/checkin/{habit_id}/{date}` (undo).
- `POST /api/freeze` {habit_id, date?} — витратити freeze token на сьогодні.
- `GET /api/heatmap?weeks=12` — сітка тижні×дні.
- `GET /api/stats` — довша серія, % за 30 днів.
- `GET /api/export`, `POST /api/import`.

## 6. Roadmap

- **v0.1 (MVP, поточний)** — усе з таблички вище.
- **v1.0** — квести-«боси» (monthly challenge), іконки-редактор, темна/світла тема.
- **v1.1** — PWA (installable), сповіщення локальні (web notifications).
- **v1.2** — річні heatmap-и, додаткові теми. Roadmap безкоштовний: усі фічі
  open-source, монетизації немає.
- **Статистика днів тижня** — у `/api/stats` додано `weekday_stats`: скільки
  чек-інів припадає на кожен день тижня, найкращий день та середню кількість
  чек-інів за тиждень (v1.x).
- **PDF-звіти** — `GET /api/report.pdf?month=YYYY-MM` віддає місячний рекап
  як PDF (генератор на чистій stdlib, без нових залежностей) (v1.x).
- **Buddy-режим через файл-обмін** — `GET /api/buddy/file` будує портативну
  картку прогресу (лише агрегати: XP, рівень, чек-іни, стрик), а
  `POST /api/buddy/compare` порівнює її з файлом друга; без сервера
  (v1.x, ідея «local co-op» із розділу «Ризики»).

## 7. Roadmap безкоштовний

Проєкт — 100% безкоштовний open-source: усі фічі доступні всім, монетизація
(Sponsors, платні пакети, one-time покупки) не передбачена і не планується.

## 8. Ризики

| Ризик | Мітигація |
|---|---|
| Геймфікація набридає | Легка вага: XP/рівні не блокують жодної функції; heatmap корисний і «вимкнувши гру» |
| Втрата даних | Export/Import JSON + SQLite-файл можна просто скопіювати |
| Single-player нудно | У v1.0 розглядається local co-op через спільний файл (без сервера) |
| SQLite concurrency | Один процес FastAPI, WAL не потрібен для MVP |
| «Ще один трекер» | Фокус на local-first + грі — ніша, яку топ-застосунки не покривають безкоштовно |

## 9. Критерії готовності MVP

- `pytest` проходить: XP/рівні, стрик із freeze, weekly target, досягнення, heatmap, export/import roundtrip, API smoke.
- `uvicorn app.main:app` піднімається, day view дозволяє чек-ін, heatmap малюється.
