"""Tests: data safety — CSV export and deletion guardrails."""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    with TestClient(main.app) as c:
        yield c
    main._database = None


def _parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_csv_export_habits_and_checkins(client):
    hid = client.post("/api/habits", json={"name": "Gym", "icon": "🏋", "category": "health"}).json()["id"]
    client.post("/api/checkin", json={"habit_id": hid, "date": "2026-01-09", "note": "legs"})
    habits = _parse_csv(client.get("/api/export/csv?kind=habits").json()["habits"])
    assert habits == [{"id": str(hid), "name": "Gym", "icon": "🏋", "schedule": "daily",
                       "target_per_period": "1", "category": "health", "created_at": habits[0]["created_at"]}]
    checkins = _parse_csv(client.get("/api/export/csv?kind=checkins").json()["checkins"])
    assert checkins == [{"habit_id": str(hid), "date": "2026-01-09", "note": "legs"}]
    assert client.get("/api/export/csv?kind=bogus").status_code == 400


def test_deletion_warning_in_ui_source():
    """The delete button must confirm before deleting (data-safety requirement)."""
    js = (main.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "confirm(" in js and "не можна відмінити" in js
    html = (main.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "btn-export-csv" in html  # one-click CSV export next to JSON
