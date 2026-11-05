"""Service layer: orchestrates check-ins, freezes, XP and achievements."""
from __future__ import annotations

import json
from datetime import date, timedelta

from . import db, gamification as g


def today_iso(today: date | None = None) -> str:
    return (today or date.today()).isoformat()


# --- monthly quests / boss battles -------------------------------------------
def create_quest(
    database: db.Database,
    habit_id: int,
    target: int,
    month: str | None = None,
    today: date | None = None,
) -> dict:
    """Create (or return the existing) monthly quest for a habit."""
    habit = database.get_habit(habit_id)
    if habit is None:
        raise ValueError(f"unknown habit {habit_id}")
    month = month or g.month_key(today or date.today())
    try:
        if date.fromisoformat(month + "-01").strftime("%Y-%m") != month:
            raise ValueError
    except ValueError as e:
        raise ValueError(f"invalid month {month!r}; expected 'YYYY-MM'") from e
    if not isinstance(target, int) or isinstance(target, bool) or not 1 <= target <= 31:
        raise ValueError("target must be between 1 and 31")
    if database.find_quest(month, habit_id) is not None:
        raise ValueError(f"quest for {month} / habit {habit_id} already exists")
    qid = database.add_quest(month, habit_id, target)
    _sync_quest(database, database.get_quest(qid))
    return quest_status(database, database.get_quest(qid))


def _sync_quest(database: db.Database, quest, day: str = "") -> None:
    """Recompute quest progress/damage from this month's check-in XP.

    Boss HP = target × 10; every check-in deals damage equal to the XP it
    earned (longer streaks hit harder). Victory → one-time bonus + badge.
    """
    dates = database.checkins_in_month(quest["habit_id"], quest["month"])
    progress = len(dates)
    damage = database.sum_xp_in_month(quest["habit_id"], quest["month"])
    hp = g.boss_hp(quest["target"])
    completed = damage >= hp
    rewarded = bool(quest["rewarded"])
    if completed and not quest["completed"] and not rewarded:
        database.add_xp(g.QUEST_BONUS_XP)
        database.add_coins(g.QUEST_BONUS_XP)
        database.log_xp(day or f"{quest['month']}-01", g.QUEST_BONUS_XP, "boss_bonus", quest["habit_id"])
        habit = database.get_habit(quest["habit_id"])
        name = habit["name"] if habit else f"habit {quest['habit_id']}"
        database.add_badge(
            f"boss_{quest['month']}_{quest['habit_id']}",
            f"👹 {name} — {quest['month']}",
            day or f"{quest['month']}-01",
        )
        rewarded = True
    database.update_quest(quest["id"], progress, damage, completed, rewarded)


def quest_status(database: db.Database, quest, habit=None) -> dict:
    habit = habit or database.get_habit(quest["habit_id"])
    hp = g.boss_hp(quest["target"])
    return {
        "id": quest["id"],
        "month": quest["month"],
        "habit_id": quest["habit_id"],
        "habit_name": habit["name"] if habit else "?",
        "habit_icon": habit["icon"] if habit else "✅",
        "target": quest["target"],
        "progress": quest["progress"],
        "hp": hp,
        "damage": quest["damage"],
        "completed": bool(quest["completed"]),
        "reward": g.QUEST_BONUS_XP,
    }


def list_quests(database: db.Database, month: str | None = None, today: date | None = None) -> list[dict]:
    month = month or g.month_key(today or date.today())
    out = []
    for q in database.list_quests(month):
        out.append(quest_status(database, q))
    return out


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
        database.add_coins(xp_gained)  # spendable wallet (streak shield shop)
        database.log_xp(day, xp_gained, "checkin", habit_id)
        _sync_quests_for(database, habit_id, day)
        _sync_weekly_quests_for(database, habit_id, day)
    return {
        "habit_id": habit_id,
        "date": day,
        "created": created,
        "xp_gained": xp_gained,
        "streak": _habit_streak(database, habit, today=today or date.today()),
        "player_xp": database.xp(),
        "coins": database.coins(),
    }


def undo_checkin(database: db.Database, habit_id: int, day: str) -> dict:
    """Remove a check-in and claw back the XP/coins it awarded."""
    ok = database.remove_checkin(habit_id, day)
    if not ok:
        raise ValueError("no such check-in")
    amount = database.pop_checkin_log(habit_id, day)
    if amount:
        database.add_xp(-amount)
        database.add_coins(-amount)
    _sync_quests_for(database, habit_id, day)
    _sync_weekly_quests_for(database, habit_id, day)
    return {"removed": True, "xp_revoked": amount, "player_xp": database.xp(), "coins": database.coins()}


def _sync_quests_for(database: db.Database, habit_id: int, day: str) -> None:
    """Recompute the quest of this habit whose month matches the check-in."""
    quest = database.find_quest(day[:7], habit_id)
    if quest is not None:
        _sync_quest(database, quest, day)


# --- weekly mini-quests (3 habits × N check-ins, coin reward) -------------------
def create_weekly_quest(
    database: db.Database,
    habit_ids: list[int],
    target: int = g.WEEKLY_QUEST_TARGET,
    today: date | None = None,
) -> dict:
    """Create the weekly mini-quest: 3 habits × `target` check-ins each."""
    if (not isinstance(habit_ids, list) or len(habit_ids) != g.WEEKLY_QUEST_SIZE
            or not all(isinstance(h, int) and not isinstance(h, bool) for h in habit_ids)
            or len(set(habit_ids)) != len(habit_ids)):
        raise ValueError(f"weekly quest needs {g.WEEKLY_QUEST_SIZE} distinct habit ids")
    for hid in habit_ids:
        if database.get_habit(hid) is None:
            raise ValueError(f"unknown habit {hid}")
    if not isinstance(target, int) or isinstance(target, bool) or not 1 <= target <= 7:
        raise ValueError("target must be between 1 and 7")
    week = g.week_key(today or date.today())
    rows = database.list_weekly_quests(week)
    if rows:
        raise ValueError(f"weekly quest for {week} already exists")
    qid = database.add_weekly_quest(week, habit_ids, target)
    return weekly_quest_status(database, database.get_weekly_quest(qid))


def weekly_quest_status(database: db.Database, quest, habit_by_id: dict | None = None) -> dict:
    """Progress of a weekly quest, recomputed from this week's check-ins."""
    ids = json.loads(quest["habit_ids"])
    week_dates = g.iso_dates_of_week(*_iso_year_week_of_key(quest["week"]))
    habits = habit_by_id or {h["id"]: h for h in database.list_habits()}
    per_habit = []
    for hid in ids:
        h = habits.get(hid)
        dates = database.checkin_dates(hid)
        done = sum(1 for d in week_dates if d.isoformat() in dates)
        per_habit.append({
            "habit_id": hid,
            "name": h["name"] if h else f"habit {hid}",
            "icon": h["icon"] if h else "✅",
            "done": done,
        })
    completed = all(p["done"] >= quest["target"] for p in per_habit)
    return {
        "id": quest["id"],
        "week": quest["week"],
        "target": quest["target"],
        "habits": per_habit,
        "completed": completed or bool(quest["completed"]),
        "reward": g.WEEKLY_QUEST_REWARD,
        "rewarded": bool(quest["rewarded"]),
    }


def _iso_year_week_of_key(week_key_str: str) -> tuple[int, int]:
    """Parse '2026-W02' back into (iso_year, iso_week)."""
    year, week = week_key_str.split("-W")
    return int(year), int(week)


def _sync_weekly_quest(database: db.Database, quest, day: str = "") -> None:
    """Recompute completion; on first completion grant the coin reward."""
    ids = json.loads(quest["habit_ids"])
    week_dates = g.iso_dates_of_week(*_iso_year_week_of_key(quest["week"]))
    completed = all(
        sum(1 for d in week_dates if d.isoformat() in database.checkin_dates(hid)) >= quest["target"]
        for hid in ids
    )
    rewarded = bool(quest["rewarded"])
    was = bool(quest["completed"])
    if completed and not was and not rewarded:
        database.add_coins(g.WEEKLY_QUEST_REWARD)
        database.log_xp(day or f"{quest['week']}", 0, "weekly_quest")
        rewarded = True
    # a rewarded quest stays completed even if a check-in is undone
    database.update_weekly_quest(quest["id"], completed or was, rewarded)


def _sync_weekly_quests_for(database: db.Database, habit_id: int, day: str) -> None:
    quest = database.list_weekly_quests(g.week_key(date.fromisoformat(day)))
    if quest and habit_id in json.loads(quest[0]["habit_ids"]):
        _sync_weekly_quest(database, quest[0], day)


def list_weekly_quests(database: db.Database, week: str | None = None, today: date | None = None) -> list[dict]:
    week = week or g.week_key(today or date.today())
    return [weekly_quest_status(database, q) for q in database.list_weekly_quests(week)]


def _habit_streak(database: db.Database, habit, today: date | None = None) -> int:
    dates = database.checkin_dates(habit["id"])
    freezes = database.freeze_dates().get(habit["id"], set())
    if habit["schedule"] == "weekly":
        return g.compute_streak_weekly(dates, habit["target_per_period"], today=today)
    return g.compute_streak(dates, freezes, today=today)


def use_freeze(database: db.Database, habit_id: int, day: str | None = None, today: date | None = None) -> dict:
    """Freeze a day: free weekly token first, then a bought streak shield."""
    habit = database.get_habit(habit_id)
    if habit is None:
        raise ValueError(f"unknown habit {habit_id}")
    today = today or date.today()
    day = day or today_iso(today)
    if database.freezes_this_week(habit_id, today) >= g.FREEZE_WEEKLY_LIMIT:
        # weekly token spent → try to pay with a shield from the shop
        if database.shields() > 0:
            database.add_shields(-1)
            database.add_freeze(habit_id, day)
            return {"habit_id": habit_id, "date": day, "frozen": True, "source": "shield",
                    "shields": database.shields()}
        raise ValueError("no freeze left this week — buy a streak shield in the shop")
    ok = database.add_freeze(habit_id, day)
    return {"habit_id": habit_id, "date": day, "frozen": ok, "source": "weekly"}


def streak_series(database: db.Database, habit_id: int, days: int = 30, today: date | None = None) -> dict:
    """Per-day check-in counts for the last `days` days (SVG streak chart source)."""
    habit = database.get_habit(habit_id)
    if habit is None:
        raise ValueError(f"unknown habit {habit_id}")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    today = today or date.today()
    dates = database.checkin_dates(habit_id)
    series = []
    for i in range(days - 1, -1, -1):
        iso = (today - timedelta(days=i)).isoformat()
        series.append({"date": iso, "count": 1 if iso in dates else 0})
    return {"habit_id": habit_id, "days": days, "series": series,
            "streak": _habit_streak(database, habit, today=today)}


# --- habit templates ------------------------------------------------------------
def template_by_id(templates: list[dict], template_id: str) -> dict:
    for t in templates:
        if t["id"] == template_id:
            return t
    raise ValueError(f"unknown template {template_id!r}")


def create_from_template(
    database: db.Database,
    template_id: str,
    templates_path=None,
    name: str | None = None,
    today: date | None = None,
) -> dict:
    """Add a habit from the template library (id/icon/category/schedule/target)."""
    template = template_by_id(g.load_templates(templates_path), template_id)
    hid = database.add_habit(
        name or template["name_ua"], template["icon"], template["schedule"],
        template["target_per_period"], today_iso(today), template["category"],
    )
    return {"id": hid, "template_id": template_id, "name": name or template["name_ua"],
            "icon": template["icon"], "category": template["category"],
            "schedule": template["schedule"], "target_per_period": template["target_per_period"]}


# --- settings (sound / effects) -------------------------------------------------
def get_settings(database: db.Database) -> dict:
    """Stored settings merged over the defaults (unknown keys ignored)."""
    import json as _json
    try:
        stored = _json.loads(database.settings_json() or "{}")
    except ValueError:
        stored = {}
    return {**g.DEFAULT_SETTINGS, **{k: v for k, v in stored.items() if k in g.DEFAULT_SETTINGS}}


def set_settings(database: db.Database, patch: dict) -> dict:
    """Validate and persist a partial settings update; returns the full state."""
    import json as _json
    if not isinstance(patch, dict):
        raise ValueError("settings patch must be an object")
    for key, value in patch.items():
        if key not in g.DEFAULT_SETTINGS:
            raise ValueError(f"unknown setting {key!r}; expected one of {sorted(g.DEFAULT_SETTINGS)}")
        if not isinstance(value, bool):
            raise ValueError(f"setting {key!r} must be a boolean")
    merged = {**get_settings(database), **patch}
    database.save_settings_json(_json.dumps(merged))
    return merged


# --- streak shield shop -------------------------------------------------------
def shop_state(database: db.Database) -> dict:
    return {
        "coins": database.coins(),
        "shields": database.shields(),
        "shield_price": g.SHIELD_PRICE,
        "shield_effect": "extra freeze token: saves a streak day when the weekly free token is gone",
    }


def buy_shield(database: db.Database, qty: int = 1, today: date | None = None) -> dict:
    """Spend earned XP (coins) on extra freeze tokens."""
    if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= 10:
        raise ValueError("qty must be between 1 and 10")
    cost = qty * g.SHIELD_PRICE
    if database.coins() < cost:
        raise ValueError(f"not enough coins: need {cost}, have {database.coins()}")
    database.add_coins(-cost)
    database.add_shields(qty)
    database.log_xp(today_iso(today), -cost, "shop")
    return {"bought": qty, "cost": cost, "coins": database.coins(), "shields": database.shields()}


# --- monthly recap -------------------------------------------------------------
def recap(database: db.Database, month: str | None = None, today: date | None = None) -> dict:
    """Month summary: XP flow, streaks, per-category activity, quest wins."""
    month = month or g.month_key(today or date.today())
    try:
        if date.fromisoformat(month + "-01").strftime("%Y-%m") != month:
            raise ValueError
    except ValueError as e:
        raise ValueError(f"invalid month {month!r}; expected 'YYYY-MM'") from e

    dates = set(database.checkins_in_month(None, month))
    earned, spent = database.xp_flow_in_month(month)
    counts_by_habit = database.checkin_counts_by_habit_in_month(month)

    per_category = {c: {"checkins": 0, "habits": 0} for c in g.CATEGORIES}
    top_habits = []
    for h in database.list_habits():
        n = counts_by_habit.get(h["id"], 0)
        top_habits.append({"id": h["id"], "name": h["name"], "icon": h["icon"], "checkins": n})
        if h["category"] in per_category:
            per_category[h["category"]]["checkins"] += n
            if n:
                per_category[h["category"]]["habits"] += 1
    top_habits.sort(key=lambda x: -x["checkins"])

    # weekly buckets (ISO weeks that overlap the month, clipped to it)
    weeks: dict[str, int] = {}
    for d in dates:
        y, w, _ = date.fromisoformat(d).isocalendar()
        weeks[f"{y}-W{w:02d}"] = weeks.get(f"{y}-W{w:02d}", 0) + 1
    week_bars = [{"week": k, "count": v} for k, v in sorted(weeks.items())]

    best_day, best_n = None, 0
    day_counts: dict[str, int] = {}
    for d in dates:
        day_counts[d] = day_counts.get(d, 0) + 1
    for d in sorted(day_counts):
        if day_counts[d] > best_n:
            best_day, best_n = d, day_counts[d]

    quests = database.list_quests(month)
    return {
        "month": month,
        "checkins": len(dates),
        "active_days": len(day_counts),
        "xp_earned": earned,
        "xp_spent": spent,
        "xp_net": earned - spent,
        "longest_streak": g.longest_streak(dates),
        "best_day": best_day,
        "best_day_checkins": best_n,
        "per_category": per_category,
        "top_habits": top_habits[:5],
        "weeks": week_bars,
        "quests_total": len(quests),
        "quests_won": sum(1 for q in quests if q["completed"]),
    }


def player_state(database: db.Database) -> dict:
    return g.level_progress(database.xp())


def habit_status(database: db.Database, habit, today: date | None = None,
                 achievements_path=None) -> dict:
    today = today or date.today()
    dates = database.checkin_dates(habit["id"])
    streak = _habit_streak(database, habit, today=today)
    status = {
        "id": habit["id"],
        "name": habit["name"],
        "icon": habit["icon"],
        "schedule": habit["schedule"],
        "category": habit["category"],
        "target_per_period": habit["target_per_period"],
        "streak": streak,
        "done_today": today.isoformat() in dates,
        "achievements": g.evaluate_achievements(streak, len(dates), g.last_gap_days(dates, today))
        + g.evaluate_custom_achievements(g.load_achievement_defs(achievements_path), streak, len(dates), g.last_gap_days(dates, today)),
    }
    if habit["schedule"] == "weekly":
        week_dates = g.iso_dates_of_week(*today.isocalendar()[:2])
        status["week_count"] = sum(1 for d in week_dates if d.isoformat() in dates)
    return status


def full_state(database: db.Database, today: date | None = None, category: str | None = None,
               achievements_path=None) -> dict:
    habits = [habit_status(database, h, today, achievements_path) for h in database.list_habits(category)]
    return {"player": player_state(database), "habits": habits,
            "quests": list_quests(database, today=today),
            "weekly_quests": list_weekly_quests(database, today=today),
            "settings": get_settings(database),
            "badges": [dict(b) for b in database.list_badges()]}


# --- dashboard visualizations ---------------------------------------------------
def dashboard(database: db.Database, today: date | None = None) -> dict:
    """30-day XP flow + wallet + level: the data behind the dashboard SVGs."""
    today = today or date.today()
    log = database.xp_by_day(30, today)
    xp_by_day = [{"date": (today - timedelta(days=i)).isoformat(), "xp": log.get((today - timedelta(days=i)).isoformat(), 0)}
                 for i in range(29, -1, -1)]
    all_dates = database.checkin_dates()
    return {
        "xp_by_day": xp_by_day,
        "xp_earned_30d": sum(d["xp"] for d in xp_by_day if d["xp"] > 0),
        "coins": database.coins(),
        "shields": database.shields(),
        "player": player_state(database),
        "checkins_30d": round(g.completion_rate_30d(all_dates, today) * 30),
    }


def stats(database: db.Database, today: date | None = None) -> dict:
    all_dates = database.checkin_dates()
    return {
        "longest_streak": g.longest_streak(all_dates),
        "completion_rate_30d": g.completion_rate_30d(all_dates, today),
        "total_checkins": len(all_dates),
        "player": player_state(database),
    }
