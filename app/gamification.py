"""Pure gamification logic: XP, levels, streaks, freezes, achievements.

Everything here operates on plain dates/sets so it is unit-testable
without HTTP or the database.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

BASE_XP = 10
STREAK_CAP = 30  # multiplier caps at streak 30
FREEZE_WEEKLY_LIMIT = 1
CATEGORIES = ("health", "mind", "work", "home")
BOSS_HP_PER_TARGET = 10   # boss HP = target × 10
QUEST_BONUS_XP = 100      # one-time XP reward for slaying a monthly boss
SHIELD_PRICE = 50         # shop price of one extra freeze token (streak shield)
WEEKLY_QUEST_SIZE = 3     # habits in a weekly mini-quest
WEEKLY_QUEST_TARGET = 5   # check-ins per habit per week
WEEKLY_QUEST_REWARD = 150  # coin reward for completing the weekly quest

# User-facing toggles (WebAudio check-in sound, level-up effects, hardcore mode).
DEFAULT_SETTINGS = {"sound": True, "effects": True, "hardcore": False}
HARDCORE_PENALTY_XP = 10     # XP lost per missed (unfrozen) day in hardcore mode
HARDCORE_LOOKBACK_DAYS = 90  # how far back missed days can be penalized

ACHIEVEMENTS_FILE = Path(__file__).resolve().parent / "achievements.json"
TEMPLATES_FILE = Path(__file__).resolve().parent / "templates.json"
QUOTES_FILE = Path(__file__).resolve().parent / "quotes.json"
I18N_FILE = Path(__file__).resolve().parent / "i18n.json"
SUPPORTED_LANGS = ("uk", "en")
LANG_SETTING_KEY = "lang"  # stored in player.settings (string, 'uk'|'en')


def month_key(d: date) -> str:
    """'YYYY-MM' key of a date."""
    return f"{d.year:04d}-{d.month:02d}"


def week_key(d: date) -> str:
    """ISO week key of a date, e.g. '2026-W02'."""
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def boss_hp(target: int) -> int:
    """A monthly boss has HP proportional to the quest target."""
    return max(target, 1) * BOSS_HP_PER_TARGET


# --- XP & levels -----------------------------------------------------------
def xp_for_checkin(streak_len: int, base: int = BASE_XP) -> int:
    """XP for a check-in with the streak multiplier (1 + min(streak,30)*0.1)."""
    multiplier = 1 + min(max(streak_len, 0), STREAK_CAP) * 0.1
    return round(base * multiplier)


def xp_to_reach_level(level: int) -> int:
    """Cumulative XP needed to *be* at `level` (level 1 = 0 XP)."""
    n = level - 1
    return 50 * n * (n + 1) // 2


def level_for_xp(xp: int) -> int:
    """Highest level whose threshold is <= xp."""
    level = 1
    while xp_to_reach_level(level + 1) <= xp:
        level += 1
    return level


def level_progress(xp: int) -> dict:
    """Current level, XP within the level and XP needed for the next one."""
    level = level_for_xp(xp)
    base = xp_to_reach_level(level)
    nxt = xp_to_reach_level(level + 1)
    return {"level": level, "xp": xp, "xp_in_level": xp - base, "xp_for_next": nxt - base}


# --- streaks -----------------------------------------------------------------
def compute_streak(
    checkin_dates: set[str],
    freezes: set[str] = frozenset(),  # type: ignore[assignment]
    today: date | None = None,
) -> int:
    """Current daily streak. Freeze days are skipped without breaking it.

    If today has no check-in yet, the count starts from yesterday (today's
    pending check-in must not zero the streak).
    """
    today = today or date.today()
    freezes = set(freezes)
    d = today if today.isoformat() in checkin_dates else today - timedelta(days=1)
    streak = 0
    while True:
        iso = d.isoformat()
        if iso in checkin_dates:
            streak += 1
        elif iso in freezes:
            pass  # frozen day: excused, does not break the streak
        else:
            break
        d -= timedelta(days=1)
    return streak


def compute_streak_weekly(checkin_dates: set[str], target: int, today: date | None = None) -> int:
    """Consecutive ISO weeks with >= target check-ins, counting back from this week."""
    today = today or date.today()
    year, week, _ = today.isocalendar()
    streak = 0
    for _ in range(520):  # safety bound: 10 years
        week_dates = {d.isoformat() for d in iso_dates_of_week(year, week) if d.isoformat() in checkin_dates}
        if len(week_dates) >= target:
            streak += 1
        else:
            break
        # step back one ISO week
        monday = date.fromisocalendar(year, week, 1) - timedelta(days=7)
        year, week, _ = monday.isocalendar()
    return streak


def iso_dates_of_week(year: int, week: int) -> list[date]:
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(7)]


# --- achievements -------------------------------------------------------------
ACHIEVEMENTS = [
    {"id": "first_checkin", "name": "Перший крок", "description": "Перший чек-ін"},
    {"id": "first_week", "name": "Перший тиждень", "description": "Серія 7 днів"},
    {"id": "thirty_days", "name": "Місяць дисципліни", "description": "Серія 30 днів"},
    {"id": "comeback", "name": "Повернення", "description": "Чек-ін після паузи ≥3 днів"},
]


def evaluate_achievements(
    streak: int,
    total_checkins: int,
    last_gap_days: int | None,
) -> list[str]:
    """Return ids of achievements earned given the current stats."""
    earned: list[str] = []
    if total_checkins >= 1:
        earned.append("first_checkin")
    if streak >= 7:
        earned.append("first_week")
    if streak >= 30:
        earned.append("thirty_days")
    if last_gap_days is not None and last_gap_days >= 3:
        earned.append("comeback")
    return earned


def last_gap_days(checkin_dates: set[str], today: date | None = None) -> int | None:
    """Gap in days between the two most recent check-ins (None if <2)."""
    if len(checkin_dates) < 2:
        return None
    today = today or date.today()
    ds = sorted(date.fromisoformat(d) for d in checkin_dates)
    if ds[-1] > today:  # future dates are a data error; ignore
        ds = [d for d in ds if d <= today]
        if len(ds) < 2:
            return None
    return (ds[-1] - ds[-2]).days


# --- achievement definitions (JSON, custom achievement templates) -------------
# Schema per definition:
#   {"id": str, "name": str, "description": str,
#    "metric": "streak" | "total_checkins" | "gap_days",
#    "threshold": int}
# A definition is earned when metric >= threshold (gap_days: comeback-style).
_VALID_METRICS = ("streak", "total_checkins", "gap_days")


def validate_achievement_def(d: dict) -> None:
    """Raise ValueError if an achievement definition is malformed."""
    if not isinstance(d, dict):
        raise ValueError("achievement definition must be an object")
    for key in ("id", "name", "description", "metric", "threshold"):
        if key not in d:
            raise ValueError(f"achievement definition missing '{key}'")
    if not isinstance(d["id"], str) or not d["id"]:
        raise ValueError("achievement 'id' must be a non-empty string")
    if d["metric"] not in _VALID_METRICS:
        raise ValueError(f"unknown metric {d['metric']!r}; expected one of {_VALID_METRICS}")
    if not isinstance(d["threshold"], int) or isinstance(d["threshold"], bool) or d["threshold"] < 1:
        raise ValueError("achievement 'threshold' must be a positive integer")


def load_achievement_defs(path: Path | None = None) -> list[dict]:
    """Load achievement definitions from JSON (built-ins by default)."""
    path = path or ACHIEVEMENTS_FILE
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    defs = data.get("achievements", data) if isinstance(data, dict) else data
    if not isinstance(defs, list):
        raise ValueError("achievements JSON must contain a list")
    for d in defs:
        validate_achievement_def(d)
    return defs


ACHIEVEMENTS_COMMENT = (
    "Визначення досягнень habitquest (кастомні досягнення). Додайте об'єкти з полями "
    "id, name, description, metric (streak | total_checkins | gap_days), threshold."
)


def save_achievement_defs(defs: list[dict], path: Path | None = None) -> None:
    """Validate and persist the achievement definitions (editor storage)."""
    path = Path(path or ACHIEVEMENTS_FILE)
    for d in defs:
        validate_achievement_def(d)
    ids = [d["id"] for d in defs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate achievement id in definitions")
    payload = {"_comment": ACHIEVEMENTS_COMMENT, "achievements": defs}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_achievement_def(path: Path | None, payload: dict) -> list[dict]:
    """Validate and append a new achievement definition; returns the full list."""
    validate_achievement_def(payload)
    defs = load_achievement_defs(path)
    if any(d["id"] == payload["id"] for d in defs):
        raise ValueError(f"achievement {payload['id']!r} already exists")
    defs.append(dict(payload))
    save_achievement_defs(defs, path)
    return defs


def update_achievement_def(path: Path | None, achievement_id: str, payload: dict) -> list[dict]:
    """Replace the definition with the given id; returns the full list."""
    validate_achievement_def(payload)
    defs = load_achievement_defs(path)
    index = next((i for i, d in enumerate(defs) if d["id"] == achievement_id), None)
    if index is None:
        raise ValueError(f"unknown achievement {achievement_id!r}")
    if payload["id"] != achievement_id and any(d["id"] == payload["id"] for d in defs):
        raise ValueError(f"achievement {payload['id']!r} already exists")
    defs[index] = dict(payload)
    save_achievement_defs(defs, path)
    return defs


def evaluate_custom_achievements(
    defs: list[dict],
    streak: int,
    total_checkins: int,
    last_gap_days: int | None,
) -> list[str]:
    """Return ids of JSON-defined achievements earned for the given stats."""
    metrics = {"streak": streak, "total_checkins": total_checkins,
               "gap_days": last_gap_days if last_gap_days is not None else 0}
    earned = []
    for d in defs:
        validate_achievement_def(d)
        if metrics[d["metric"]] >= d["threshold"]:
            earned.append(d["id"])
    return earned


# --- habit templates (New Year onboarding library) ------------------------------
_VALID_SCHEDULES = ("daily", "weekly")


def validate_template(t: dict) -> None:
    """Raise ValueError if a habit template is malformed."""
    if not isinstance(t, dict):
        raise ValueError("template must be an object")
    for key in ("id", "icon", "name_ua", "name_en", "category", "schedule", "target_per_period"):
        if key not in t:
            raise ValueError(f"template missing '{key}'")
    if not isinstance(t["id"], str) or not t["id"]:
        raise ValueError("template 'id' must be a non-empty string")
    if not isinstance(t["icon"], str) or not t["icon"]:
        raise ValueError("template 'icon' must be a non-empty string")
    for key in ("name_ua", "name_en"):
        if not isinstance(t[key], str) or not t[key]:
            raise ValueError(f"template '{key}' must be a non-empty string")
    if t["category"] not in CATEGORIES:
        raise ValueError(f"unknown category {t['category']!r}; expected one of {CATEGORIES}")
    if t["schedule"] not in _VALID_SCHEDULES:
        raise ValueError(f"unknown schedule {t['schedule']!r}; expected one of {_VALID_SCHEDULES}")
    if not isinstance(t["target_per_period"], int) or isinstance(t["target_per_period"], bool) \
            or not 1 <= t["target_per_period"] <= 7:
        raise ValueError("template 'target_per_period' must be 1..7")


def load_templates(path: Path | None = None) -> list[dict]:
    """Load the habit template library from JSON (built-ins by default)."""
    data = json.loads(Path(path or TEMPLATES_FILE).read_text(encoding="utf-8"))
    templates = data.get("templates", data) if isinstance(data, dict) else data
    if not isinstance(templates, list):
        raise ValueError("templates JSON must contain a list")
    for t in templates:
        validate_template(t)
    ids = [t["id"] for t in templates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate template id")
    return templates


# --- quote of the day (local JSON, no external API) ------------------------------
def load_quotes(path: Path | None = None) -> list[dict]:
    """Load motivational quotes (UA + EN) from the local JSON file."""
    data = json.loads(Path(path or QUOTES_FILE).read_text(encoding="utf-8"))
    quotes = data.get("quotes", data) if isinstance(data, dict) else data
    if not isinstance(quotes, list) or not quotes:
        raise ValueError("quotes JSON must contain a non-empty list")
    for q in quotes:
        for key in ("ua", "en", "author"):
            if not isinstance(q.get(key), str) or not q[key].strip():
                raise ValueError(f"quote missing '{key}'")
    return quotes


def quote_of_the_day(day: date | None = None, quotes_path: Path | None = None) -> dict:
    """Deterministic quote for the given date (cycles through the list)."""
    quotes = load_quotes(quotes_path)
    d = day or date.today()
    q = quotes[d.toordinal() % len(quotes)]
    return {"date": d.isoformat(), "ua": q["ua"], "en": q["en"], "author": q["author"],
            "total": len(quotes)}


# --- i18n (UI dictionaries, UA/EN; no Russian by design) -------------------------
def load_i18n(path: Path | None = None) -> dict:
    """Load the UI dictionaries {lang: {key: string}} from JSON."""
    data = json.loads(Path(path or I18N_FILE).read_text(encoding="utf-8"))
    dict_ = data.get("dict", {})
    if not isinstance(dict_, dict) or set(dict_) < {"uk", "en"}:
        raise ValueError("i18n JSON must contain 'dict' with 'uk' and 'en'")
    return dict_


def strings_for(lang: str, path: Path | None = None) -> dict:
    """Flat string dictionary for a language ('uk' | 'en')."""
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"unsupported language {lang!r}; expected one of {SUPPORTED_LANGS}")
    return load_i18n(path)[lang]


# --- heat map -----------------------------------------------------------------
def week_grid(checkin_dates: set[str], weeks: int, today: date | None = None) -> dict:
    """Weeks × 7 grid of check-in counts for the SVG heatmap.

    Returns {"weeks": [iso-monday...], "weekdays": [0..6], "cells": {monday: [7 counts]}}
    """
    today = today or date.today()
    year, week, _ = today.isocalendar()
    cells: dict[str, list[int]] = {}
    labels: list[str] = []
    for _ in range(weeks):
        dates = iso_dates_of_week(year, week)
        labels.append(dates[0].isoformat())
        counts = [1 if d.isoformat() in checkin_dates else 0 for d in dates]
        cells[dates[0].isoformat()] = counts
        monday = dates[0] - timedelta(days=7)
        year, week, _ = monday.isocalendar()
    return {"weeks": list(reversed(labels)), "weekdays": list(range(7)),
            "cells": {w: cells[w] for w in reversed(labels)}}


def completion_rate_30d(checkin_dates: set[str], today: date | None = None) -> float:
    """Share of the last 30 days (incl. today) with at least one check-in."""
    today = today or date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(30)]
    hit = sum(1 for d in days if d in checkin_dates)
    return round(hit / 30, 3)


def longest_streak(checkin_dates: set[str]) -> int:
    """Longest run of consecutive days ever recorded."""
    if not checkin_dates:
        return 0
    ds = sorted(date.fromisoformat(d) for d in checkin_dates)
    best = cur = 1
    for prev, cur_d in zip(ds, ds[1:]):
        cur = cur + 1 if (cur_d - prev).days == 1 else 1
        best = max(best, cur)
    return best
