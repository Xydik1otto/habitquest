"""Tests: first-run experience — opt-in demo data seeding."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod, main, service

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


def test_first_run_true_on_empty_tracker(database):
    assert service.is_first_run(database) is True
    database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    assert service.is_first_run(database) is False


def test_seed_demo_data_full_experience(database):
    out = service.seed_demo_data(database, days=21, today=TODAY)
    assert out == {"habits": 6, "days": 21}
    habits = database.list_habits()
    assert len(habits) == 6
    assert {h["category"] for h in habits} == {"health", "mind", "work", "home"}
    assert any(h["schedule"] == "weekly" for h in habits)
    # realistic history: ~80% of the last 21 days checked in per daily habit
    daily = [h for h in habits if h["schedule"] == "daily"]
    for h in daily:
        dates = database.checkin_dates(h["id"])
        assert len(dates) >= 14 and len(dates) <= 21
        assert all(d < TODAY.isoformat() for d in dates)  # history, not today
    # a monthly boss quest was created and has accumulated damage
    quests = database.list_quests("2026-01")
    assert len(quests) == 1 and quests[0]["damage"] > 0
    # demo grants XP via check-ins only
    assert database.xp() > 0
    # no demo today: seeding is idempotent only when empty; refusing twice
    with pytest.raises(ValueError, match="empty"):
        service.seed_demo_data(database, today=TODAY)


def test_demo_not_today_checkins(database):
    service.seed_demo_data(database, days=10, today=TODAY)
    for h in database.list_habits():
        assert TODAY.isoformat() not in database.checkin_dates(h["id"]), \
            "demo must leave today's choice to the player"


def test_first_run_and_demo_api(client):
    assert client.get("/api/first-run").json() == {"first_run": True}
    out = client.post("/api/demo").json()
    assert out["habits"] == 6
    assert client.get("/api/first-run").json() == {"first_run": False}
    # seeding a second time is a conflict
    assert client.post("/api/demo").status_code == 409
    state = client.get("/api/state").json()
    assert len(state["habits"]) == 6
    assert state["quests"] and state["quests"][0]["progress"] > 0
    # deleting everything makes it a first run again
    for h in state["habits"]:
        client.delete(f"/api/habits/{h['id']}")
    assert client.get("/api/first-run").json() == {"first_run": True}
