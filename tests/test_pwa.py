"""Tests: PWA installability (manifest, service worker, icons)."""
from fastapi.testclient import TestClient

from app import main


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "api.db")
    main._database = None
    with TestClient(main.app) as c:
        yield c
    main._database = None


def test_manifest_served_and_valid(tmp_path, monkeypatch):
    for c in _client(tmp_path, monkeypatch):
        r = c.get("/manifest.json")
        assert r.status_code == 200
        m = r.json()
        assert m["name"] == "HabitQuest"
        assert m["display"] == "standalone"
        assert m["start_url"] == "/" and m["scope"] == "/"
        sizes = {i["sizes"] for i in m["icons"]}
        assert {"192x192", "512x512"} <= sizes


def test_service_worker_served_with_js_mime(tmp_path, monkeypatch):
    for c in _client(tmp_path, monkeypatch):
        r = c.get("/sw.js")
        assert r.status_code == 200
        assert "text/javascript" in r.headers["content-type"]
        assert "habitquest-v1" in r.text and "addEventListener" in r.text


def test_icons_exist_and_are_png(tmp_path, monkeypatch):
    from pathlib import Path
    static = Path(main.STATIC_DIR)
    for size in (192, 512):
        p = static / "icons" / f"icon-{size}.png"
        assert p.exists() and p.stat().st_size > 100
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    for c in _client(tmp_path, monkeypatch):
        r = c.get("/static/icons/icon-192.png")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_index_links_manifest_and_registers_sw(tmp_path, monkeypatch):
    for c in _client(tmp_path, monkeypatch):
        html = c.get("/").text
        assert 'rel="manifest"' in html
        js = c.get("/static/app.js").text
        assert "serviceWorker" in js
