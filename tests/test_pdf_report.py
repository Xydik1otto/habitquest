"""Tests: stdlib PDF monthly report (/api/report.pdf)."""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod, main, pdf_report, service


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


def test_pdf_starts_and_ends_correctly():
    pdf = pdf_report.build_report_pdf(["Month: 2026-01", "Check-in days: 3"])
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert b"(Month: 2026-01)" in pdf and b"(Check-in days: 3)" in pdf


def test_pdf_xref_offsets_are_exact():
    """Every xref entry must point at the start of its obj."""
    pdf = pdf_report.build_report_pdf(["a", "b"])
    xref_at = int(pdf.rstrip().rsplit(b"startxref", 1)[1].split(b"%%EOF")[0].strip())
    assert pdf[xref_at:xref_at + 4] == b"xref"
    table = pdf[xref_at:].split(b"trailer", 1)[0].decode("latin-1").splitlines()
    count = int(table[1].split()[1])
    for i in range(1, count):
        offset = int(table[2 + i][:10])
        assert pdf[offset:offset + 10].decode().startswith(f"{i} 0 obj")


def test_pdf_escapes_specials_and_non_latin1():
    pdf = pdf_report.build_report_pdf(["name (v2) \\ back 100%"])
    assert rb"(name \(v2\) \\ back 100%)" in pdf
    pdf2 = pdf_report.build_report_pdf(["icon: \U0001f3cb strong"])
    assert b"icon: ? strong" in pdf2


def test_service_report_pdf_contains_month_summary(database):
    hid = database.add_habit("Gym", "G", "daily", 1, "2026-01-01")
    service.checkin(database, hid, "2026-01-05", today=date(2026, 1, 5))
    service.checkin(database, hid, "2026-01-06", today=date(2026, 1, 6))
    pdf = service.report_pdf(database, "2026-01", today=date(2026, 1, 10))
    assert pdf.startswith(b"%PDF-1.4")
    assert b"(Month: 2026-01)" in pdf
    assert b"(Check-in days: 2)" in pdf
    assert b"(Longest streak: 2)" in pdf


def test_report_endpoint_serves_pdf(client, database=None):
    client.post("/api/habits", json={"name": "Run", "schedule": "daily"})
    client.post("/api/checkin", json={"habit_id": 1, "date": "2026-11-01"})
    r = client.get("/api/report.pdf", params={"month": "2026-11"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert r.content.startswith(b"%PDF-1.4")
    assert b"(Month: 2026-11)" in r.content


def test_report_endpoint_rejects_bad_month(client):
    r = client.get("/api/report.pdf", params={"month": "2026-1"})
    assert r.status_code == 400
