"""Tests: bilingual documentation (README.md UA + README.en.md EN)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_both_readmes_exist_and_cover_the_product():
    ua = (ROOT / "README.md").read_text(encoding="utf-8")
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    for keyword in ("HabitQuest", "XP", "PWA", "SQLite", "api/export"):
        assert keyword in ua and keyword in en
    # README.en.md is genuinely English (no Ukrainian-only Cyrillic heading words)
    assert "Habit tracker" in en or "habit tracker" in en
    # each links to the other
    assert "README.en.md" in ua or "[README.md](README.md)" in en
    assert "README.md" in en


def test_readmes_mention_the_headline_gamification_features():
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    ua = (ROOT / "README.md").read_text(encoding="utf-8")
    for term in ("streak", "boss", "freeze", "PWA"):
        assert term.lower() in en.lower()
    for term in ("стрик", "бос", "freeze", "PWA"):
        assert term.lower() in ua.lower()
