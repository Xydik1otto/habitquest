# 📦 Встановлення HabitQuest

Інструкція для **не-програміста**: від нульового комп'ютера до працюючого
застосунку за ~5 хвилин. Нічого хмарного, все на вашому пристрої.

---

## Windows 10 / 11

### 1. Встановіть Python (один раз)

1. Відкрийте https://www.python.org/downloads/ і завантажте останній Python 3.12+.
2. У вікні інсталятора **обов'язково поставте галочку «Add Python to PATH»**, тисніть *Install Now*.
3. Перевірка: натисніть `Win+R`, введіть `cmd`, Enter, у чорному вікні наберіть
   `python --version` — має з'явитися номер версії.

### 2. Розпакуйте HabitQuest

Розпакуйте архів проєкту (або `git clone`) у зручну папку, наприклад `C:\HabitQuest`.

> Зрозумілий шлях без пробілів — менше сюрпризів. Не кладіть у `C:\Program Files`.

### 3. Запуск — подвійний клік на `start.bat`

У корені проєкту є файл **`start.bat`**:

- перший запуск створить віртуальне середовище і встановить залежності (1–2 хв);
- потім відкриється браузер на `http://127.0.0.1:8000`;
- вікно сервера тримайте відкритим (можна згорнути) — це ваш локальний застосунок.

Або вручну з командного рядка:

```bat
cd C:\HabitQuest
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app
```

### 4. Автозапуск через папку Startup (опційно)

1. Натисніть `Win+R`, введіть `shell:startup`, Enter.
2. Скопіюйте в папку, що відкрилась, **ярлик** на `start.bat` (правий клік на файлі → «Створити ярлик»).
3. Тепер HabitQuest стартуватиме сам при вході в систему.

### 5. Встановлення як PWA (опційно)

Відкрийте `http://127.0.0.1:8000` в Chrome/Edge → меню (⋮) → **«Встановити застосунок»**.
З'явиться іконка на робочому столі, як у звичайної програми.

---

## Linux

### 1. Python і файли

```bash
# Debian/Ubuntu
sudo apt install python3 python3-venv python3-pip
git clone <url-проєкту> ~/habitquest && cd ~/habitquest
```

### 2. Перший запуск

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app
# відкрийте http://127.0.0.1:8000
```

### 3. Автозапуск через systemd user unit

Створіть файл `~/.config/systemd/user/habitquest.service`:

```ini
[Unit]
Description=HabitQuest — local gamified habit tracker
After=network.target

[Service]
WorkingDirectory=%h/habitquest
ExecStart=%h/habitquest/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=default.target
```

Увімкніть:

```bash
systemctl --user daemon-reload
systemctl --user enable --now habitquest
systemctl --user status habitquest   # має бути active (running)
# щоб сервіс працював і без активного сеансу:
sudo loginctl enable-linger $USER
```

---

## Оновлення

```bash
# Windows: зупиніть сервер (закрийте вікно start.bat), потім у папці проєкту:
git pull
.venv\Scripts\pip install -r requirements.txt   # якщо змінилися залежності
start.bat

# Linux:
systemctl --user stop habitquest
git pull
.venv/bin/pip install -r requirements.txt
systemctl --user start habitquest
```

Дані (SQLite-база) живуть у `data/habitquest.db` і **не зачіпаються** оновленнями.
Перед великим оновленням не зайвим буде експорт: кнопка **⬇ Export JSON** в інтерфейсі.

---

## Де мої дані?

- База: `data/habitquest.db` (SQLite, один файл).
- Повна копія: кнопка **⬇ Export JSON** → один файл, який можна імпортувати
  на будь-якому іншому пристрої (**⬆ Import**).
- Нічого не надсилається в інтернет: сервер слухає лише `127.0.0.1`.

## Проблеми?

- **«python не є внутрішньою чи зовнішньою командою»** — перевстановіть Python з галочкою *Add to PATH*.
- **Порт зайнятий** — запустіть на іншому: `python -m uvicorn app.main:app --port 8080`.
- **Браузер не відкрився** — відкрийте вручну `http://127.0.0.1:8000`.
- Знайшли баг? Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) — будемо вдячні за issue.
