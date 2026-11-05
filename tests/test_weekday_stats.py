"""Tests: weekday streak-support stats (best / average day of week)."""
from datetime import date

from fastapi.testclient import TestClient
import pytest

from app import db as db_mod, gamification as g, main, service


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


def test_weekday_counts_and_best_day():
    # 2026-01-05 is Monday, 2026-01-07 Wednesday, 2026-01-10 Saturday
    dates = {"2026-01-05", "2026-01-07", "2026-01-10", "2026-01-12"}
    s = g.weekday_stats(dates)
    assert s["counts"][1] == 2          # two Mondays
    assert s["counts"][3] == 1 and s["counts"][6] == 1
    assert s["best_weekday"] == 1 and s["best_weekday_name"] == "monday"
    assert s["best_count"] == 2
    # 4 check-ins across 2 ISO weeks -> average 2.0 per week
    assert s["average_per_week"] == 2.0


def test_weekday_stats_empty_history():
    s = g.weekday_stats(set())
    assert s["best_weekday"] is None and s["best_count"] == 0
    assert s["average_per_week"] == 0.0
    assert set(s["counts"]) == {1, 2, 3, 4, 5, 6, 7}


def test_weekday_tie_resolves_to_earlier_weekday():
    dates = {"2026-01-05", "2026-01-06"}  # one Monday, one Tuesday
    s = g.weekday_stats(dates)
    assert s["best_weekday"] == 1


def test_stats_endpoint_includes_weekday_stats(client):
    client.post("/api/habits", json={"name": "Gym", "schedule": "daily"})
    client.post("/api/checkin", json={"habit_id": 1})
    s = client.get("/api/stats").json()
    # JSON object keys arrive as strings ("1".."7")
    assert set(s["weekday_stats"]["counts"]) == {"1", "2", "3", "4", "5", "6", "7"}
    assert s["weekday_stats"]["best_weekday"] is not None


def test_service_stats_empty_database_weekday_stats(database):
    s = service.stats(database, today=date(2026, 1, 10))
    assert s["weekday_stats"]["best_weekday"] is None
    assert s["total_checkins"] == 0
