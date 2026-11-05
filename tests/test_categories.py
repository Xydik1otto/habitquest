"""Tests: habit categories (health/mind/work/home) with filters."""
import sqlite3

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


def test_category_constant():
    assert g.CATEGORIES == ("health", "mind", "work", "home")


def test_default_category_is_health(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    assert database.get_habit(hid)["category"] == "health"


def test_create_with_category(database):
    hid = database.add_habit("Read", "📚", "daily", 1, "2026-01-01", category="mind")
    assert database.get_habit(hid)["category"] == "mind"


def test_migrated_habits_get_default_category(tmp_path):
    """A database created before categories must migrate without losing rows."""
    path = tmp_path / "old.db"
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE habits (id INTEGER PRIMARY KEY, name TEXT NOT NULL, icon TEXT NOT NULL DEFAULT '✅',
            schedule TEXT NOT NULL DEFAULT 'daily', target_per_period INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL);
        INSERT INTO habits(id, name, created_at) VALUES (1, 'Old habit', '2026-01-01');
    """)
    conn.commit()
    conn.close()
    database = db_mod.Database(path)
    h = database.get_habit(1)
    assert h["name"] == "Old habit" and h["category"] == "health"


def test_list_habits_filter(database):
    a = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01", category="health")
    b = database.add_habit("Code", "💻", "daily", 1, "2026-01-01", category="work")
    ids = [h["id"] for h in database.list_habits("work")]
    assert ids == [b] and a not in ids
    assert {h["id"] for h in database.list_habits()} == {a, b}


def test_state_endpoint_filters_by_category(client):
    client.post("/api/habits", json={"name": "Gym", "category": "health"})
    client.post("/api/habits", json={"name": "Read", "category": "mind"})
    client.post("/api/habits", json={"name": "Deploy", "category": "work"})
    assert client.get("/api/state?category=work").json()["habits"][0]["name"] == "Deploy"
    assert len(client.get("/api/state").json()["habits"]) == 3
    assert client.get("/api/state?category=nope").status_code == 400


def test_invalid_category_rejected(client):
    assert client.post("/api/habits", json={"name": "X", "category": "chaos"}).status_code == 422


def test_category_in_status_and_export_roundtrip(database, tmp_path):
    hid = database.add_habit("Read", "📚", "daily", 1, "2026-01-01", category="mind")
    st = service.habit_status(database, database.get_habit(hid))
    assert st["category"] == "mind"
    data = database.export()
    assert data["habits"][0]["category"] == "mind"
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data
