"""Tests: weekly mini-quests (3 habits × 5 check-ins, coin reward)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app import gamification as g, main, service

# 2026-01-10 is a Saturday of ISO week 2026-W02 (Mon 05.01 .. Sun 11.01)
TODAY = date(2026, 1, 10)
WEEK = "2026-W02"


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


def _three_habits(database):
    return [database.add_habit(n, "✅", "daily", 1, "2026-01-01")
            for n in ("Run", "Read", "Water")]


def test_week_key_is_iso():
    assert g.week_key(TODAY) == WEEK
    assert g.week_key(date(2026, 1, 4)) == "2026-W01"  # Sunday → previous week


def test_create_weekly_quest_defaults(database):
    ids = _three_habits(database)
    q = service.create_weekly_quest(database, ids, today=TODAY)
    assert q["week"] == WEEK and q["target"] == g.WEEKLY_QUEST_TARGET
    assert [h["habit_id"] for h in q["habits"]] == ids
    assert q["completed"] is False and q["reward"] == 150


def test_create_validates_input(database):
    ids = _three_habits(database)
    with pytest.raises(ValueError, match="3 distinct"):
        service.create_weekly_quest(database, ids[:2], today=TODAY)
    with pytest.raises(ValueError, match="3 distinct"):
        service.create_weekly_quest(database, [ids[0], ids[0], ids[1]], today=TODAY)
    with pytest.raises(ValueError, match="unknown habit"):
        service.create_weekly_quest(database, [ids[0], ids[1], 99], today=TODAY)
    with pytest.raises(ValueError, match="target"):
        service.create_weekly_quest(database, ids, target=8, today=TODAY)
    service.create_weekly_quest(database, ids, today=TODAY)
    with pytest.raises(ValueError, match="already exists"):
        service.create_weekly_quest(database, ids, today=TODAY)


def test_progress_and_coin_reward(database):
    ids = _three_habits(database)
    service.create_weekly_quest(database, ids, today=TODAY)
    coins_before = database.coins()
    # 5 check-ins for the first two habits
    for hid in ids[:2]:
        for d in ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):
            service.checkin(database, hid, d, today=TODAY)
    status = service.list_weekly_quests(database, today=TODAY)[0]
    assert status["completed"] is False
    assert [h["done"] for h in status["habits"]] == [5, 5, 0]
    # the third habit still needs its own 5 check-ins; the last one completes the quest
    coins_before_final = database.coins()
    gained = 0
    for d in ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):
        gained += service.checkin(database, ids[2], d, today=TODAY)["xp_gained"]
    status = service.list_weekly_quests(database, today=TODAY)[0]
    assert status["completed"] is True and status["rewarded"] is True
    assert database.coins() == coins_before_final + gained + g.WEEKLY_QUEST_REWARD
    # more check-ins do not pay the reward twice
    coins_after_reward = database.coins()
    extra = service.checkin(database, ids[2], "2026-01-10", today=TODAY)
    assert database.coins() == coins_after_reward + extra["xp_gained"]  # no extra +150


def test_undo_keeps_reward(database):
    ids = _three_habits(database)
    service.create_weekly_quest(database, ids, today=TODAY)
    for hid in ids:
        for d in ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):
            service.checkin(database, hid, d, today=TODAY)
    coins_after = database.coins()
    assert coins_after >= g.WEEKLY_QUEST_REWARD
    out = service.undo_checkin(database, ids[0], "2026-01-09")
    status = service.list_weekly_quests(database, today=TODAY)[0]
    assert status["completed"] is True and status["rewarded"] is True  # one-time reward stays
    # only the check-in XP left the wallet, the quest reward was not clawed back
    assert database.coins() == coins_after - out["xp_revoked"]


def test_only_habits_in_quest_count(database):
    ids = _three_habits(database)
    outside = database.add_habit("Outside", "🧩", "daily", 1, "2026-01-01")
    service.create_weekly_quest(database, ids, today=TODAY)
    for d in ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"):
        service.checkin(database, outside, d, today=TODAY)
    status = service.list_weekly_quests(database, today=TODAY)[0]
    assert all(h["done"] == 0 for h in status["habits"])


def test_export_import_roundtrip_includes_weekly(database, tmp_path):
    ids = _three_habits(database)
    service.create_weekly_quest(database, ids, today=TODAY)
    data = database.export()
    assert data["weekly_quests"][0]["week"] == WEEK
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data


def test_weekly_quest_api(client):
    for name in ("A", "B", "C"):
        client.post("/api/habits", json={"name": name})
    r = client.post("/api/weekly-quests", json={"habit_ids": [1, 2, 3]})
    assert r.status_code == 200
    assert r.json()["target"] == 5
    assert client.post("/api/weekly-quests", json={"habit_ids": [1, 2, 3]}).status_code == 400
    assert client.post("/api/weekly-quests", json={"habit_ids": [1, 2]}).status_code == 400
    assert client.post("/api/weekly-quests", json={"habit_ids": [1, 2, 99]}).status_code == 404
    lst = client.get("/api/weekly-quests").json()["weekly_quests"]
    assert len(lst) == 1 and lst[0]["completed"] is False
    import datetime as _dt
    monday = _dt.date.fromisocalendar(*_dt.date.today().isocalendar()[:2], 1)
    for hid in (1, 2, 3):
        for i in range(5):  # Mon..Fri of the quest's ISO week — one check-in per day counts
            client.post("/api/checkin", json={"habit_id": hid, "date": (monday + _dt.timedelta(days=i)).isoformat()})
    lst = client.get("/api/weekly-quests").json()["weekly_quests"]
    assert lst[0]["completed"] is True and lst[0]["rewarded"] is True
    state = client.get("/api/state").json()
    assert state["weekly_quests"][0]["completed"] is True
