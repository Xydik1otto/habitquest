"""Tests: XP and level calculations."""
import pytest

from app.gamification import level_for_xp, level_progress, xp_for_checkin, xp_to_reach_level


def test_xp_base_without_streak():
    assert xp_for_checkin(0) == 10


def test_xp_streak_multiplier_grows():
    assert xp_for_checkin(1) == 11
    assert xp_for_checkin(10) == 20
    assert xp_for_checkin(30) == 40


def test_xp_multiplier_caps_at_30():
    assert xp_for_checkin(30) == xp_for_checkin(100) == 40


@pytest.mark.parametrize("level,expected", [(1, 0), (2, 50), (3, 150), (4, 300), (5, 500)])
def test_level_thresholds(level, expected):
    assert xp_to_reach_level(level) == expected


def test_level_for_xp_boundaries():
    assert level_for_xp(0) == 1
    assert level_for_xp(49) == 1
    assert level_for_xp(50) == 2
    assert level_for_xp(149) == 2
    assert level_for_xp(150) == 3


def test_level_progress_fields():
    p = level_progress(60)
    assert p["level"] == 2
    assert p["xp_in_level"] == 10
    assert p["xp_for_next"] == 100  # 150 - 50
