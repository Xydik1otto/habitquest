# Security Policy / Політика безпеки

## Supported versions / Підтримувані версії

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ (оновітьось до v1.0.0) |

## Reporting a vulnerability / Як повідомити про вразливість

**EN:** HabitQuest is a local-first application with no network surface beyond
`127.0.0.1`, so the practical attack surface is small — but reports are still welcome.
Please do **NOT** open a public issue for security problems. Email the maintainer
(contact link on the repository profile) with:

- a description of the issue and its impact;
- steps to reproduce (a minimal script or request is ideal);
- affected version (`habitquest --help` / `pyproject.toml`).

We aim to respond within 7 days. Please give us up to 30 days to ship a fix
before publishing details.

**UA:** HabitQuest — local-first застосунок; уся мережева поверхня обмежена
`127.0.0.1`, тому практичний ризик малий, але звіти вітаються. Будь ласка,
**не створюйте публічний issue** для проблем безпеки: напишіть власнику
(контакт у профілі репозиторію) з описом, кроками відтворення та версією.
Відповідаємо протягом 7 днів; на виправлення просимо до 30 днів до публікації деталей.

## Scope / Що вважаємо вразливістю

- XSS через імена звичок/нотатки у UI (текст потрапляє в innerHTML — увага до екранування вітається).
- Path traversal / довільний запис файлів через імпорт JSON.
- Витік даних з локальної машини (сервіс не має слухати на 0.0.0.0 за замовчуванням).

## Data handling / Робота з даними

Усі дані зберігаються локально у `data/habitquest.db`; експорт/імпорт — вручну
через UI. Проєкт не надсилає жодних даних у мережу.
