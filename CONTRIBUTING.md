# Contributing / CONTRIBUTING.md

Дякуємо за інтерес до **HabitQuest**! Проєкт — local-first і minimal-by-design,
тому будь-який внесок проходить простий, але суворий шлях.

Thank you for your interest in **HabitQuest**! The project is local-first and
minimal-by-design, so every contribution follows a simple but strict path.

## Як допомогти / How you can help

- 🐛 Баг-репорти / Bug reports — через [шаблон issue](.github/ISSUE_TEMPLATE/bug_report.md).
- 💡 Пропозиції фіч / Feature proposals — через [шаблон](.github/ISSUE_TEMPLATE/feature_request.md).
- 🔒 Безпека / Security — **приватно**, див. [SECURITY.md](SECURITY.md). Не відкривайте публічний issue.
- 🌍 Переклади / Translations — **лише українська та англійська** (див. нижче).
- 📝 Документація: README, README.en.md, INSTALL.md.

## Мови / Languages policy

Проєкт підтримує **дві мови: українську та англійську**. Російську локалізацію
**не додавати** — це свідоме політичне рішення власника; такі PR закриваються без обговорення.

The project supports **two languages: Ukrainian and English**. Russian
localization is **not accepted** — this is a deliberate policy of the maintainer;
such PRs are closed without discussion.

## Процес / Process

1. Форкніть репозиторій, створіть гілку: `git checkout -b fix/my-fix`.
2. Налаштуйте середовище:
   ```bash
   python -m venv .venv
   .venv/bin/pip install -e ".[dev]"      # або pip install -r requirements.txt
   pytest                                  # має бути зеленим ДО ваших змін
   ```
3. Кожна фічa/виправлення = окремий коміт з тестами. Стиль тестів див. у `tests/`.
4. Без build-кроку: vanilla JS у `static/`, без нових залежностей без вагомої причини.
5. Перевірте, що ваш патч не містить приватних даних (шляхів типу `G:\`, токенів, e-mail).
6. PR з описом «що/чому/як перевіряв». CI має пройти (pytest на 3.12–3.14).

## Правила коду / Code rules

- Python: type hints, stdlib-first, без ORM; логіка в `app/gamification.py` має бути чистою (без HTTP/DB).
- Тести: кожна нова поведінка API/сервісу має хоча б один pytest у `tests/`.
- UI-рядки — тільки через `app/i18n.json` (ключі однакові для `uk` і `en`).
- Дані користувача не залишають пристрій: жодних телеметрії, аналітики чи зовнішніх викликів.

## Ліцензія / License

Вносячи зміни, ви погоджуєтесь, що вони ліцензуються під MIT разом із проєктом.
By contributing you agree that your changes are licensed under the project's MIT license.
