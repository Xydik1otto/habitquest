"""Tests: achievement triggers."""
from datetime import date, timedelta

from app.gamification import evaluate_achievements, last_gap_days


def test_first_checkin():
    assert evaluate_achievements(streak=1, total_checkins=1, last_gap_days=None) == ["first_checkin"]


def test_first_week_at_7():
    out = evaluate_achievements(streak=7, total_checkins=7, last_gap_days=1)
    assert "first_week" in out
    assert "first_checkin" in out


def test_no_first_week_below_7():
    assert "first_week" not in evaluate_achievements(streak=6, total_checkins=6, last_gap_days=1)


def test_thirty_days():
    out = evaluate_achievements(streak=30, total_checkins=30, last_gap_days=1)
    assert {"first_week", "thirty_days"} <= set(out)


def test_comeback_after_long_gap():
    out = evaluate_achievements(streak=1, total_checkins=5, last_gap_days=5)
    assert "comeback" in out


def test_no_comeback_for_small_gap():
    assert "comeback" not in evaluate_achievements(streak=2, total_checkins=2, last_gap_days=2)


def test_last_gap_days_calculation():
    today = date(2026, 1, 10)
    dates = {today.isoformat(), (today - timedelta(days=4)).isoformat()}
    assert last_gap_days(dates, today=today) == 4


def test_last_gap_days_none_for_single():
    assert last_gap_days({"2026-01-10"}, today=date(2026, 1, 10)) is None
