"""Tests: settings (sound/effects toggles) behind WebAudio + level-up FX."""
import json

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


def test_settings_persist_across_connections(tmp_path):
    path = tmp_path / "persist.db"
    db = db_mod.Database(path)
    out = service.set_settings(db, {"sound": False})
    assert out == {"sound": False, "effects": True}
    reopened = db_mod.Database(path)
    assert service.get_settings(reopened) == {"sound": False, "effects": True}


def test_settings_defaults_and_unknown_key_filtering(database):
    assert service.get_settings(database) == g.DEFAULT_SETTINGS
    database.save_settings_json(json.dumps({"sound": False, "bogus": 1}))
    assert service.get_settings(database) == {"sound": False, "effects": True}
    # corrupt JSON falls back to defaults
    database.save_settings_json("not-json{")
    assert service.get_settings(database) == g.DEFAULT_SETTINGS


def test_set_settings_validates(database):
    with pytest.raises(ValueError, match="unknown setting"):
        service.set_settings(database, {"volume": 5})
    with pytest.raises(ValueError, match="boolean"):
        service.set_settings(database, {"sound": "yes"})


def test_settings_api_roundtrip(client):
    assert client.get("/api/settings").json() == {"sound": True, "effects": True}
    r = client.patch("/api/settings", json={"settings": {"sound": False}})
    assert r.status_code == 200 and r.json() == {"sound": False, "effects": True}
    assert client.get("/api/settings").json()["sound"] is False
    assert client.patch("/api/settings", json={"settings": {"nope": True}}).status_code == 400
    assert client.patch("/api/settings", json={"settings": {"sound": 3}}).status_code == 400
    # state carries the toggles so the UI can honour them without an extra call
    state = client.get("/api/state").json()
    assert state["settings"] == {"sound": False, "effects": True}


def test_settings_in_export_import(database, tmp_path):
    service.set_settings(database, {"effects": False})
    data = database.export()
    other = db_mod.Database(tmp_path / "restored.db")
    other.import_data(data)
    assert other.export() == data
    assert service.get_settings(other)["effects"] is False


def test_fx_ui_and_assets_present(tmp_path, monkeypatch):
    from pathlib import Path
    static = Path(main.STATIC_DIR)
    js = (static / "app.js").read_text(encoding="utf-8")
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "style.css").read_text(encoding="utf-8")
    assert "AudioContext" in js and "createOscillator" in js  # WebAudio blip
    assert "confetti" in js and "celebrate" in js
    assert 'id="settings"' in html and 'id="levelup"' in html
    assert "confetti-fall" in css and "levelup-pop" in css


def test_sound_toggle_guards_blip(tmp_path, monkeypatch):
    """blip() must be a no-op when the sound setting is off."""
    js = (main.STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "if (!settings.sound) return;" in js
