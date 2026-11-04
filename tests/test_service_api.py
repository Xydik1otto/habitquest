"""Tests: service layer + API end-to-end with TestClient."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app import main, service


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


def test_checkin_awards_xp_with_streak_multiplier(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    today = date(2026, 1, 10)
    for i in range(4, -1, -1):  # 5 consecutive days ending today
        service.checkin(database, hid, (today - timedelta(days=i)).isoformat(), today=today)
    # XP multiplier anchors to the check-in day: streaks 1..5 → 11+12+13+14+15
    assert database.xp() == 11 + 12 + 13 + 14 + 15
    st = service.habit_status(database, database.get_habit(hid), today=today)
    assert st["streak"] == 5
    assert st["done_today"] is True


def test_service_freeze_once_per_week(database):
    hid = database.add_habit("Read", "📚", "daily", 1, "2026-01-01")
    today = date(2026, 1, 10)
    service.use_freeze(database, hid, today=today)
    with pytest.raises(ValueError):
        service.use_freeze(database, hid, today=today)


def test_export_import_roundtrip(database, tmp_path):
    hid = database.add_habit("Water", "💧", "daily", 1, "2026-01-01")
    service.checkin(database, hid, "2026-01-09")
    data = database.export()
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data


def test_imported_ids_continue(database):
    hid = database.add_habit("A", "✅", "daily", 1, "2026-01-01")
    data = database.export()
    database.import_data(data)
    hid2 = database.add_habit("B", "✅", "daily", 1, "2026-01-01")
    assert hid2 != hid and hid2 > hid


def test_stats_endpoint_shape(client):
    client.post("/api/habits", json={"name": "Gym", "schedule": "daily"})
    client.post("/api/checkin", json={"habit_id": 1})
    r = client.get("/api/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["total_checkins"] == 1
    assert s["player"]["level"] >= 1


def test_full_api_flow(client):
    r = client.post("/api/habits", json={"name": "Meditate", "icon": "🧘", "schedule": "daily"})
    assert r.json() == {"id": 1}
    r = client.post("/api/checkin", json={"habit_id": 1, "note": "morning"})
    assert r.json()["created"] is True
    assert r.json()["xp_gained"] >= 10
    # duplicate check-in same day: no double XP
    r2 = client.post("/api/checkin", json={"habit_id": 1})
    assert r2.json()["created"] is False
    assert r2.json()["xp_gained"] == 0
    # state shows habit done today
    st = client.get("/api/state").json()
    assert st["habits"][0]["done_today"] is True
    # undo removes it
    import datetime as _dt
    today = _dt.date.today().isoformat()
    assert client.delete(f"/api/checkin/1/{today}").json()["removed"] is True
    # export/import
    exp = client.get("/api/export").json()
    assert exp["version"] == 1 and len(exp["habits"]) == 1
    assert client.post("/api/import", json=exp).json()["imported"] is True


def test_freeze_api_limit(client):
    client.post("/api/habits", json={"name": "Run"})
    assert client.post("/api/freeze", json={"habit_id": 1}).status_code == 200
    assert client.post("/api/freeze", json={"habit_id": 1}).status_code == 400


def test_unknown_habit_404(client):
    assert client.post("/api/checkin", json={"habit_id": 99}).status_code == 404


def test_index_served(client):
    assert "HabitQuest" in client.get("/").text
