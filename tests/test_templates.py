"""Tests: habit template library (20 ready-made habits with icons)."""
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


def test_library_has_20_valid_templates():
    templates = g.load_templates()
    assert len(templates) == 20
    ids = [t["id"] for t in templates]
    assert len(set(ids)) == 20
    for t in templates:
        assert t["category"] in g.CATEGORIES
        assert t["schedule"] in ("daily", "weekly")
        assert 1 <= t["target_per_period"] <= 7
        assert t["name_ua"] and t["name_en"] and t["icon"]
    # New Year onboarding staples are present
    ids_set = set(ids)
    assert {"water", "workout", "read", "meditate", "deep_work", "tidy"} <= ids_set
    # every category is represented
    assert {t["category"] for t in templates} == set(g.CATEGORIES)


def test_validate_template_rejects_bad_rows():
    with pytest.raises(ValueError, match="missing"):
        g.validate_template({"id": "x"})
    with pytest.raises(ValueError, match="category"):
        g.validate_template({"id": "x", "icon": "✅", "name_ua": "a", "name_en": "b",
                             "category": "fun", "schedule": "daily", "target_per_period": 1})
    with pytest.raises(ValueError, match="target"):
        g.validate_template({"id": "x", "icon": "✅", "name_ua": "a", "name_en": "b",
                             "category": "health", "schedule": "daily", "target_per_period": 9})


def test_create_habit_from_template(database):
    created = service.create_from_template(database, "water", today=__import__("datetime").date(2026, 1, 10))
    habit = database.get_habit(created["id"])
    assert habit["name"] == "Пити воду"
    assert habit["icon"] == "💧"
    assert habit["category"] == "health"
    assert habit["schedule"] == "daily"


def test_create_from_template_custom_name_and_unknown(database):
    created = service.create_from_template(database, "read", name="Evening reading")
    assert database.get_habit(created["id"])["name"] == "Evening reading"
    with pytest.raises(ValueError, match="unknown template"):
        service.create_from_template(database, "nope")


def test_templates_api(client):
    body = client.get("/api/templates").json()
    assert len(body["templates"]) == 20
    r = client.post("/api/habits/from-template", json={"template_id": "workout"})
    assert r.status_code == 200
    hid = r.json()["id"]
    state = client.get("/api/state").json()
    habit = next(h for h in state["habits"] if h["id"] == hid)
    assert habit["name"] == "Тренування" and habit["icon"] == "🏋" and habit["category"] == "health"
    # custom name is honoured
    r2 = client.post("/api/habits/from-template", json={"template_id": "read", "name": "Книжка перед сном"})
    assert client.get("/api/state").json()["habits"][1]["name"] == "Книжка перед сном"
    assert client.post("/api/habits/from-template", json={"template_id": "ghost"}).status_code == 404
