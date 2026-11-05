"""Tests: boss battle mechanics (HP, per-hit damage, victory bonus + badge)."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app import gamification as g, main, service


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


def test_damage_equals_sum_of_checkin_xp(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 5, month="2026-01")
    service.checkin(database, hid, "2026-01-05")  # streak 1 → 11
    service.checkin(database, hid, "2026-01-06")  # streak 2 → 12
    q = database.list_quests("2026-01")[0]
    assert q["damage"] == 23 and q["progress"] == 2


def test_longer_streak_hits_harder(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 31, month="2026-01")  # never completes here
    for i in range(1, 6):
        service.checkin(database, hid, (date(2026, 1, 1) + timedelta(days=i)).isoformat())
    q = database.list_quests("2026-01")[0]
    # streaks 1..5 → 11+12+13+14+15 = 65 > 10 damage × 5 hits
    assert q["damage"] == 65 and q["damage"] > 10 * q["progress"]


def test_victory_possible_before_target_hits(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 10, month="2026-01")  # HP = 100
    before = database.xp()
    for i in range(1, 9):  # 8 hits: 11+12+...+18 = 116 ≥ 100
        service.checkin(database, hid, (date(2026, 1, 1) + timedelta(days=i)).isoformat())
    q = database.list_quests("2026-01")[0]
    assert q["progress"] == 8 and q["damage"] == 116
    assert q["completed"] == 1 and q["rewarded"] == 1
    # bonus XP + coins granted exactly once
    assert database.xp() == before + 116 + g.QUEST_BONUS_XP


def test_victory_badge_awarded_once(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 2, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    service.checkin(database, hid, "2026-01-06")
    badges = database.list_badges()
    assert len(badges) == 1
    assert badges[0]["id"] == "boss_2026-01_1"
    assert "Gym" in badges[0]["label"] and "2026-01" in badges[0]["label"]
    # undo below HP and redo: badge is kept, bonus is not re-awarded
    service.undo_checkin(database, hid, "2026-01-06")
    assert database.list_quests("2026-01")[0]["completed"] == 0
    assert len(database.list_badges()) == 1  # badge stays earned
    xp_before = database.xp()
    service.checkin(database, hid, "2026-01-06")
    assert database.xp() == xp_before + 12  # no second bonus
    assert len(database.list_badges()) == 1


def test_no_badge_without_victory(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 31, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    assert database.list_badges() == []


def test_badges_endpoint_and_state(client):
    client.post("/api/habits", json={"name": "Gym"})
    client.post("/api/quests", json={"habit_id": 1, "target": 1})
    client.post("/api/checkin", json={"habit_id": 1})  # 10 XP ≥ HP 10 → victory
    assert client.get("/api/badges").json()["badges"][0]["id"] == f"boss_{service.today_iso()[:7]}_1"
    state = client.get("/api/state").json()
    assert len(state["badges"]) == 1


def test_damage_survives_undo_redo_cycle(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 2, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    service.checkin(database, hid, "2026-01-06")
    service.undo_checkin(database, hid, "2026-01-06")
    q = database.list_quests("2026-01")[0]
    assert q["damage"] == 11 and q["completed"] == 0


def test_export_roundtrip_keeps_badges(database, tmp_path):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 1, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    data = database.export()
    assert len(data["badges"]) == 1
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data
