"""Service layer: orchestrates check-ins, freezes, XP and achievements."""
from __future__ import annotations

from datetime import date

from . import db, gamification as g


def today_iso(today: date | None = None) -> str:
    return (today or date.today()).isoformat()


def checkin(database: db.Database, habit_id: int, day: str | None = None, note: str = "", today: date | None = None) -> dict:
    """Record a check-in, award streak-multiplied XP, return the new state."""
    habit = database.get_habit(habit_id)
    if habit is None:
        raise ValueError(f"unknown habit {habit_id}")
    day = day or today_iso(today)
    created = database.add_checkin(habit_id, day, note)
    # XP multiplier anchors to the checked-in day, not to "today"
    anchor = date.fromisoformat(day)
    streak = _habit_streak(database, habit, today=anchor)
    xp_gained = 0
    if created:
        xp_gained = g.xp_for_checkin(streak)
        database.add_xp(xp_gained)
    return {
        "habit_id": habit_id,
        "date": day,
        "created": created,
        "xp_gained": xp_gained,
        "streak": _habit_streak(database, habit, today=today or date.today()),
        "player_xp": database.xp(),
    }


def _habit_streak(database: db.Database, habit, today: date | None = None) -> int:
    dates = database.checkin_dates(habit["id"])
    freezes = database.freeze_dates().get(habit["id"], set())
    if habit["schedule"] == "weekly":
        return g.compute_streak_weekly(dates, habit["target_per_period"], today=today)
    return g.compute_streak(dates, freezes, today=today)


def use_freeze(database: db.Database, habit_id: int, day: str | None = None, today: date | None = None) -> dict:
    """Spend this week's freeze token on a day (default: today)."""
    habit = database.get_habit(habit_id)
    if habit is None:
        raise ValueError(f"unknown habit {habit_id}")
    today = today or date.today()
    if database.freezes_this_week(habit_id, today) >= g.FREEZE_WEEKLY_LIMIT:
        raise ValueError("freeze token already used this week")
    day = day or today_iso(today)
    ok = database.add_freeze(habit_id, day)
    return {"habit_id": habit_id, "date": day, "frozen": ok}


def player_state(database: db.Database) -> dict:
    return g.level_progress(database.xp())


def habit_status(database: db.Database, habit, today: date | None = None) -> dict:
    today = today or date.today()
    dates = database.checkin_dates(habit["id"])
    streak = _habit_streak(database, habit, today=today)
    status = {
        "id": habit["id"],
        "name": habit["name"],
        "icon": habit["icon"],
        "schedule": habit["schedule"],
        "target_per_period": habit["target_per_period"],
        "streak": streak,
        "done_today": today.isoformat() in dates,
        "achievements": g.evaluate_achievements(streak, len(dates), g.last_gap_days(dates, today)),
    }
    if habit["schedule"] == "weekly":
        week_dates = g.iso_dates_of_week(*today.isocalendar()[:2])
        status["week_count"] = sum(1 for d in week_dates if d.isoformat() in dates)
    return status


def full_state(database: db.Database, today: date | None = None) -> dict:
    habits = [habit_status(database, h, today) for h in database.list_habits()]
    return {"player": player_state(database), "habits": habits}


def stats(database: db.Database, today: date | None = None) -> dict:
    all_dates = database.checkin_dates()
    return {
        "longest_streak": g.longest_streak(all_dates),
        "completion_rate_30d": g.completion_rate_30d(all_dates, today),
        "total_checkins": len(all_dates),
        "player": player_state(database),
    }
