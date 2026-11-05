"""Tests: buddy mode — progress card via file exchange, no server."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

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


def test_snapshot_has_version_and_level():
    s = g.buddy_snapshot(player_xp=160, total_checkins=12, longest_streak=5)
    assert s["version"] == g.BUDDY_FILE_VERSION
    assert s["level"] == 3  # level 3 threshold = 150 XP
    assert s["total_checkins"] == 12 and s["longest_streak"] == 5


def test_service_buddy_file_from_database(database):
    hid = database.add_habit("Gym", "G", "daily", 1, "2026-01-01")
    service.checkin(database, hid, "2026-01-05", today=date(2026, 1, 5))
    service.checkin(database, hid, "2026-01-06", today=date(2026, 1, 6))
    snap = service.buddy_file(database)
    assert snap["player_xp"] == 11 + 12
    assert snap["total_checkins"] == 2 and snap["longest_streak"] == 2
    assert snap["level"] == 1


def test_compare_detects_leader_per_metric():
    mine = g.buddy_snapshot(player_xp=300, total_checkins=10, longest_streak=7)
    theirs = g.buddy_snapshot(player_xp=100, total_checkins=10, longest_streak=3)
    r = g.buddy_compare(mine, theirs)
    assert r["per_metric"]["player_xp"]["leader"] == "mine"
    assert r["per_metric"]["total_checkins"]["leader"] == "tie"
    assert r["per_metric"]["longest_streak"]["leader"] == "mine"
    assert r["wins"] == {"mine": 3, "theirs": 0, "tie": 1}  # xp, level, streak; checkins tie
    assert r["ahead"] == "mine"


def test_compare_rejects_invalid_snapshots():
    good = g.buddy_snapshot(player_xp=0, total_checkins=0, longest_streak=0)
    with pytest.raises(ValueError, match="version"):
        g.buddy_compare(good, {"version": "other"})
    with pytest.raises(ValueError, match="player_xp"):
        g.buddy_compare(good, {**good, "player_xp": -1})
    with pytest.raises(ValueError, match="must be an object"):
        g.buddy_compare(good, "not a dict")


def test_buddy_file_endpoint_and_roundtrip(client):
    client.post("/api/habits", json={"name": "Run", "schedule": "daily"})
    client.post("/api/checkin", json={"habit_id": 1, "date": "2026-11-01"})
    snap = client.get("/api/buddy/file").json()
    assert snap["version"] == g.BUDDY_FILE_VERSION
    # self-compare through the API: everything ties
    r = client.post("/api/buddy/compare", json={"buddy": snap})
    assert r.status_code == 200
    assert r.json()["ahead"] == "tie"
    assert r.json()["wins"]["tie"] == len(g.BUDDY_METRICS)


def test_buddy_compare_endpoint_rejects_bad_file(client):
    r = client.post("/api/buddy/compare", json={"buddy": {"version": "nope"}})
    assert r.status_code == 400
    assert "version" in r.json()["detail"]
