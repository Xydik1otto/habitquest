"""Tests: daily streak with freeze tokens + weekly-target streaks."""
from datetime import date, timedelta

from app.gamification import compute_streak, compute_streak_weekly, iso_dates_of_week


def d(iso: str) -> str:
    return iso


def test_streak_simple_consecutive():
    today = date(2026, 1, 10)
    dates = {(today - timedelta(days=i)).isoformat() for i in range(5)}
    assert compute_streak(dates, today=today) == 5


def test_streak_today_pending_counts_from_yesterday():
    today = date(2026, 1, 10)
    dates = {(today - timedelta(days=i)).isoformat() for i in range(1, 4)}  # 9,8,7
    assert compute_streak(dates, today=today) == 3


def test_streak_broken_by_gap():
    today = date(2026, 1, 10)
    dates = {today.isoformat(), (today - timedelta(days=1)).isoformat(), (today - timedelta(days=3)).isoformat()}
    assert compute_streak(dates, today=today) == 2


def test_freeze_does_not_break_streak():
    today = date(2026, 1, 10)
    checked = {today.isoformat(), (today - timedelta(days=2)).isoformat(), (today - timedelta(days=3)).isoformat()}
    freezes = {(today - timedelta(days=1)).isoformat()}  # yesterday frozen
    assert compute_streak(checked, freezes, today=today) == 3


def test_freeze_bridges_gaps_but_never_creates_streak():
    today = date(2026, 1, 10)
    # only today checked; two frozen days after it — streak stops at the check-ins
    freezes = {(today - timedelta(days=1)).isoformat(), (today - timedelta(days=2)).isoformat()}
    assert compute_streak({today.isoformat()}, freezes, today=today) == 1
    # with a check-in beyond the frozen gap, the freeze bridges it
    assert compute_streak({today.isoformat(), (today - timedelta(days=3)).isoformat()}, freezes, today=today) == 2


def test_weekly_streak_meets_target():
    # 3 consecutive weeks with >= 3 check-ins each
    today = date(2026, 1, 10)  # Saturday of ISO week 2
    dates = set()
    for w in (2, 1, 52):
        year = 2026 if w == 2 else (2026 if w == 1 else 2025)
        for i in range(3):
            dates.add(date.fromisocalendar(year, w, i + 1).isoformat())
    assert compute_streak_weekly(dates, target=3, today=today) == 3


def test_weekly_streak_breaks_below_target():
    today = date(2026, 1, 10)
    dates = {date.fromisocalendar(2026, 2, 1).isoformat()}  # only 1 check-in this week
    assert compute_streak_weekly(dates, target=3, today=today) == 0


def test_week_dates_monday_first():
    dates = iso_dates_of_week(2026, 2)
    assert dates[0] == date(2026, 1, 5)  # Monday
    assert dates[6] == date(2026, 1, 11)  # Sunday
