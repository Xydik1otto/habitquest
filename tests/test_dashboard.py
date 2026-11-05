"""Tests: dashboard visualizations (30-day XP flow, wallet, level)."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app import main, service

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


def test_dashboard_empty(database):
    d = service.dashboard(database, today=TODAY)
    assert len(d["xp_by_day"]) == 30
    assert d["xp_by_day"][-1]["date"] == "2026-01-10"
    assert d["xp_by_day"][0]["date"] == "2025-12-12"
    assert all(p["xp"] == 0 for p in d["xp_by_day"])
    assert d["xp_earned_30d"] == 0 and d["coins"] == 0 and d["shields"] == 0
    assert d["player"]["level"] == 1 and d["checkins_30d"] == 0


def test_dashboard_counts_xp_flow(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    for i in range(4, -1, -1):
        service.checkin(database, hid, (TODAY - timedelta(days=i)).isoformat(), today=TODAY)
    d = service.dashboard(database, today=TODAY)
    xp = {p["date"]: p["xp"] for p in d["xp_by_day"]}
    assert xp["2026-01-10"] == 15  # streak 5 → 10×1.5
    assert xp["2026-01-06"] == 11
    assert d["xp_earned_30d"] == 11 + 12 + 13 + 14 + 15
    assert d["coins"] == 65 and d["checkins_30d"] == 5
    assert d["player"]["xp"] == 65


def test_dashboard_includes_spends_and_excludes_old_days(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2025-11-01")
    database.add_checkin(hid, "2025-12-01")  # 40 days ago → outside the 30-day window
    database.add_xp(50)
    database.add_coins(50)
    database.log_xp("2025-12-01", 50, "checkin", hid)
    service.buy_shield(database, qty=1, today=TODAY)  # -50 today
    d = service.dashboard(database, today=TODAY)
    xp = {p["date"]: p["xp"] for p in d["xp_by_day"]}
    assert xp.get("2025-12-01", 0) == 0  # outside window
    assert xp["2026-01-10"] == -50
    assert d["xp_earned_30d"] == 0
    assert d["coins"] == 0 and d["shields"] == 1


def test_dashboard_api_shape(client):
    client.post("/api/habits", json={"name": "Run"})
    client.post("/api/checkin", json={"habit_id": 1})
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    d = r.json()
    assert len(d["xp_by_day"]) == 30
    assert d["xp_by_day"][-1]["xp"] > 0
    assert {"coins", "shields", "player", "xp_earned_30d", "checkins_30d"} <= set(d)


def test_dashboard_ui_present(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    html = (Path(main.STATIC_DIR) / "index.html").read_text(encoding="utf-8")
    js = (Path(main.STATIC_DIR) / "app.js").read_text(encoding="utf-8")
    main._database = None
    assert 'id="dashboard"' in html
    assert "renderDashboard" in js and "/api/dashboard" in js
