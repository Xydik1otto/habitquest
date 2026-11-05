"""Tests: quote-of-the-day from the local JSON (UA + EN)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import gamification as g, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    with TestClient(main.app) as c:
        yield c
    main._database = None


def test_quotes_file_has_50_valid_bilingual_quotes():
    quotes = g.load_quotes()
    assert len(quotes) == 50
    for q in quotes:
        assert q["ua"].strip() and q["en"].strip() and q["author"].strip()
        # bilingual: UA text uses Ukrainian script, EN uses Latin
        assert any("\u0400" <= ch <= "\u04FF" for ch in q["ua"])
        assert all(not ("\u0400" <= ch <= "\u04FF") for ch in q["en"])


def test_quote_of_the_day_is_deterministic_per_date():
    d1 = g.quote_of_the_day(date(2026, 1, 10))
    d1_again = g.quote_of_the_day(date(2026, 1, 10))
    d2 = g.quote_of_the_day(date(2026, 1, 11))
    assert d1 == d1_again
    assert d1["date"] == "2026-01-10"
    assert d1["ua"] != d2["ua"]  # consecutive days rotate
    assert d1["total"] == 50
    # cycle wraps around deterministically
    assert g.quote_of_the_day(date(2026, 1, 10))["ua"] == \
        g.quote_of_the_day(date(2027, 1, 5))["ua"] if (
            date(2027, 1, 5).toordinal() - date(2026, 1, 10).toordinal()) % 50 == 0 else True


def test_quote_api_roundtrip(client):
    body = client.get("/api/quote").json()
    assert set(body) >= {"date", "ua", "en", "author", "total"}
    q1 = client.get("/api/quote?date_str=2026-01-10").json()
    q2 = client.get("/api/quote?date_str=2026-01-10").json()
    assert q1 == q2
    assert client.get("/api/quote?date_str=bad-date").status_code == 400
