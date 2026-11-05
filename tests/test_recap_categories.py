"""Tests: per-category statistics (checkins, share, XP) in the monthly recap."""
from datetime import date

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


def test_recap_per_category_checkins_share_xp(database):
    gym = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01", category="health")
    read = database.add_habit("Read", "📚", "daily", 1, "2026-01-01", category="mind")
    tidy = database.add_habit("Tidy", "🧹", "daily", 1, "2026-01-01", category="home")
    for day in ("2026-01-02", "2026-01-03"):
        service.checkin(database, gym, day)          # health: 2 check-ins
    for day in ("2026-01-02", "2026-01-04", "2026-01-05"):
        service.checkin(database, read, day)         # mind: 3 check-ins
    service.checkin(database, tidy, "2026-01-02")    # home: 1 check-in
    recap = service.recap(database, "2026-01")
    pc = recap["per_category"]
    assert pc["health"]["checkins"] == 2 and pc["mind"]["checkins"] == 3 and pc["home"]["checkins"] == 1
    assert pc["work"] == {"checkins": 0, "habits": 0, "xp": 0, "share": 0}
    assert pc["health"]["habits"] == 1 and pc["mind"]["habits"] == 1
    # shares sum to 100% of the 6 check-ins of the month
    total_share = sum(pc[c]["share"] for c in pc)
    assert abs(total_share - 100.0) < 0.3
    assert pc["mind"]["share"] == 50.0
    # XP per category comes from the checkin xp_log (streak-multiplied)
    assert pc["health"]["xp"] > 0 and pc["mind"]["xp"] > 0 and pc["home"]["xp"] > 0
    assert sum(pc[c]["xp"] for c in pc) == recap["xp_earned"]
    # empty month: zero shares, no division errors
    empty = service.recap(database, "2026-02")
    assert all(empty["per_category"][c]["share"] == 0 for c in empty["per_category"])


def test_recap_categories_api(client):
    h = client.post("/api/habits", json={"name": "Gym", "category": "health"}).json()["id"]
    client.post("/api/checkin", json={"habit_id": h, "date": "2026-01-09"})
    recap = client.get("/api/recap?month=2026-01").json()
    pc = recap["per_category"]
    assert pc["health"]["checkins"] == 1 and pc["health"]["share"] == 100.0
    assert pc["health"]["xp"] == 11  # streak-1 check-in XP
