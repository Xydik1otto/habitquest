# ⚔️ HabitQuest

![tests](https://img.shields.io/badge/tests-179%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-gold)
![status](https://img.shields.io/badge/version-1.0.0-orange)

**Local-first gamified habit tracker** — звички як RPG: XP, рівні, серії з «заморозками»,
щомісячні **бос-бої**, **крамниця щитів** та підсумки місяця. Усе локально, жодних підписок,
жодного хмарного рахунку. *(English version: [README.en.md](README.en.md).)*

> 📸 *Скриншот-плейсхолдери:*
> `![Day view](docs/screenshots/day-view.png)` — день з чекбоксами та стрик-вогниками 🔥/❄
> `![Boss battle](docs/screenshots/boss-battle.png)` — бос місяця з HP-баром (прогрес = шкода)
> `![Recap](docs/screenshots/recap.png)` — підсумок місяця з графіками
> *(TODO: зняти скриншоти після першого деплою; тексти вже в README.)*

## Проблема

- Health & Wellness — найшвидше зростаюча категорія застосунків; habit-трекери стабільно вгорі запитів.
- Subscription fatigue: більшість трекерів — підписка $4–6/міс за CRUD над локальними даними.
- Ігрові елементи утримують краще за «сірі» списки, але топові гравці (Habitica, Streaks) — хмара або paywall.

## Чому це існує

Класичне дослідження формування звичок (Lally et al., 2010, *European Journal of Social
Psychology*, «How are habits formed: Modelling habit formation in the real world») показало
дві речі, які визначають дизайн HabitQuest:

1. **Автоматичність займає в середньому 66 днів** (медіана; розкид 18–254 дні) —
   тому гра оперує довгими горизонтами: 30-денні графіки серій, місячні бос-бої,
   довгі стрики з множником XP, а не «21 день і готово».
2. **Один пропущений день не руйнує формування звички** — тому в HabitQuest є
   freeze-токени та «щити»: зірвати серію через хворобу чи відрядження — не програш,
   і система не карає за людське.

І головне: нагороди мають значення лише тоді, коли дані — ваші. Звідси local-first
SQLite, експорт одним JSON і нуль підписок.

## Рішення

Python **FastAPI + SQLite + vanilla JS** (без build-кроку). Нуль зовнішніх сервісів.
Дані експортуються/імпортуються одним JSON-файлом. **PWA**: встановлюється на
телефон/десктоп, статика кешується (offline shell).

### Гейміфікація

- **XP за чек-ін** зі стрік-множником `1 + min(streak,30)×0.1` — довша серія → більше XP.
- **Рівні**: кумулятивні пороги `50×n(n+1)/2` (L2=50, L3=150, L4=300…).
- **Стрик-вогник** ❄/🔥; 1 **freeze token** на тиждень «заморожує» пропущений день.
- **🛡 Крамниця щитів**: зароблені XP → монети; щит (50 💰) = додатковий freeze token,
  коли безкоштовний тижневий уже витрачено.
- **👹 Бос-бій місяця**: щомісячна ціль «виконати звичку N разів» → бос з
  **HP = N×10**; кожен чек-ін завдає шкоди = зароблений XP (сильніший стрик —
  сильніший удар). Перемога → **+100 XP bonus** + колекційний **бейдж**.
- **Досягнення з JSON** (`app/achievements.json`) — кастомні досягнення:
  додайте свій об'єкт `{id, name, description, metric, threshold}` через UI-редактор
  — і він працює.
- **Категорії** звичок: 💚 health / 🧠 mind / 💼 work / 🏠 home — з фільтрами в UI.
- **📅 Тижневі квести**: 3 звички × 5 чек-інів за тиждень → разова нагорода 150 💰.
- **🔊 Звук + ✨ анімації**: WebAudio «блим» на чек-ін, level-up конфетті — вимикаються
  в налаштуваннях.

### Вьюхи

1. **Day view** — сьогоднішні звички з чекбоксами (daily) і прогресом тижня (weekly), фільтр за категоріями, 📈-графік серії за 30 днів на кожну звичку.
2. **Бос-бій** — HP-бар монстра місяця; прогрес = завдана шкода.
3. **Тижневий квест** — прогрес-бари трьох звичок тижня.
4. **Дашборд** — SVG-діаграма XP за 30 днів, монети, щити, рівень.
5. **Week heatmap** — SVG-сітка «тижні × дні».
6. **Підсумок місяця** — чек-іни, найдовша серія, XP зароблено/витрачено, найкращий день,
   розбивка за категоріями, стовпчикова діаграма тижнів, переможені боси.
7. **Редактор досягнень** + stats + бейджі + крамниця + налаштування.

### Data portability

`GET /api/export` → JSON (включно з квестами, бейджами та XP-журналом);
`POST /api/import` → повне відновлення. Дані завжди ваші.

## Швидкий старт

```bash
cd habitquest
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# http://127.0.0.1:8000  →  «Встановити» як PWA з меню браузера

pytest           # 179 тестів
./scripts/smoke.sh  # швидкий smoke API (Pass/Fail)
```

## API (стисло)

`/api/state` · `POST /api/habits` · `POST /api/checkin` · `DELETE /api/checkin/{h}/{d}` ·
`GET /api/habits/{id}/series` · `/api/freeze` · `POST /api/quests` · `/api/weekly-quests` ·
`/api/shop` + `POST /api/shop/buy` · `/api/badges` · `/api/recap?month=YYYY-MM` ·
`/api/dashboard` · `/api/heatmap` · `/api/stats` · `/api/settings` ·
`/api/achievements` (+ POST/PUT — редактор) · `/api/export` · `/api/import`

## Дорожня карта

- [x] MVP: XP/рівні/стрики/freeze/досягнення/heatmap/export-import
- [x] v0.1.0-alpha: боси-квести, PWA, JSON-досягнення
- [x] v0.2.x: крамниця щитів, детальні бос-бої, категорії, підсумок місяця
- [x] v0.4.0: графіки серій, тижневі квести, звук/анімації, дашборд, редактор досягнень
- [x] v1.0.0: бібліотека шаблонів звичок, цитата дня, хардкор-режим, категорії у recap,
  i18n UA/EN, first-run демо, INSTALL.md, packaging, CSV-експорт, a11y, open-source hygiene
- [ ] v1.1: іконки-редактор, темна/світла тема, річні heatmap-и
- [ ] v1.2: річні звіти, додаткові теми — Roadmap безкоштовний: усі фічі open-source

## Contributing / Розробка

Проєкт open-source (MIT). Інструкція для учасників — [CONTRIBUTING.md](CONTRIBUTING.md);
проблеми безпеки — приватно, [SECURITY.md](SECURITY.md). Баг-репорти та пропозиції —
через шаблони issues (українська або англійська мова; російську локалізацію не приймаємо).

Рекомендовані GitHub topics: `habits`, `gamification`, `self-improvement`, `fastapi`,
`pwa`, `local-first`.

## Ліцензія

MIT — див. [LICENSE](LICENSE). 100% локально: жодної телеметрії, акаунтів чи хмари.
