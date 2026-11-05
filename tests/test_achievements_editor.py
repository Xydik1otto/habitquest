"""Tests: achievements.json editor (API + UI wiring)."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import gamification as g, main

NEW_DEF = {"id": "night_owl", "name": "Нічна сова", "description": "Після 23:00",
           "metric": "total_checkins", "threshold": 5}


@pytest.fixture
def client(tmp_path, monkeypatch):
    defs_file = tmp_path / "achievements.json"
    defs_file.write_text(json.dumps({"achievements": g.load_achievement_defs()}), encoding="utf-8")
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    monkeypatch.setattr(main, "ACHIEVEMENTS_PATH", defs_file)
    main._database = None
    with TestClient(main.app) as c:
        yield c
    main._database = None


def _stored_defs(client):
    return g.load_achievement_defs(main.ACHIEVEMENTS_PATH)


def test_add_definition_persists_to_json(client):
    r = client.post("/api/achievements", json=NEW_DEF)
    assert r.status_code == 200
    ids = [d["id"] for d in r.json()["achievements"]]
    assert "night_owl" in ids
    stored = _stored_defs(client)
    assert NEW_DEF in [d for d in stored if d["id"] == "night_owl"]
    # GET reflects the persisted file
    assert "night_owl" in [d["id"] for d in client.get("/api/achievements").json()["all"]]


def test_add_duplicate_id_conflict(client):
    assert client.post("/api/achievements", json=NEW_DEF).status_code == 200
    assert client.post("/api/achievements", json=NEW_DEF).status_code == 409


def test_add_invalid_payload_rejected(client):
    bad = {**NEW_DEF, "id": "x", "metric": "level"}
    assert client.post("/api/achievements", json=bad).status_code == 422
    bad2 = {**NEW_DEF, "id": "y", "threshold": 0}
    assert client.post("/api/achievements", json=bad2).status_code == 422
    assert client.post("/api/achievements", json={**NEW_DEF, "name": ""}).status_code == 422
    # nothing was written
    assert "night_owl" not in [d["id"] for d in _stored_defs(client)]


def test_update_definition(client):
    client.post("/api/achievements", json=NEW_DEF)
    updated = {**NEW_DEF, "threshold": 10}
    r = client.put("/api/achievements/night_owl", json=updated)
    assert r.status_code == 200
    stored = [d for d in _stored_defs(client) if d["id"] == "night_owl"]
    assert stored[0]["threshold"] == 10


def test_update_can_rename_id_and_rejects_collisions(client):
    client.post("/api/achievements", json=NEW_DEF)
    r = client.put("/api/achievements/night_owl", json={**NEW_DEF, "id": "early_bird"})
    assert r.status_code == 200
    ids = [d["id"] for d in _stored_defs(client)]
    assert "early_bird" in ids and "night_owl" not in ids
    # renaming onto an existing id is a conflict
    r = client.put("/api/achievements/early_bird", json={**NEW_DEF, "id": "first_week"})
    assert r.status_code == 409


def test_update_unknown_achievement_404(client):
    r = client.put("/api/achievements/nope", json=NEW_DEF)
    assert r.status_code == 404


def test_new_definition_is_evaluated_in_habit_status(client):
    client.post("/api/habits", json={"name": "Gym"})
    client.post("/api/achievements", json={**NEW_DEF, "threshold": 1})
    st = client.get("/api/state").json()
    earned = st["habits"][0]["achievements"]
    assert "night_owl" not in earned  # no check-ins yet
    client.post("/api/checkin", json={"habit_id": 1})
    st = client.get("/api/state").json()
    assert "night_owl" in st["habits"][0]["achievements"]


def test_editor_ui_present(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    html = (Path(main.STATIC_DIR) / "index.html").read_text(encoding="utf-8")
    js = (Path(main.STATIC_DIR) / "app.js").read_text(encoding="utf-8")
    main._database = None
    assert 'id="achv-form"' in html and 'id="a-metric"' in html
    assert "renderAchvEditor" in js and "/api/achievements/" in js
