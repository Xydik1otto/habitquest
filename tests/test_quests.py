"""Tests: monthly quests / boss battles."""
from datetime import date

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


def test_boss_hp_formula():
    assert g.boss_hp(1) == 10
    assert g.boss_hp(12) == 120
    assert g.boss_hp(0) == 10  # clamped to a minimum of one hit


def test_create_quest_default_month(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    q = service.create_quest(database, hid, 12, today=date(2026, 1, 10))
    assert q["month"] == "2026-01"
    assert q["target"] == 12
    assert q["progress"] == 0
    assert q["completed"] is False
    assert q["hp"] == 120 and q["damage"] == 0


def test_quest_progress_counts_checkins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 3, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    service.checkin(database, hid, "2026-01-06")
    q = database.list_quests("2026-01")[0]
    assert q["progress"] == 2
    assert q["damage"] == 20  # flat 10 damage per hit in alpha


def test_quest_completion_awards_bonus_once(database):
    hid = database.add_habit("Read", "📚", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 2, month="2026-01")
    service.checkin(database, hid, "2026-01-05")  # +11 XP, boss not dead yet
    xp_after_first = database.xp()
    assert xp_after_first == 11
    service.checkin(database, hid, "2026-01-06")  # +12 XP + 100 boss bonus
    assert database.xp() == xp_after_first + 12 + g.QUEST_BONUS_XP
    q = database.list_quests("2026-01")[0]
    assert q["completed"] == 1 and q["rewarded"] == 1
    # undo + redo must not re-award the bonus
    database.remove_checkin(hid, "2026-01-06")
    service._sync_quests_for(database, hid, "2026-01-06")
    service.checkin(database, hid, "2026-01-06")
    assert database.xp() == xp_after_first + 12 + g.QUEST_BONUS_XP + 12


def test_duplicate_quest_rejected(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 5, month="2026-02")
    with pytest.raises(ValueError, match="already exists"):
        service.create_quest(database, hid, 5, month="2026-02")


def test_quest_unknown_habit_and_bad_month(database):
    with pytest.raises(ValueError, match="unknown habit"):
        service.create_quest(database, 99, 5)
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    with pytest.raises(ValueError, match="invalid month"):
        service.create_quest(database, hid, 5, month="2026-13")
    with pytest.raises(ValueError, match="target"):
        service.create_quest(database, hid, 0)


def test_quest_ignores_other_month_checkins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 1, month="2026-02")
    service.checkin(database, hid, "2026-01-31")  # January hit must not help the February boss
    q = database.list_quests("2026-02")[0]
    assert q["progress"] == 0


def test_quests_in_state_and_endpoints(client):
    client.post("/api/habits", json={"name": "Gym"})
    r = client.post("/api/quests", json={"habit_id": 1, "target": 3})
    assert r.status_code == 200
    q = r.json()
    assert q["hp"] == 30 and q["progress"] == 0
    # duplicate → 400, unknown habit → 404, bad month → 422 (pattern)
    assert client.post("/api/quests", json={"habit_id": 1, "target": 3}).status_code == 400
    assert client.post("/api/quests", json={"habit_id": 99, "target": 3}).status_code == 404
    assert client.post("/api/quests", json={"habit_id": 1, "target": 3, "month": "bad"}).status_code == 422
    assert client.get("/api/quests").json()["quests"][0]["target"] == 3
    state = client.get("/api/state").json()
    assert state["quests"][0]["habit_name"] == "Gym"
    # check-in moves the boss bar
    client.post("/api/checkin", json={"habit_id": 1})
    q = client.get("/api/quests").json()["quests"][0]
    assert q["progress"] == 1 and q["damage"] == 10


def test_undo_checkin_updates_quest_progress(client):
    import datetime as _dt
    client.post("/api/habits", json={"name": "Gym"})
    client.post("/api/quests", json={"habit_id": 1, "target": 2})
    client.post("/api/checkin", json={"habit_id": 1})
    today = _dt.date.today().isoformat()
    client.delete(f"/api/checkin/1/{today}")
    q = client.get("/api/quests").json()["quests"][0]
    assert q["progress"] == 0 and q["damage"] == 0


def test_quest_export_import_roundtrip(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 2, month="2026-01")
    service.checkin(database, hid, "2026-01-05")
    service.checkin(database, hid, "2026-01-06")
    data = database.export()
    assert len(data["quests"]) == 1 and data["quests"][0]["completed"] is True
