"""Tests: JSON achievement definitions (Pro-Pack templates)."""
from datetime import date

import pytest

from app import gamification as g

DEFS = g.load_achievement_defs()


def test_builtin_defs_load_and_are_valid():
    ids = {d["id"] for d in DEFS}
    assert {"first_checkin", "first_week", "thirty_days", "comeback"} <= ids
    for d in DEFS:
        g.validate_achievement_def(d)  # must not raise


def test_json_defs_match_builtin_semantics():
    by_id = {d["id"]: d for d in DEFS}
    assert by_id["first_week"]["metric"] == "streak"
    assert by_id["first_week"]["threshold"] == 7
    assert by_id["thirty_days"]["threshold"] == 30
    assert by_id["comeback"]["metric"] == "gap_days"


def test_custom_defs_evaluate():
    defs = DEFS + [{"id": "ten_checkins", "name": "Десятка", "description": "10 чек-інів",
                    "metric": "total_checkins", "threshold": 10}]
    got = g.evaluate_custom_achievements(defs, streak=0, total_checkins=10, last_gap_days=None)
    assert "ten_checkins" in got
    assert "centurion" not in got  # 100 чек-інів ще не набрано


def test_custom_defs_streak_threshold():
    got = g.evaluate_custom_achievements(DEFS, streak=100, total_checkins=100, last_gap_days=1)
    assert {"first_week", "thirty_days", "centurion", "first_checkin"} <= set(got)


def test_invalid_def_rejected():
    with pytest.raises(ValueError, match="missing"):
        g.validate_achievement_def({"id": "x", "metric": "streak", "threshold": 1})
    with pytest.raises(ValueError, match="metric"):
        g.validate_achievement_def({"id": "x", "name": "n", "description": "d",
                                    "metric": "level", "threshold": 1})
    with pytest.raises(ValueError, match="threshold"):
        g.validate_achievement_def({"id": "x", "name": "n", "description": "d",
                                    "metric": "streak", "threshold": 0})


def test_load_achievement_defs_custom_file(tmp_path):
    p = tmp_path / "custom.json"
    p.write_text('[{"id":"night_owl","name":"Нічна сова","description":" після 23:00",'
                 '"metric":"total_checkins","threshold":5}]', encoding="utf-8")
    defs = g.load_achievement_defs(p)
    assert defs[0]["id"] == "night_owl"


def test_definitions_served_by_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main

    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    with TestClient(main.app) as c:
        data = c.get("/api/achievements").json()["all"]
    main._database = None
    assert {d["id"] for d in data} >= {"first_checkin", "centurion"}


def test_custom_achievement_shows_in_habit_status(tmp_path):
    from app import db as db_mod, service

    database = db_mod.Database(tmp_path / "t.db")
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    for i in range(101):
        database.add_checkin(hid, f"2025-{(1 + i // 28):02d}-{1 + i % 28:02d}")
    st = service.habit_status(database, database.get_habit(hid), today=date(2026, 1, 10))
    assert "centurion" in st["achievements"]
