"""Tests: 30-day streak series (SVG chart source)."""
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


def test_series_defaults_to_30_days(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    out = service.streak_series(database, hid, today=date(2026, 1, 10))
    assert out["habit_id"] == hid and out["days"] == 30
    assert len(out["series"]) == 30
    assert out["series"][-1]["date"] == "2026-01-10"
    assert out["series"][0]["date"] == "2025-12-12"
    assert all(p["count"] == 0 for p in out["series"])
    assert out["streak"] == 0


def test_series_counts_checkins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    today = date(2026, 1, 10)
    for i in range(4, -1, -1):  # 5 consecutive days ending today
        service.checkin(database, hid, (today - timedelta(days=i)).isoformat(), today=today)
    out = service.streak_series(database, hid, days=10, today=today)
    counts = [p["count"] for p in out["series"]]
    assert counts == [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
    assert out["streak"] == 5
    # only the last `days` days are returned
    assert out["series"][0]["date"] == "2026-01-01"


def test_series_validates_days(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    with pytest.raises(ValueError, match="days"):
        service.streak_series(database, hid, days=0)
    with pytest.raises(ValueError, match="days"):
        service.streak_series(database, hid, days=366)


def test_series_unknown_habit(database):
    with pytest.raises(ValueError, match="unknown habit"):
        service.streak_series(database, 99)


def test_series_api(client):
    client.post("/api/habits", json={"name": "Run"})
    client.post("/api/checkin", json={"habit_id": 1})
    r = client.get("/api/habits/1/series")
    assert r.status_code == 200
    data = r.json()
    assert data["days"] == 30 and len(data["series"]) == 30
    assert data["series"][-1]["count"] == 1
    assert client.get("/api/habits/99/series").status_code == 404
    assert client.get("/api/habits/1/series?days=0").status_code == 400


def test_chart_ui_present(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    from pathlib import Path

    js = (Path(main.STATIC_DIR) / "app.js").read_text(encoding="utf-8")
    css = (Path(main.STATIC_DIR) / "style.css").read_text(encoding="utf-8")
    main._database = None
    assert "streakChartSVG" in js and "/api/habits/" in js and "series?days=30" in js
    assert ".streak-chart" in css
