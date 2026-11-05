"""Tests: INSTALL.md exists and covers the promised paths (Windows + Linux)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_install_md_covers_windows_and_linux():
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for keyword in ("Add Python to PATH", "start.bat", "shell:startup",        # Windows
                    "systemd", "systemctl --user", "python3 -m venv",          # Linux
                    "Оновлення", "Export JSON", "data/habitquest.db"):
        assert keyword in text, f"INSTALL.md must mention {keyword!r}"


def test_start_bat_launcher_exists_and_installs_deps():
    bat = (ROOT / "start.bat").read_text(encoding="utf-8")
    for token in (".venv", "requirements.txt", "uvicorn app.main:app", "127.0.0.1:8000"):
        assert token in bat
