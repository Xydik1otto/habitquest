"""Tests: hardcore mode — a missed (unfrozen) day of a daily habit costs XP."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod, gamification as g, main, service

TODAY = date(2026, 1, 10)


@pytest.fixture
def database(tmp_path):
    return db_mod.Database(tmp_path / "test.db")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    with TestClient(main.app) as c:
        yield c
    main._database = None


def _enable_hardcore(database):
    service.set_settings(database, {"hardcore": True})


def test_disabled_by_default_no_penalties(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-05")
    gained = service.checkin(database, hid, "2026-01-09")["xp_gained"]
    out = service.apply_hardcore_penalties(database, today=TODAY)
    assert out == {"enabled": False, "penalties": 0, "xp_deducted": 0}
    assert database.xp() == gained


def test_missed_day_deducts_xp_once(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-05")
    service.checkin(database, hid, "2026-01-09")  # +11 XP (streak 1), 2026-01-05..08 missed
    _enable_hardcore(database)
    out = service.apply_hardcore_penalties(database, today=TODAY)
    # 4 missed days (5th–8th); deduction is capped at the player's XP (floor 0):
    # day 5 takes 10 (→1 XP left), day 6 takes the last 1, then nothing remains
    assert out["enabled"] is True
    assert out["penalties"] == 2 and out["xp_deducted"] == 11
    assert database.xp() == 0
    # idempotent: a second pass does not double-charge
    again = service.apply_hardcore_penalties(database, today=TODAY)
    assert again["penalties"] == 0
    assert database.xp() == 0


def test_frozen_days_are_not_penalized(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-05")
    database.add_xp(100)
    service.use_freeze(database, hid, "2026-01-06", today=TODAY)
    service.checkin(database, hid, "2026-01-09")
    _enable_hardcore(database)
    out = service.apply_hardcore_penalties(database, today=TODAY)
    # missed: 5, 7, 8 (6th is frozen) = 3 × 10
    assert out["penalties"] == 3 and out["xp_deducted"] == 30
    assert database.xp() == 100 + 11 - 30  # check-in on the 9th earned 11 (streak 1)


def test_checkin_after_penalty_is_not_re_penalized(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-05")
    database.add_xp(200)
    _enable_hardcore(database)
    service.apply_hardcore_penalties(database, today=TODAY)  # penalties for 5th..9th
    before = database.xp()
    service.checkin(database, hid, "2026-01-10")  # today's check-in is a win, not a miss
    out = service.apply_hardcore_penalties(database, today=TODAY)
    assert out["penalties"] == 0
    assert database.xp() == before + g.xp_for_checkin(1)


def test_weekly_habits_are_exempt(database):
    hid = database.add_habit("Laundry", "🧺", "weekly", 1, "2026-01-05")
    database.add_xp(50)
    _enable_hardcore(database)
    out = service.apply_hardcore_penalties(database, today=TODAY)
    assert out["penalties"] == 0
    assert database.xp() == 50


def test_penalty_respects_xp_floor_and_lookback(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2025-06-01")  # far beyond lookback
    _enable_hardcore(database)
    # with 0 XP nothing can be charged
    out = service.apply_hardcore_penalties(database, today=TODAY)
    assert out["penalties"] == 0 and database.xp() == 0
    # with a wallet, exactly the days inside the lookback window are charged
    database.add_xp(1000)
    out = service.apply_hardcore_penalties(database, today=TODAY)
    assert out["penalties"] == g.HARDCORE_LOOKBACK_DAYS
    assert out["xp_deducted"] == g.HARDCORE_LOOKBACK_DAYS * g.HARDCORE_PENALTY_XP
    assert database.xp() == 1000 - out["xp_deducted"]


def test_hardcore_via_api_state_and_toggle(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    # backdate a habit directly so it has real missed days behind it
    pre = db_mod.Database(tmp_path / "api.db")
    pre.add_habit("Gym", "🏋", "daily", 1, "2026-01-05")
    pre.add_xp(100)
    pre = None
    with TestClient(main.app) as c:
        hid = 1
        c.post("/api/checkin", json={"habit_id": hid, "date": "2026-01-09"})
        # default: off, state carries the hardcore summary
        state = c.get("/api/state").json()
        assert state["settings"]["hardcore"] is False and state["hardcore"]["enabled"] is False
        # enable → next state load penalizes the missed days
        c.patch("/api/settings", json={"settings": {"hardcore": True}})
        state = c.get("/api/state").json()
        assert state["hardcore"]["penalties"] >= 1
        assert state["player"]["xp"] >= 0
    main._database = None
