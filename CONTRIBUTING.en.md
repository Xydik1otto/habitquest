# Contributing / Contributor guide

Thank you for your interest in **HabitQuest**! The project is local-first and
minimal-by-design, so every contribution follows a simple but strict path.

Дякуємо за інтерес до **HabitQuest**! Проєкт — local-first і minimal-by-design,
тому будь-який внесок проходить простий, але суворий шлях.

> Українська версія: [CONTRIBUTING.md](CONTRIBUTING.md)

## Contents / Зміст

1. [Architecture](#architecture--архітектура)
2. [Environment & tests](#environment--tests--середовище-та-тести)
3. [How to add a habit template](#how-to-add-a-habit-template-templatesjson)
4. [How to add an achievement](#how-to-add-an-achievement-achievementsjson)
5. [Branches](#branches--гілки)
6. [PRs & commit style](#prs--commit-style--pr-та-стиль-комітів)
7. [Languages & i18n](#languages--i18n--мови-та-i18n)
8. [Mobile port](#mobile-port--мобільний-порт)
9. [License](#license--ліцензія)

## How you can help / Як допомогти

- 🐛 Bug reports — via the [issue template](.github/ISSUE_TEMPLATE/bug_report.md).
- 💡 Feature proposals — via the [template](.github/ISSUE_TEMPLATE/feature_request.md).
- 🔒 Security — **privately**, see [SECURITY.md](SECURITY.md). Do not open a public issue.
- 🌍 Translations — **Ukrainian and English only** (see below).
- 📚 Content: habit templates (`app/templates.json`), achievements
  (`app/achievements.json`), quotes (`app/quotes.json`) — the easiest way to
  make a first contribution.
- 📝 Documentation: README, README.en.md, INSTALL.md.

## Architecture / Архітектура

The project is deliberately flat: four layers, no frameworks beyond FastAPI.

```
static/            UI (vanilla JS + CSS + service worker, PWA) — no build step
app/main.py        FastAPI: thin HTTP routes — validation + service calls only
app/service.py     Service layer: orchestrates check-ins, freezes, XP, quests, bosses
app/gamification.py  PURE functions: XP/levels/streaks/battles/achievements (no HTTP, no DB)
app/db.py          SQLite storage (stdlib sqlite3, no ORM)
app/templates.json | quotes.json | achievements.json | i18n.json — data & dictionaries
tests/             pytest (~30 files, 179 tests)
```

Key architecture rules:

- **`app/gamification.py` is pure functions.** No HTTP, no DB access, no global
  state, no "ambient" time: everything takes `date`/numbers/collections as
  arguments. That is what makes this logic easy to unit-test. Balance constants
  (BASE_XP, STREAK_CAP, SHIELD_PRICE, QUEST_BONUS_XP…) live at the top of the file.
- **`app/service.py` is the service layer.** The single place that combines the
  database with gamification: quest creation, boss battles, weekly quests,
  XP accrual for check-ins. HTTP handlers in `main.py` contain no business logic.
- **`app/db.py` is SQLite.** Stdlib `sqlite3`, no ORM. The schema is the `SCHEMA`
  string at the top of the file. There are no migrations: change the schema
  carefully and keep it backwards compatible.
- **`static/` is the UI.** Vanilla JS, no npm build for the web version
  (node_modules is only needed for the Capacitor mobile platforms on the
  `mobile/android-ios` branch). All visible strings go through i18n
  (see "Languages & i18n").
- **Data lives in JSON, not in code.** Habit templates, quotes and achievements
  are plain JSON files in `app/`, validated by dedicated functions
  (`validate_template`, `validate_achievement_def`) and dedicated tests.
  Content contributions require no Python knowledge.

## Environment & tests / Середовище та тести

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # or pip install -r requirements.txt
pytest                                  # must be green BEFORE your changes
```

- CI runs pytest on Python 3.12–3.14.
- The full suite is **179 tests** and must stay green.
- Run a single file quickly: `pytest tests/test_streaks.py -q`.
- Fixtures in `tests/conftest.py` give you a temporary DB (`tmp_path`) and a
  TestClient with a patched `DB_PATH` — copy that pattern in new tests.
- The privacy test (`tests/test_oss_hygiene.py`) scans tracked files for
  paths/tokens/personal data and for **Russian-specific letters** — your patch
  must pass it.

## How to add a habit template (templates.json)

Templates are the ready-made habits of the "New Year onboarding" library in
`app/templates.json`. File format:

```json
{
  "_comment": "Habit template library. Fields: id, icon, name_ua, name_en, category (health|mind|work|home), schedule (daily|weekly), target_per_period.",
  "templates": [
    { "id": "water", "icon": "💧", "name_ua": "Пити воду", "name_en": "Drink water",
      "category": "health", "schedule": "daily", "target_per_period": 1 }
  ]
}
```

Step by step:

1. Open `app/templates.json` and add a new object to the `templates` array.
2. Fill in **all** fields:
   - `id` — Latin, unique, snake_case (`cold_shower`);
   - `icon` — a single emoji;
   - `name_ua` / `name_en` — the name in Ukrainian and in English (both required);
   - `category` — one of `health | mind | work | home`;
   - `schedule` — `daily` or `weekly`;
   - `target_per_period` — an integer from 1 to 7.
3. Do not forget the English name — the validator rejects a template without `name_en`.
4. Add/update a test in `tests/test_templates.py`: make sure the template-count
   test passes with your new row (field validation is done by `validate_template`).
5. Run `pytest tests/test_templates.py -q`, then the full `pytest`.

## How to add an achievement (achievements.json)

Custom achievements are declared declaratively in `app/achievements.json`:

```json
{
  "_comment": "Add objects with fields id, name, description, metric (streak | total_checkins | gap_days), threshold.",
  "achievements": [
    { "id": "first_week", "name": "Перший тиждень", "description": "Серія 7 днів",
      "metric": "streak", "threshold": 7 }
  ]
}
```

Fields:

- `id` — unique, snake_case;
- `name`, `description` — human-readable names (keep the description short and
  language-neutral);
- `metric` — what is measured, exactly one of:
  - `streak` — the current consecutive-day streak;
  - `total_checkins` — the total number of check-ins;
  - `gap_days` — the pause between check-ins (a comeback after a break of ≥ threshold days);
- `threshold` — an integer **≥ 1** (0 and negative values are rejected).

Step by step:

1. Add an object to the `achievements` array with all five fields.
2. Make sure `metric` is only `streak | total_checkins | gap_days` and
   `threshold ≥ 1` — this is exactly what `validate_achievement_def` in
   `app/gamification.py` checks.
3. Add a test in `tests/test_achievements_json.py`:

   ```python
   def test_my_achievement():
       defs = DEFS + [{"id": "hundred_days", "name": "Сто днів", "description": "100 днів поспіль",
                       "metric": "streak", "threshold": 100}]
       got = g.evaluate_custom_achievements(defs, streak=100, total_checkins=0, last_gap_days=None)
       assert "hundred_days" in got
   ```

4. Run `pytest tests/test_achievements_json.py -q` and then the full `pytest`.
5. The achievement automatically appears in the API
   (`/api/achievements/definitions`) and in the achievements editor — no extra
   code needed.

## Branches / Гілки

- **`master` is the stable branch.** Every commit must keep the full test suite
  green. Only verified work lands here.
- **`mobile/android-ios` is the mobile port branch** (Capacitor 6: Android +
  iOS). It runs ahead of master: it contains the native `android/` and `ios/`
  platforms, mobile CI and the `MOBILE.md` documentation. Make new mobile
  changes as branches off `mobile/android-ios`; server-core changes land in
  `master` first and are then carried over to the mobile branch.
- Your working branch: `git checkout -b fix/my-fix` from the appropriate base branch.
- master history is linear (rebase/force-push are allowed to the owner only).

## PRs & commit style / PR та стиль комітів

1. Fork the repository and create a branch off `master` (or
   `mobile/android-ios` for mobile changes).
2. Each feature/fix = a separate commit with tests. See `tests/` for test style.
3. No build step: vanilla JS in `static/`, no new dependencies without a good reason.
4. Make sure your patch contains no private data (paths, tokens, e-mails).
5. PR with a "what / why / how I verified" description. CI must pass
   (pytest on 3.12–3.14).

Commit style: `Area: what was done` — a short imperative in a single line, e.g.

```
Docs: expanded CONTRIBUTING (UA+EN)
Mobile: Android platform (Capacitor 6) — npx cap add android
OSS: remove monetization
```

Areas already in use: `Docs`, `Mobile`, `OSS`, `Tests`, `UI`, `Release`.

## Code rules / Правила коду

- Python: type hints, stdlib-first, no ORM; logic in `app/gamification.py` must be pure (no HTTP/DB).
- Tests: every new API/service behavior gets at least one pytest in `tests/`.
- UI strings go only through `app/i18n.json` (the same keys for `uk` and `en`).
- User data never leaves the device: no telemetry, analytics or external calls.

## Languages & i18n / Мови та i18n

The project supports **two languages: Ukrainian and English**. Russian
localization is **not accepted** — this is a deliberate policy of the
maintainer; such PRs are closed without discussion (the hygiene test
`tests/test_oss_hygiene.py` scans tracked files for Russian-specific letters
and will fail CI).

Проєкт підтримує **дві мови: українську та англійську**. Російську локалізацію
**не додавати** — це свідоме політичне рішення власника; такі PR закриваються
без обговорення.

Practical i18n rules:

- Every visible UI string goes through `app/i18n.json`: the `dict.uk` and
  `dict.en` dictionaries must have the **same set of keys**; the language is
  stored in the player's settings (`settings.lang`), supported languages are
  `SUPPORTED_LANGS = ("uk", "en")`.
- When adding a key, add it in both languages at once and update
  `tests/test_i18n.py` if it has a key-completeness check.
- Documentation is also bilingual in pairs: `README.md` ↔ `README.en.md`,
  `CONTRIBUTING.md` ↔ `CONTRIBUTING.en.md`.

## Mobile port / Мобільний порт

The mobile apps (Android / iOS via Capacitor) are developed in the separate
**`mobile/android-ios`** branch. The build & install guide is in the `MOBILE.md`
file on that branch (Android sideload, AltStore/Sideloadly for iOS, local server
address, Tailscale for external access, local builds). The web version in
`master` does not depend on the mobile branch.

## License / Ліцензія

By contributing you agree that your changes are licensed under the project's MIT license.
Вносячи зміни, ви погоджуєтесь, що вони ліцензуються під MIT разом із проєктом.
