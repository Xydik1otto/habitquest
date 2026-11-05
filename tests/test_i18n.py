"""Tests: i18n — UA/EN UI dictionaries, persisted language choice, no Russian."""
import json
from pathlib import Path

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


def test_i18n_json_has_complete_uk_and_en_dicts():
    dict_ = g.load_i18n()
    assert set(dict_) == {"uk", "en"}
    keys_uk, keys_en = set(dict_["uk"]), set(dict_["en"])
    assert keys_uk == keys_en and len(keys_uk) >= 40
    for key, value in dict_["en"].items():
        assert value.strip()
    # crucial keys exist in both languages
    for key in ("nav_today", "nav_recap", "set_hardcore", "filter_all", "add"):
        assert dict_["uk"][key] and dict_["en"][key]


def test_no_russian_localization_anywhere():
    """Policy: UA/EN only. Russian-specific Cyrillic letters must not appear."""
    # built via codepoints so this test file itself contains no Russian letters
    russian_only = "".join(chr(c) for c in (0x044B, 0x044A, 0x044D, 0x0451, 0x042B, 0x042A, 0x042D, 0x0401))
    for json_name in ("i18n.json", "templates.json", "quotes.json"):
        path = Path(g.__file__).parent / json_name
        data = path.read_text(encoding="utf-8")
        for letter in russian_only:
            assert letter not in data, f"Russian letter {letter!r} found in {json_name}"
    # the i18n dictionary never adds a third language
    dict_ = g.load_i18n()
    assert "ru" not in dict_


def test_strings_for_validates_language():
    assert g.strings_for("uk")["nav_today"] == "Сьогодні"
    assert g.strings_for("en")["nav_today"] == "Today"
    with pytest.raises(ValueError, match="unsupported language"):
        g.strings_for("ru")
    with pytest.raises(ValueError, match="unsupported language"):
        g.strings_for("de")


def test_lang_persists_in_player_settings(database):
    assert service.get_lang(database) == "uk"  # default
    assert service.set_lang(database, "en") == "en"
    reopened = db_mod.Database(database.conn.execute("PRAGMA database_list").fetchone()[2])
    assert service.get_lang(reopened) == "en"
    with pytest.raises(ValueError, match="unsupported language"):
        service.set_lang(database, "ru")


def test_lang_api_roundtrip(client):
    assert client.get("/api/lang").json() == {"lang": "uk", "languages": ["uk", "en"]}
    r = client.put("/api/lang", json={"lang": "en"})
    assert r.status_code == 200 and r.json() == {"lang": "en"}
    assert client.get("/api/lang").json()["lang"] == "en"
    assert client.put("/api/lang", json={"lang": "ru"}).status_code == 400
    # state round-trips the language through export/import
    data = client.get("/api/export").json()
    assert json.loads(json.dumps(data))["settings"]["lang"] == "en"


def test_i18n_api(client):
    full = client.get("/api/i18n").json()
    assert full["languages"] == ["uk", "en"] and set(full["dict"]) == {"uk", "en"}
    en = client.get("/api/i18n?lang=en").json()
    assert en["strings"]["nav_recap"] == "📊 Monthly recap"
    assert client.get("/api/i18n?lang=ru").status_code == 400
