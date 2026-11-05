"""Tests: monthly recap page."""
from datetime import date

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


def _seed_month(database, hid, days):
    for d in days:
        service.checkin(database, hid, d)


def test_recap_month_defaults_to_current(database):
    r = service.recap(database, today=date(2026, 3, 15))
    assert r["month"] == "2026-03" and r["checkins"] == 0


def test_recap_invalid_month(database):
    with pytest.raises(ValueError, match="invalid month"):
        service.recap(database, "2026-13")
    with pytest.raises(ValueError, match="invalid month"):
        service.recap(database, "junk")


def test_recap_counts_and_xp(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    _seed_month(database, hid, [f"2026-01-{d:02d}" for d in (3, 4, 5, 10, 11)])
    r = service.recap(database, "2026-01")
    assert r["checkins"] == 5
    assert r["active_days"] == 5
    assert r["xp_earned"] == 11 + 12 + 13 + 11 + 12  # streaks 1-3, then reset → 1-2
    assert r["xp_spent"] == 0 and r["xp_net"] == r["xp_earned"]
    assert r["best_day"] == "2026-01-03" and r["best_day_checkins"] == 1


def test_recap_longest_streak_within_month(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    # 31 Dec counts in December only; January run: 1–4 → 4, then gap, 8–10 → 3
    _seed_month(database, hid, ["2025-12-31", "2026-01-01", "2026-01-02", "2026-01-03",
                                "2026-01-04", "2026-01-08", "2026-01-09", "2026-01-10"])
    r = service.recap(database, "2026-01")
    assert r["longest_streak"] == 4
    assert service.recap(database, "2025-12")["longest_streak"] == 1


def test_recap_per_category_and_top_habits(database):
    gym = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01", category="health")
    read = database.add_habit("Read", "📚", "daily", 1, "2026-01-01", category="mind")
    _seed_month(database, gym, ["2026-01-01", "2026-01-02", "2026-01-03"])
    _seed_month(database, read, ["2026-01-01"])
    r = service.recap(database, "2026-01")
    assert r["per_category"]["health"]["checkins"] == 3
    assert r["per_category"]["health"]["habits"] == 1
    assert r["per_category"]["mind"]["checkins"] == 1
    assert r["per_category"]["work"] == {"checkins": 0, "habits": 0, "xp": 0, "share": 0}
    assert r["top_habits"][0] == {"id": gym, "name": "Gym", "icon": "🏋", "checkins": 3}


def test_recap_quests_won(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.create_quest(database, hid, 1, month="2026-01")
    service.create_quest(database, hid, 30, month="2026-02")
    service.checkin(database, hid, "2026-01-05")
    r = service.recap(database, "2026-01")
    assert r["quests_total"] == 1 and r["quests_won"] == 1
    assert service.recap(database, "2026-02")["quests_won"] == 0


def test_recap_xp_spent_counts_shop(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    for i in range(1, 6):
        service.checkin(database, hid, f"2026-01-{i:02d}")
    service.buy_shield(database, 1, today=date(2026, 1, 10))
    r = service.recap(database, "2026-01")
    assert r["xp_spent"] == 50
    assert r["xp_net"] == r["xp_earned"] - 50


def test_recap_weeks_buckets(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    _seed_month(database, hid, ["2026-01-05", "2026-01-06", "2026-01-13"])
    r = service.recap(database, "2026-01")
    counts = {w["week"]: w["count"] for w in r["weeks"]}
    assert counts["2026-W02"] == 2 and counts["2026-W03"] == 1
    assert r["weeks"] == sorted(r["weeks"], key=lambda w: w["week"])


def test_recap_endpoint(client):
    client.post("/api/habits", json={"name": "Gym"})
    client.post("/api/checkin", json={"habit_id": 1})
    r = client.get("/api/recap")
    assert r.status_code == 200
    body = r.json()
    assert body["checkins"] == 1 and "per_category" in body and "weeks" in body
    assert client.get("/api/recap?month=bad").status_code == 400
    assert client.get("/api/recap?month=2025-12").json()["checkins"] == 0
