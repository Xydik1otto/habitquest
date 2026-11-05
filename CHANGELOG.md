# Changelog

Усі помітні зміни проєкту документуються в цьому файлі.

Формат базується на [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/)
і дотримується [Semantic Versioning](https://semver.org/lang/uk/).

## [Unreleased]

### Added
- **Мобільні порти (Capacitor 6)**: `android/` (minSdk 24, target 35) та `ios/`
  (target 14) — оболонка, що підключається до власного сервера (splash з полем
  «Адреса сервера», збереження в Preferences); CI-збірка APK (android-build.yml)
  та unsigned iOS ZIP (ios-build.yml); `MOBILE.md` з гайдами sideload/AltStore/Tailscale.

### Removed
- Монетизаційний каркас: `.github/FUNDING.yml`, усі згадки «Pro Pack» (тепер
  «кастомні досягнення»), секцію монетизації в PLAN.md. Проєкт — 100% безкоштовний
  open-source, усі фічі вільні.

## [1.0.0] — 2026-11-05

### Added
- **Бібліотека шаблонів звичок**: 20 готових звичок з іконками й категоріями
  (`app/templates.json`, `GET /api/templates`, `POST /api/habits/from-template`
  з перевизначенням назви) — one-click панель у UI для New Year onboarding.
- **Цитата дня**: локальний `app/quotes.json` з 50 мотиваційними цитатами UA+EN,
  детермінована ротація за датою (`GET /api/quote`), панель у UI.
- **Хардкор-режим**: перемикач у налаштуваннях; пропущений (не заморожений) день
  щоденної звички = **−10 XP** (cap на поточний XP, списання один раз на день через
  xp_log, lookback 90 днів); `GET /api/state` повертає підсумку штрафів.
- **Статистика по категоріях у recap**: чек-іни, частка % місяця та XP по кожній
  категорії (health/mind/work/home) у `GET /api/recap` і UI.
- **i18n UA/EN**: словники інтерфейсу `app/i18n.json` (40+ ключів), `GET /api/i18n`,
  `GET/PUT /api/lang` (зберігається у player.settings), перемикач мови в шапці.
  Російської локалізації немає і не буде (політичне рішення).
- **First-run experience**: банер для порожнього трекера з opt-in кнопкою
  «Завантажити демо» (`GET /api/first-run`, `POST /api/demo`) — 6 демо-звичок,
  3 тижні реалістичної історії, бос-бій; «сьогодні» залишається гравцеві.
- **INSTALL.md**: покрокова інструкція для не-програміста (Windows: Python+PATH,
  `start.bat`, автозапуск через Startup; Linux: systemd user unit + linger),
  оновлення, розташування даних + лаунчер `start.bat`.
- **Packaging**: `pyproject.toml` (PEP 621, metadata v1.0.0), console-script
  `habitquest` (`app/cli.py` — браузер відкривається автоматично),
  `pip install -e .` працює; package-data для JSON-файлів.
- **Data safety**: one-click CSV-експорт (`GET /api/export/csv?kind=habits|checkins`,
  кнопка в UI) і `confirm()`-попередження перед видаленням звички.
- **A11y**: aria-labels на всіх статичних і динамічних елементах, skip-link,
  `:focus-visible` обвід, XP-прогресбар з `aria-valuenow`, `aria-live` для level-up.
- **Open-source hygiene**: CONTRIBUTING.md (UA/EN, політика мов: лише українська
  та англійська), SECURITY.md, шаблони issues (bug_report, feature_request — двомовні),
  README-секції Contributing + GitHub topics; тести-сканери приватності
  (жодних локальних шляхів/токенів/російських літер у tracked-файлах).

## [0.4.0] — 2026-11-05

### Added
- **Графіки серій**: SVG-графік 30-денних серій для кожної звички на сторінці дня
  (`GET /api/habits/{id}/series`, кнопка 📈 розгортає діаграму під рядком звички).
- **Тижневі квести**: міні-квест на тиждень — 3 звички × 5 чек-інів кожна,
  разова нагорода **150 💰** (`weekly_quests` таблиця, `POST/GET /api/weekly-quests`,
  панель з прогрес-барами; нагорода не відкликається при undo).
- **Звуки та анімації**: WebAudio «блим» на чек-ін, level-up оверлей з CSS-конфетті;
  перемикачі 🔊 Звук / ✨ Анімація в налаштуваннях (`player.settings`,
  `GET/PATCH /api/settings`, враховуються в export/import).
- **Дашборд візуалізацій**: `GET /api/dashboard` — чистий XP за кожен із останніх 30 днів
  (SVG-стовпчикова діаграма), монети, щити, рівень, чек-іни за 30 днів.
- **Редактор досягнень**: UI-панель для `app/achievements.json` — додати/редагувати
  шаблон досягнення (`POST /api/achievements`, `PUT /api/achievements/{id}`) з валідацією.
- Інфраструктура: `CHANGELOG.md`, favicon.svg + OG-мета,
  `scripts/smoke.sh` (smoke-тест API на випадковому порту).

## [0.3.0] — 2026-11-05

### Added
- **Крамниця щитів**: XP-гаманець (монети), покупка додаткових freeze-токенів (50 💰);
  тижневий безкоштовний токен витрачається першим.
- **Механіка бос-боїв**: шкода за удар = XP чек-іну (сильніший стрик — сильніший удар),
  перемога можливою до дедлайну; разовий бонус +100 XP і колекційний бейдж.
- **Категорії** звичок: health / mind / work / home, фільтр `?category=`, чіпси в UI.
- **Підсумок місяця**: `GET /api/recap?month=` — чек-іни, XP зароблено/витрачено,
  найдовша серія, найкращий день, розбивка за категоріями, тижневі стовпчики, переможені боси.
- Підготовка до GitHub: LICENSE (MIT), CI-workflow (pytest 3.12–3.14), .gitignore.

## [0.2.0] — 2026-11-05

### Added
- Бос-квести місяця (прогрес, HP = target×10, бонус XP), PWA (manifest + service worker,
  offline shell), JSON-визначення досягнень (кастомні досягнення).

## [0.1.0] — 2026-11-05

### Added
- MVP: локальний геймфікований трекер звичок (FastAPI + SQLite) — XP/рівні,
  стрики з freeze-токенами, досягнення, heatmap, export/import JSON, тести.
