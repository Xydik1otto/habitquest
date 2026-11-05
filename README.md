# ⚔️ HabitQuest

![tests](https://img.shields.io/badge/tests-98%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-gold)
![status](https://img.shields.io/badge/version-0.3.0--alpha-orange)

**Local-first gamified habit tracker** — звички як RPG: XP, рівні, серії з «заморозками»,
щомісячні **бос-бої**, **крамниця щитів** та підсумки місяця. Усе локально, жодних підписок,
жодного хмарного рахунку.

> 📸 *Скриншот-плейсхолдери:*
> `![Day view](docs/screenshots/day-view.png)` — день з чекбоксами та стрик-вогниками 🔥/❄
> `![Boss battle](docs/screenshots/boss-battle.png)` — бос місяця з HP-баром (прогрес = шкода)
> `![Recap](docs/screenshots/recap.png)` — підсумок місяця з графіками
> *(TODO: зняти скриншоти після першого деплою; тексти вже в README.)*

## Проблема

- Health & Wellness — найшвидше зростаюча категорія застосунків; habit-трекери стабільно вгорі запитів.
- Subscription fatigue: більшість трекерів — підписка $4–6/міс за CRUD над локальними даними.
- Ігрові елементи утримують краще за «сірі» списки, але топові гравці (Habitica, Streaks) — хмара або paywall.

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
- **Досягнення з JSON** (`app/achievements.json`) — шаблони для Pro Pack:
  додайте свій об'єкт `{id, name, description, metric, threshold}` — і він працює.
- **Категорії** звичок: 💚 health / 🧠 mind / 💼 work / 🏠 home — з фільтрами в UI.

### Вьюхи

1. **Day view** — сьогоднішні звички з чекбоксами (daily) і прогресом тижня (weekly), фільтр за категоріями.
2. **Бос-бій** — HP-бар монстра місяця; прогрес = завдана шкода.
3. **Week heatmap** — SVG-сітка «тижні × дні».
4. **Підсумок місяця** — чек-іни, найдовша серія, XP зароблено/витрачено, найкращий день,
   розбивка за категоріями, стовпчикова діаграма тижнів, переможені боси.
5. **Stats + бейджі + крамниця.**

### Data portability

`GET /api/export` → JSON (включно з квестами, бейджами та XP-журналом);
`POST /api/import` → повне відновлення. Дані завжди ваші.

## Швидкий старт

```bash
cd habitquest
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# http://127.0.0.1:8000  →  «Встановити» як PWA з меню браузера

pytest          # 98 тестів
```

## API (стисло)

`/api/state` · `POST /api/habits` · `POST /api/checkin` · `DELETE /api/checkin/{h}/{d}` ·
`/api/freeze` · `POST /api/quests` · `/api/shop` + `POST /api/shop/buy` · `/api/badges` ·
`/api/recap?month=YYYY-MM` · `/api/heatmap` · `/api/stats` · `/api/achievements` ·
`/api/export` · `/api/import`

## Дорожня карта

- [x] MVP: XP/рівні/стрики/freeze/досягнення/heatmap/export-import
- [x] v0.1.0-alpha: боси-квести, PWA, JSON-досягнення
- [x] v0.2.x: крамниця щитів, детальні бос-бої, категорії, підсумок місяця
- [ ] v1.0: іконки-редактор, темна/світла тема, річні heatmap-и
- [ ] Pro Pack (one-time): додаткові теми, кастомні досягнення, річні звіти

## Ліцензія

MIT — див. [LICENSE](LICENSE). 100% локально: жодної телеметрії, акаунтів чи хмари.
