"""Tests: PWA installability (manifest, service worker, icons)."""
from pathlib import Path

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
        assert "habitquest-v" in r.text and "addEventListener" in r.text


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


def test_favicon_and_og_meta(tmp_path, monkeypatch):
    favicon = Path(main.STATIC_DIR) / "icons" / "favicon.svg"
    assert favicon.exists() and b"<svg" in favicon.read_bytes()
    for c in _client(tmp_path, monkeypatch):
        r = c.get("/static/icons/favicon.svg")
        assert r.status_code == 200 and "image/svg" in r.headers["content-type"]
        html = c.get("/").text
        assert 'rel="icon"' in html and "favicon.svg" in html  # SVG favicon
        assert 'property="og:title"' in html and 'property="og:description"' in html
        assert 'property="og:image"' in html and 'name="twitter:card"' in html


def test_smoke_script_exists_and_is_executable():
    script = Path(main.STATIC_DIR).parent / "scripts" / "smoke.sh"
    assert script.exists()
    import os
    assert os.access(script, os.X_OK) or script.read_text(encoding="utf-8").startswith("#!")
