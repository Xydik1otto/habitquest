# Contributing / Учаснику проєкту

Дякуємо за інтерес до **HabitQuest**! Проєкт — local-first і minimal-by-design,
тому будь-який внесок проходить простий, але суворий шлях.

Thank you for your interest in **HabitQuest**! The project is local-first and
minimal-by-design, so every contribution follows a simple but strict path.

> English version: [CONTRIBUTING.en.md](CONTRIBUTING.en.md)

## Зміст / Contents

1. [Архітектура](#архітектура--architecture)
2. [Середовище та тести](#середовище-та-тести--environment--tests)
3. [Як додати звичку-шаблон](#як-додати-звичку-шаблон-templatesjson)
4. [Як додати досягнення](#як-додати-досягнення-achievementsjson)
5. [Гілки](#гілки--branches)
6. [PR та стиль комітів](#pr-та-стиль-комітів--prs--commit-style)
7. [Мови та i18n](#мови-та-i18n--languages--i18n)
8. [Мобільний порт](#мобільний-порт--mobile-port)
9. [Ліцензія](#ліцензія--license)

## Як допомогти / How you can help

- 🐛 Баг-репорти / Bug reports — через [шаблон issue](.github/ISSUE_TEMPLATE/bug_report.md).
- 💡 Пропозиції фіч / Feature proposals — через [шаблон](.github/ISSUE_TEMPLATE/feature_request.md).
- 🔒 Безпека / Security — **приватно**, див. [SECURITY.md](SECURITY.md). Не відкривайте публічний issue.
- 🌍 Переклади / Translations — **лише українська та англійська** (див. нижче).
- 📚 Контент: звички-шаблони (`app/templates.json`), досягнення (`app/achievements.json`),
  цитати (`app/quotes.json`) — найпростіший спосіб зробити перший внесок.
- 📝 Документація: README, README.en.md, INSTALL.md.

## Архітектура / Architecture

Проєкт навмисно плоский: чотири шари, жодних фреймворків понад FastAPI.

```
static/            UI (vanilla JS + CSS + service worker, PWA) — без build-кроку
app/main.py        FastAPI: HTTP-маршрути, тонкі — лише валідація і виклик service
app/service.py     Сервісний шар: оркестрація чек-інів, фризів, XP, квестів, босів
app/gamification.py  ЧИСТІ функції: XP/рівні/стрики/бої/досягнення (без HTTP і БД)
app/db.py          SQLite-сховище (stdlib sqlite3, без ORM)
app/templates.json | quotes.json | achievements.json | i18n.json — дані й словники
tests/             pytest (~30 файлів, 179 тестів)
```

Ключові правила архітектури:

- **`app/gamification.py` — чисті функції.** Ніяких HTTP-запитів, доступу до БД,
  глобального стану чи часу «з неба»: усе приймає `date`/числа/колекції як аргументи.
  Саме тому цю логіку легко тестувати. Константи балансу (BASE_XP, STREAK_CAP,
  SHIELD_PRICE, QUEST_BONUS_XP…) живуть тут, у верхній частині файлу.
- **`app/service.py` — сервісний шар.** Єдине місце, яке комбінує БД і геймифікацію:
  створення квестів, бос-бої, тижневі квести, нарахування XP за чек-ін.
  HTTP-обробники в `main.py` не містять бізнес-логіки.
- **`app/db.py` — SQLite.** Stdlib `sqlite3`, без ORM. Схема — рядок `SCHEMA`
  на початку файлу. Міграцій немає: зміни схеми робіть обережно й назад сумісно.
- **`static/` — UI.** Vanilla JS, жодного npm-білду для вебверсії (node_modules
  потрібен лише для Capacitor-мобільних платформ на гілці `mobile/android-ios`).
  Усі видимі рядки — через i18n (див. розділ «Мови та i18n»).
- **Дані у JSON, не в коді.** Шаблони звичок, цитати й досягнення — це звичайні
  JSON-файли в `app/`; їх валідують окремі функції (`validate_template`,
  `validate_achievement_def`) і окремі тести. Контент-внески не вимагають знань Python.

## Середовище та тести / Environment & tests

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # або pip install -r requirements.txt
pytest                                  # має бути зеленим ДО ваших змін
```

- CI проганяє pytest на Python 3.12–3.14.
- Повний набір — **179 тестів**, мають залишатися зеленими.
- Швидкий запуск одного файлу: `pytest tests/test_streaks.py -q`.
- Фікстури у `tests/conftest.py` дають тимчасову БД (`tmp_path`) і TestClient
  з підміненим `DB_PATH` — копіюйте цей патерн у нових тестах.
- Тест на приватність (`tests/test_oss_hygiene.py`) сканує відстежувані файли
  на шляхи/токени/особисті дані та **на російські літери** — ваш патч мусить
  це проходити.

## Як додати звичку-шаблон (templates.json)

Шаблони — готові звички з бібліотеки «New Year onboarding» у `app/templates.json`.
Формат файлу:

```json
{
  "_comment": "Бібліотека шаблонів звичок. Поля: id, icon, name_ua, name_en, category (health|mind|work|home), schedule (daily|weekly), target_per_period.",
  "templates": [
    { "id": "water", "icon": "💧", "name_ua": "Пити воду", "name_en": "Drink water",
      "category": "health", "schedule": "daily", "target_per_period": 1 }
  ]
}
```

Покроково:

1. Відкрийте `app/templates.json` і додайте новий об'єкт у масив `templates`.
2. Заповніть **усі** поля:
   - `id` — латиницею, унікальний, snake_case (`cold_shower`);
   - `icon` — один емодзі;
   - `name_ua` / `name_en` — назва українською та англійською (обидві обов'язкові);
   - `category` — один із `health | mind | work | home`;
   - `schedule` — `daily` або `weekly`;
   - `target_per_period` — ціле від 1 до 7.
3. Не забудьте англійську назву — шаблон без `name_en` валідатор відхилить.
4. Додайте/оновіть тест у `tests/test_templates.py`: переконайтеся, що тест
   лічильника шаблонів проходить з вашим новим рядком (валідацію полів
   виконує `validate_template`).
5. Запустіть `pytest tests/test_templates.py -q`, потім повний `pytest`.

## Як додати досягнення (achievements.json)

Кастомні досягнення описуються декларативно у `app/achievements.json`:

```json
{
  "_comment": "Додайте об'єкти з полями id, name, description, metric (streak | total_checkins | gap_days), threshold.",
  "achievements": [
    { "id": "first_week", "name": "Перший тиждень", "description": "Серія 7 днів",
      "metric": "streak", "threshold": 7 }
  ]
}
```

Поля:

- `id` — унікальний, snake_case;
- `name`, `description` — людські назви (опис — короткий, без прив'язки до мови UI);
- `metric` — що міряємо, рівно одне з:
  - `streak` — поточна серія днів поспіль;
  - `total_checkins` — загальна кількість чек-інів;
  - `gap_days` — пауза між чек-інами (повернення після перерви ≥ threshold днів);
- `threshold` — ціле число **≥ 1** (0 і від'ємні відхиляються).

Покроково:

1. Додайте об'єкт у масив `achievements` з усіма п'ятьма полями.
2. Перевірте, що `metric` — лише `streak | total_checkins | gap_days`, а `threshold ≥ 1` —
   саме це перевіряє `validate_achievement_def` у `app/gamification.py`.
3. Додайте тест у `tests/test_achievements_json.py`:

   ```python
   def test_my_achievement():
       defs = DEFS + [{"id": "hundred_days", "name": "Сто днів", "description": "100 днів поспіль",
                       "metric": "streak", "threshold": 100}]
       got = g.evaluate_custom_achievements(defs, streak=100, total_checkins=0, last_gap_days=None)
       assert "hundred_days" in got
   ```

4. Запустіть `pytest tests/test_achievements_json.py -q` і повний `pytest`.
5. Досягнення автоматично з'являться в API (`/api/achievements/definitions`)
   та в редакторі досягнень — окремий код писати не потрібно.

## Гілки / Branches

- **`master` — стабільна гілка.** Кожен коміт має тримати повний набір тестів
  зеленим. Сюди потрапляє лише перевірене.
- **`mobile/android-ios` — гілка мобільного порту** (Capacitor 6: Android +
  iOS). Вона рухається попереду master: містить нативні платформи `android/`,
  `ios/`, мобільний CI та документацію `MOBILE.md`. Нові мобільні зміни
  робіть гілками від `mobile/android-ios`; зміни серверного ядра спочатку
  приземляйте в `master`, а потім переносіть у мобільну гілку.
- Ваша робоча гілка: `git checkout -b fix/my-fix` від відповідної базової гілки.
- Історія master — лінійна (rebase/force-push дозволені лише власнику).

## PR та стиль комітів / PRs & commit style

1. Форкніть репозиторій, створіть гілку від `master` (або `mobile/android-ios`
   для мобільних змін).
2. Кожна фіча/виправлення = окремий коміт з тестами. Стиль тестів див. у `tests/`.
3. Без build-кроку: vanilla JS у `static/`, без нових залежностей без вагомої причини.
4. Перевірте, що ваш патч не містить приватних даних (шляхів, токенів, e-mail).
5. PR з описом «що/чому/як перевіряв». CI має пройти (pytest на 3.12–3.14).

Стиль комітів: `Область: що зроблено` — короткий імператив в один рядок, як-от

```
Docs: expanded CONTRIBUTING (UA+EN)
Mobile: Android platform (Capacitor 6) — npx cap add android
OSS: remove monetization
```

Області, що вже вживаються: `Docs`, `Mobile`, `OSS`, `Tests`, `UI`, `Release`.

## Правила коду / Code rules

- Python: type hints, stdlib-first, без ORM; логіка в `app/gamification.py` має бути чистою (без HTTP/DB).
- Тести: кожна нова поведінка API/сервісу має хоча б один pytest у `tests/`.
- UI-рядки — тільки через `app/i18n.json` (ключі однакові для `uk` і `en`).
- Дані користувача не залишають пристрій: жодних телеметрії, аналітики чи зовнішніх викликів.

## Мови та i18n / Languages & i18n

Проєкт підтримує **дві мови: українську та англійську**. Російську локалізацію
**не додавати** — це свідоме політичне рішення власника; такі PR закриваються
без обговорення (тест `tests/test_oss_hygiene.py` сканує відстежувані файли
на російські літери і зафарбить CI).

The project supports **two languages: Ukrainian and English**. Russian
localization is **not accepted** — this is a deliberate policy of the maintainer;
such PRs are closed without discussion (the hygiene test scans tracked files
for Russian-specific letters and will fail CI).

Практичні правила i18n:

- Усі видимі рядки UI — через `app/i18n.json`: словники `dict.uk` і `dict.en`
  з **однаковим набором ключів**; мова зберігається у налаштуваннях гравця
  (`settings.lang`), підтримувані мови — `SUPPORTED_LANGS = ("uk", "en")`.
- Додаючи ключ, додайте його одразу обома мовами і оновіть `tests/test_i18n.py`,
  якщо там є перевірка повноти ключів.
- Документація теж двомовна парами: `README.md` ↔ `README.en.md`,
  `CONTRIBUTING.md` ↔ `CONTRIBUTING.en.md`.

## Мобільний порт / Mobile port

Мобільні застосунки (Android / iOS через Capacitor) розробляються в окремій
гілці **`mobile/android-ios`**. Інструкція зі збирання й встановлення —
у файлі `MOBILE.md` цієї гілки (sideload Android, AltStore/Sideloadly для iOS,
адреса локального сервера, Tailscale для доступу ззовні, локальна збірка).
Вебверсія в `master` не залежить від мобільної гілки.

## Ліцензія / License

Вносячи зміни, ви погоджуєтесь, що вони ліцензуються під MIT разом із проєктом.
By contributing you agree that your changes are licensed under the project's MIT license.
