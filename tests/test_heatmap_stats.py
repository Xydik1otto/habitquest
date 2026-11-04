"""Tests: week heatmap grid + stats aggregation."""
from datetime import date, timedelta

from app.gamification import completion_rate_30d, longest_streak, week_grid


def test_week_grid_shape():
    today = date(2026, 1, 10)  # Saturday, ISO week 2
    grid = week_grid(set(), weeks=4, today=today)
    assert len(grid["weeks"]) == 4
    assert grid["weeks"][-1] == "2026-01-05"  # Monday of the current week last
    assert grid["weeks"][0] == "2025-12-15"
    assert all(len(v) == 7 for v in grid["cells"].values())


def test_week_grid_counts_checkins():
    today = date(2026, 1, 10)
    dates = {"2026-01-05", "2026-01-07"}  # Monday + Wednesday of current week
    grid = week_grid(dates, weeks=2, today=today)
    cur = grid["cells"]["2026-01-05"]
    assert cur[0] == 1 and cur[2] == 1 and cur[1] == 0
    assert sum(grid["cells"]["2025-12-29"]) == 0


def test_longest_streak_finds_max_run():
    dates = {"2026-01-01", "2026-01-02", "2026-01-03", "2026-01-07", "2026-01-08"}
    assert longest_streak(dates) == 3


def test_longest_streak_empty():
    assert longest_streak(set()) == 0


def test_completion_rate_30d():
    today = date(2026, 1, 31)
    dates = {(today - timedelta(days=i)).isoformat() for i in range(15)}
    assert completion_rate_30d(dates, today=today) == 0.5


def test_completion_rate_empty():
    assert completion_rate_30d(set(), today=date(2026, 1, 31)) == 0.0
