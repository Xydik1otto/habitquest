# ⚔️ HabitQuest

![tests](https://img.shields.io/badge/tests-153%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-gold)
![status](https://img.shields.io/badge/version-0.4.0-orange)

**Local-first gamified habit tracker** — habits as an RPG: XP, levels, streaks with
«freezes», monthly **boss battles**, a **shield shop** and monthly recaps. Fully local:
no subscriptions, no cloud accounts. *(Українська версія: [README.md](README.md).)*

> 📸 *Screenshot placeholders:*
> `![Day view](docs/screenshots/day-view.png)` — day view with checkboxes and streak flames 🔥/❄
> `![Boss battle](docs/screenshots/boss-battle.png)` — monthly boss with an HP bar (progress = damage)
> `![Recap](docs/screenshots/recap.png)` — monthly recap with charts

## The problem

- Health & Wellness is the fastest-growing app category; habit trackers consistently rank high in search.
- Subscription fatigue: most trackers charge $4–6/month for CRUD over your own local data.
- Game mechanics retain better than plain lists, but the top players (Habitica, Streaks) are cloud-only or paywalled.

## Why it exists

The classic habit-formation study (Lally et al., 2010, *European Journal of Social
Psychology*, "How are habits formed: Modelling habit formation in the real world") showed
two things that shape HabitQuest's design:

1. **Automaticity takes on average 66 days** (median; range 18–254) — that's why the game
   operates on long horizons: 30-day streak charts, monthly boss battles, long streaks with
   an XP multiplier, not "21 days and you're done".
2. **One missed day doesn't ruin habit formation** — that's why HabitQuest has freeze tokens
   and shields: breaking a streak because of illness or travel is not a loss, and the system
   doesn't punish you for being human.

And the key point: rewards only matter when the data is yours. Hence local-first SQLite,
one-click JSON export and zero subscriptions.

## The solution

Python **FastAPI + SQLite + vanilla JS** (no build step). Zero external services.
Data is exported/imported as a single JSON file. **PWA**: installs on phone/desktop,
static assets are cached (offline shell).

### Gamification

- **XP per check-in** with a streak multiplier `1 + min(streak,30)×0.1` — longer streak → more XP.
- **Levels**: cumulative thresholds `50×n(n+1)/2` (L2=50, L3=150, L4=300…).
- **Streak flame** ❄/🔥; 1 **freeze token** per week "freezes" a missed day.
- **🛡 Shield shop**: earned XP → coins; a shield (50 💰) = an extra freeze token when the
  free weekly one is spent.
- **👹 Monthly boss battle**: a monthly goal "do habit N times" → a boss with
  **HP = N×10**; every check-in deals damage equal to the XP it earned (longer streak —
  stronger hit). Victory → **+100 XP bonus** + a collectible **badge**.
- **Achievements from JSON** (`app/achievements.json`) — templates for the Pro Pack:
  add your own `{id, name, description, metric, threshold}` object via the UI editor
  and it just works.
- **Habit categories**: 💚 health / 🧠 mind / 💼 work / 🏠 home — with UI filters.
- **📅 Weekly quests**: 3 habits × 5 check-ins per week → one-time reward of 150 💰.
- **🔊 Sound + ✨ effects**: WebAudio blip on check-in, level-up confetti — both can be
  disabled in settings.

### Views

1. **Day view** — today's habits with checkboxes (daily) and weekly progress (weekly),
   category filters, a 📈 30-day streak chart per habit.
2. **Boss battle** — the monthly monster's HP bar; progress = damage dealt.
3. **Weekly quest** — progress bars for the three habits of the week.
4. **Dashboard** — 30-day XP SVG chart, coins, shields, level.
5. **Week heatmap** — an SVG "weeks × days" grid.
6. **Monthly recap** — check-ins, longest streak, XP earned/spent, best day,
   per-category breakdown, weekly bar chart, bosses defeated.
7. **Achievements editor** + stats + badges + shop + settings.

### Data portability

`GET /api/export` → JSON (including quests, badges and the XP log);
`POST /api/import` → full restore. Your data always stays yours.

## Quick start

```bash
cd habitquest
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# http://127.0.0.1:8000  →  "Install" as a PWA from the browser menu

pytest              # 153 tests
./scripts/smoke.sh  # quick API smoke test (PASS/FAIL)
```

## API (briefly)

`/api/state` · `POST /api/habits` · `POST /api/checkin` · `DELETE /api/checkin/{h}/{d}` ·
`GET /api/habits/{id}/series` · `/api/freeze` · `POST /api/quests` · `/api/weekly-quests` ·
`/api/shop` + `POST /api/shop/buy` · `/api/badges` · `/api/recap?month=YYYY-MM` ·
`/api/dashboard` · `/api/heatmap` · `/api/stats` · `/api/settings` ·
`/api/achievements` (+ POST/PUT — editor) · `/api/export` · `/api/import`

## Roadmap

- [x] MVP: XP/levels/streaks/freeze/achievements/heatmap/export-import
- [x] v0.1.0-alpha: boss quests, PWA, JSON achievements
- [x] v0.2.x: shield shop, detailed boss battles, categories, monthly recap
- [x] v0.4.0: streak charts, weekly quests, sound/effects, dashboard, achievements editor
- [ ] v1.0: icon editor, dark/light theme, yearly heatmaps
- [ ] Pro Pack (one-time): extra themes, custom achievements, yearly reports

## License

MIT — see [LICENSE](LICENSE). 100% local: no telemetry, no accounts, no cloud.
