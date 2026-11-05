"""Tests: streak shield shop (XP wallet → freeze tokens)."""
from datetime import date

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


def test_checkin_pays_coins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    res = service.checkin(database, hid, "2026-01-10")
    assert res["coins"] == res["xp_gained"] == 11
    assert database.coins() == 11


def test_buy_shield_spends_coins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    for i in range(10):
        service.checkin(database, hid, f"2026-01-{i + 1:02d}")
    assert database.coins() >= g.SHIELD_PRICE
    res = service.buy_shield(database, 1, today=date(2026, 1, 10))
    assert res["bought"] == 1 and res["cost"] == g.SHIELD_PRICE
    assert database.shields() == 1
    assert database.coins() == res["coins"]
    # levels keep lifetime XP; only coins shrink
    assert database.xp() > 0


def test_buy_shield_insufficient_coins(database):
    with pytest.raises(ValueError, match="not enough coins"):
        service.buy_shield(database, 1)


def test_buy_shield_qty_validation(database):
    database.add_coins(10_000)
    with pytest.raises(ValueError, match="qty"):
        service.buy_shield(database, 0)
    with pytest.raises(ValueError, match="qty"):
        service.buy_shield(database, 11)


def test_shield_used_after_weekly_token(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    database.add_coins(10_000)
    service.buy_shield(database, 2)
    r1 = service.use_freeze(database, hid, today=date(2026, 1, 10))
    assert r1["source"] == "weekly"
    r2 = service.use_freeze(database, hid, today=date(2026, 1, 11))
    assert r2["source"] == "shield"
    assert database.shields() == 1


def test_freeze_fails_without_token_or_shield(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.use_freeze(database, hid, today=date(2026, 1, 10))
    with pytest.raises(ValueError, match="streak shield"):
        service.use_freeze(database, hid, today=date(2026, 1, 11))
    assert database.shields() == 0


def test_undo_checkin_revokes_xp_and_coins(database):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    service.checkin(database, hid, "2026-01-10")
    xp_before, coins_before = database.xp(), database.coins()
    res = service.undo_checkin(database, hid, "2026-01-10")
    assert res["removed"] is True and res["xp_revoked"] == 11
    assert database.xp() == xp_before - 11
    assert database.coins() == coins_before - 11


def test_undo_unknown_checkin_404(client):
    client.post("/api/habits", json={"name": "Gym"})
    assert client.delete("/api/checkin/1/2026-01-10").status_code == 404


def test_shop_endpoints(client):
    client.post("/api/habits", json={"name": "Gym"})
    client.post("/api/checkin", json={"habit_id": 1})
    shop = client.get("/api/shop").json()
    assert shop["shield_price"] == g.SHIELD_PRICE
    assert shop["coins"] >= 10
    # too expensive right now? then top up via many check-ins on other days
    for i in range(2, 12):
        client.post("/api/checkin", json={"habit_id": 1, "date": f"2026-01-{i:02d}"})
    coins = client.get("/api/shop").json()["coins"]
    assert client.post("/api/shop/buy", json={"item": "shield", "qty": 1}).status_code == 200
    assert client.get("/api/shop").json()["shields"] == 1
    assert client.post("/api/shop/buy", json={"item": "potion", "qty": 1}).status_code == 400
    assert client.post("/api/shop/buy", json={"item": "shield", "qty": 0}).status_code == 422
    assert client.get("/api/shop").json()["coins"] < coins  # spent on the shield


def test_export_roundtrip_keeps_wallet(database, tmp_path):
    hid = database.add_habit("Gym", "🏋", "daily", 1, "2026-01-01")
    for i in range(1, 6):
        service.checkin(database, hid, f"2026-01-{i:02d}")
    service.buy_shield(database, 1, today=date(2026, 1, 10))
    data = database.export()
    assert data["player"]["shields"] == 1
    assert any(e["reason"] == "shop" for e in data["xp_log"])
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data
