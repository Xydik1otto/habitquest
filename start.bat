@echo off
rem HabitQuest launcher: first run creates .venv and installs deps, then starts the server.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [HabitQuest] Python not found. Install it from https://www.python.org/downloads/
  echo and CHECK "Add Python to PATH" during installation.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [HabitQuest] First run: creating virtual environment...
  python -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)

echo [HabitQuest] Starting on http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app
goto :eof

:fail
echo [HabitQuest] Setup failed. Check the messages above.
pause
