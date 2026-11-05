"""Tests: seasonal events — recurring date-range events with a daily XP bonus."""
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


def test_event_detection_inside_range():
    ev = g.seasonal_event(date(2026, 10, 27))
    assert ev is not None and ev["key"] == "halloween" and ev["xp_bonus"] == 75


def test_new_year_wraps_over_calendar_year():
    assert g.seasonal_event(date(2026, 12, 30))["key"] == "new_year"
    assert g.seasonal_event(date(2027, 1, 2))["key"] == "new_year"
    # both edges are inclusive
    assert g.seasonal_event(date(2026, 12, 26))["key"] == "new_year"
    assert g.seasonal_event(date(2027, 1, 7))["key"] == "new_year"


def test_no_event_outside_ranges():
    for day in (date(2026, 1, 10), date(2026, 11, 5), date(2026, 5, 15), date(2026, 8, 20)):
        assert g.seasonal_event(day) is None, day


def test_all_events_have_required_fields():
    for ev in g.SEASONAL_EVENTS:
        assert set(ev) == {"key", "name", "start", "end", "xp_bonus"}
        assert ev["xp_bonus"] > 0
        date.fromisoformat(f"2026-{ev['start']}")
        date.fromisoformat(f"2026-{ev['end']}")


def test_claim_awards_bonus_once_per_day(database):
    hid = database.add_habit("Gym", "G", "daily", 1, "2026-01-01")
    service.checkin(database, hid, "2026-01-01", today=date(2026, 1, 1))
    xp_before = database.xp()
    r = service.claim_seasonal_bonus(database, today=date(2026, 1, 1))
    assert r["claimed"] is True and r["xp_gained"] == 50
    assert database.xp() == xp_before + 50
    # same day again -> no double claim
    r2 = service.claim_seasonal_bonus(database, today=date(2026, 1, 1))
    assert r2["claimed"] is False
    assert database.xp() == xp_before + 50
    # next day within the event -> claimable again
    r3 = service.claim_seasonal_bonus(database, today=date(2026, 1, 2))
    assert r3["claimed"] is True


def test_claim_raises_when_no_event(database):
    with pytest.raises(ValueError, match="no seasonal event"):
        service.claim_seasonal_bonus(database, today=date(2026, 11, 5))


def test_event_endpoints(client):
    ev = client.get("/api/event").json()
    assert ev["active"] in (True, False)
    if ev["active"]:
        assert {"key", "name", "xp_bonus"} <= set(ev)
        r = client.post("/api/event/claim")
        assert r.status_code == 200
    else:
        r = client.post("/api/event/claim")
        assert r.status_code == 400
        assert "no seasonal event" in r.json()["detail"]
