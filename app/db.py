"""SQLite storage layer (stdlib sqlite3, no ORM)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '✅',
    schedule TEXT NOT NULL DEFAULT 'daily' CHECK (schedule IN ('daily', 'weekly')),
    target_per_period INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    UNIQUE (habit_id, date)
);
CREATE TABLE IF NOT EXISTS freezes (
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    UNIQUE (habit_id, date)
);
CREATE TABLE IF NOT EXISTS player (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    xp INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO player (id, xp) VALUES (1, 0);
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,                -- 'YYYY-MM'
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    target INTEGER NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,  -- check-ins of the habit this month
    damage INTEGER NOT NULL DEFAULT 0,    -- boss damage dealt so far
    completed INTEGER NOT NULL DEFAULT 0,
    rewarded INTEGER NOT NULL DEFAULT 0,  -- bonus XP already granted
    UNIQUE (month, habit_id)
);
CREATE TABLE IF NOT EXISTS xp_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount INTEGER NOT NULL,            -- positive = earned, negative = spent
    reason TEXT NOT NULL,               -- 'checkin' | 'boss_bonus' | 'shop'
    habit_id INTEGER                    -- NULL for player-wide events
);
CREATE TABLE IF NOT EXISTS badges (
    id TEXT PRIMARY KEY,                -- e.g. 'boss_2026-01_3'
    label TEXT NOT NULL,
    earned_at TEXT NOT NULL
);
"""

# Columns added after the initial MVP schema; applied to existing databases.
_MIGRATIONS = [
    ("player", "coins", "ALTER TABLE player ADD COLUMN coins INTEGER NOT NULL DEFAULT 0"),
    ("player", "shields", "ALTER TABLE player ADD COLUMN shields INTEGER NOT NULL DEFAULT 0"),
    ("habits", "category", "ALTER TABLE habits ADD COLUMN category TEXT NOT NULL DEFAULT 'health'"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    for table, column, stmt in _MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(stmt)


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        _migrate(self.conn)
        self.conn.commit()

    # -- habits -------------------------------------------------------------
    def add_habit(self, name: str, icon: str, schedule: str, target: int, created: str, category: str = "health") -> int:
        cur = self.conn.execute(
            """INSERT INTO habits(id, name, icon, schedule, target_per_period, created_at, category)
               VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM habits), ?, ?, ?, ?, ?, ?)""",
            (name, icon, schedule, target, created, category),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_habit(self, habit_id: int) -> None:
        self.conn.execute("DELETE FROM checkins WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM freezes WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM quests WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
        self.conn.commit()

    def list_habits(self, category: str | None = None) -> list[sqlite3.Row]:
        if category is None:
            return self.conn.execute("SELECT * FROM habits ORDER BY id").fetchall()
        return self.conn.execute(
            "SELECT * FROM habits WHERE category=? ORDER BY id", (category,)
        ).fetchall()

    def get_habit(self, habit_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM habits WHERE id=?", (habit_id,)).fetchone()

    # -- checkins -----------------------------------------------------------
    def add_checkin(self, habit_id: int, day: str, note: str = "") -> bool:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO checkins(habit_id, date, note) VALUES (?,?,?)",
            (habit_id, day, note),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def remove_checkin(self, habit_id: int, day: str) -> bool:
        cur = self.conn.execute("DELETE FROM checkins WHERE habit_id=? AND date=?", (habit_id, day))
        self.conn.commit()
        return cur.rowcount > 0

    def checkin_dates(self, habit_id: int | None = None) -> set[str]:
        if habit_id is None:
            rows = self.conn.execute("SELECT date FROM checkins").fetchall()
        else:
            rows = self.conn.execute("SELECT date FROM checkins WHERE habit_id=?", (habit_id,)).fetchall()
        return {r["date"] for r in rows}

    def dates_by_habit(self) -> dict[int, set[str]]:
        out: dict[int, set[str]] = {}
        for r in self.conn.execute("SELECT habit_id, date FROM checkins"):
            out.setdefault(r["habit_id"], set()).add(r["date"])
        return out

    # -- freezes ------------------------------------------------------------
    def add_freeze(self, habit_id: int, day: str) -> bool:
        cur = self.conn.execute("INSERT OR IGNORE INTO freezes(habit_id, date) VALUES (?,?)", (habit_id, day))
        self.conn.commit()
        return cur.rowcount > 0

    def freeze_dates(self) -> dict[int, set[str]]:
        out: dict[int, set[str]] = {}
        for r in self.conn.execute("SELECT habit_id, date FROM freezes"):
            out.setdefault(r["habit_id"], set()).add(r["date"])
        return out

    def freezes_this_week(self, habit_id: int, today: date) -> int:
        iso_year, iso_week, _ = today.isocalendar()
        count = 0
        for d in self.freeze_dates().get(habit_id, set()):
            y, w, _ = date.fromisoformat(d).isocalendar()
            if (y, w) == (iso_year, iso_week):
                count += 1
        return count

    # -- quests ---------------------------------------------------------------
    def add_quest(self, month: str, habit_id: int, target: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO quests(month, habit_id, target) VALUES (?,?,?)",
            (month, habit_id, target),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_quests(self, month: str | None = None) -> list[sqlite3.Row]:
        if month is None:
            return self.conn.execute("SELECT * FROM quests ORDER BY month, id").fetchall()
        return self.conn.execute(
            "SELECT * FROM quests WHERE month=? ORDER BY id", (month,)
        ).fetchall()

    def get_quest(self, quest_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM quests WHERE id=?", (quest_id,)).fetchone()

    def find_quest(self, month: str, habit_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM quests WHERE month=? AND habit_id=?", (month, habit_id)
        ).fetchone()

    def update_quest(self, quest_id: int, progress: int, damage: int, completed: bool, rewarded: bool) -> None:
        self.conn.execute(
            "UPDATE quests SET progress=?, damage=?, completed=?, rewarded=? WHERE id=?",
            (progress, damage, int(completed), int(rewarded), quest_id),
        )
        self.conn.commit()

    def checkins_in_month(self, habit_id: int | None, month: str) -> list[str]:
        """ISO dates of check-ins (optionally of one habit) inside 'YYYY-MM'."""
        if habit_id is None:
            rows = self.conn.execute(
                "SELECT date FROM checkins WHERE substr(date, 1, 7)=?", (month,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT date FROM checkins WHERE habit_id=? AND substr(date, 1, 7)=?",
                (habit_id, month),
            ).fetchall()
        return [r["date"] for r in rows]

    # -- player -------------------------------------------------------------
    def add_xp(self, amount: int) -> int:
        self.conn.execute("UPDATE player SET xp = xp + ? WHERE id = 1", (amount,))
        self.conn.commit()
        return self.conn.execute("SELECT xp FROM player WHERE id=1").fetchone()["xp"]

    def xp(self) -> int:
        return self.conn.execute("SELECT xp FROM player WHERE id=1").fetchone()["xp"]

    # -- wallet (streak shield shop) ------------------------------------------
    def add_coins(self, amount: int) -> int:
        self.conn.execute("UPDATE player SET coins = coins + ? WHERE id = 1", (amount,))
        self.conn.commit()
        return self.coins()

    def coins(self) -> int:
        return self.conn.execute("SELECT coins FROM player WHERE id=1").fetchone()["coins"]

    def add_shields(self, delta: int) -> int:
        self.conn.execute("UPDATE player SET shields = shields + ? WHERE id = 1", (delta,))
        self.conn.commit()
        return self.shields()

    def shields(self) -> int:
        return self.conn.execute("SELECT shields FROM player WHERE id=1").fetchone()["shields"]

    def log_xp(self, day: str, amount: int, reason: str, habit_id: int | None = None) -> None:
        self.conn.execute(
            "INSERT INTO xp_log(date, amount, reason, habit_id) VALUES (?,?,?,?)",
            (day, amount, reason, habit_id),
        )
        self.conn.commit()

    def pop_checkin_log(self, habit_id: int, day: str) -> int:
        """Remove the check-in XP log entry for a day; return its amount (0 if none)."""
        row = self.conn.execute(
            "SELECT id, amount FROM xp_log WHERE habit_id=? AND date=? AND reason='checkin'",
            (habit_id, day),
        ).fetchone()
        if row is None:
            return 0
        self.conn.execute("DELETE FROM xp_log WHERE id=?", (row["id"],))
        self.conn.commit()
        return row["amount"]

    def sum_xp_in_month(self, habit_id: int, month: str, reason: str = "checkin") -> int:
        """Total logged XP for one habit within 'YYYY-MM' (boss damage source)."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM xp_log "
            "WHERE habit_id=? AND reason=? AND substr(date, 1, 7)=?",
            (habit_id, reason, month),
        ).fetchone()
        return row["s"]

    # -- badges ---------------------------------------------------------------
    def add_badge(self, badge_id: str, label: str, earned_at: str) -> bool:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO badges(id, label, earned_at) VALUES (?,?,?)",
            (badge_id, label, earned_at),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def list_badges(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM badges ORDER BY earned_at, id").fetchall()

    # -- portability ----------------------------------------------------------
    def export(self) -> dict:
        habits = [dict(r) for r in self.list_habits()]
        checkins = [dict(r) for r in self.conn.execute("SELECT habit_id, date, note FROM checkins")]
        freezes = [dict(r) for r in self.conn.execute("SELECT habit_id, date FROM freezes")]
        quests = [
            {"month": q["month"], "habit_id": q["habit_id"], "target": q["target"],
             "progress": q["progress"], "damage": q["damage"],
             "completed": bool(q["completed"]), "rewarded": bool(q["rewarded"])}
            for q in self.list_quests()
        ]
        xp_log = [
            {"date": r["date"], "amount": r["amount"], "reason": r["reason"], "habit_id": r["habit_id"]}
            for r in self.conn.execute("SELECT date, amount, reason, habit_id FROM xp_log ORDER BY id")
        ]
        badges = [dict(r) for r in self.list_badges()]
        row = self.conn.execute("SELECT xp, coins, shields FROM player WHERE id=1").fetchone()
        return {"version": 1, "player": {"xp": row["xp"], "coins": row["coins"], "shields": row["shields"]},
                "habits": habits, "checkins": checkins, "freezes": freezes, "quests": quests,
                "xp_log": xp_log, "badges": badges}

    def import_data(self, data: dict) -> None:
        self.conn.execute("DELETE FROM checkins")
        self.conn.execute("DELETE FROM freezes")
        self.conn.execute("DELETE FROM quests")
        self.conn.execute("DELETE FROM xp_log")
        self.conn.execute("DELETE FROM badges")
        self.conn.execute("DELETE FROM habits")
        for h in data.get("habits", []):
            self.conn.execute(
                "INSERT INTO habits(id, name, icon, schedule, target_per_period, created_at, category) VALUES (?,?,?,?,?,?,?)",
                (h["id"], h["name"], h.get("icon", "✅"), h.get("schedule", "daily"),
                 h.get("target_per_period", 1), h["created_at"], h.get("category", "health")),
            )
        for c in data.get("checkins", []):
            self.conn.execute("INSERT OR IGNORE INTO checkins(habit_id, date, note) VALUES (?,?,?)", (c["habit_id"], c["date"], c.get("note", "")))
        for f in data.get("freezes", []):
            self.conn.execute("INSERT OR IGNORE INTO freezes(habit_id, date) VALUES (?,?)", (f["habit_id"], f["date"]))
        for q in data.get("quests", []):
            self.conn.execute(
                "INSERT INTO quests(month, habit_id, target, progress, damage, completed, rewarded) VALUES (?,?,?,?,?,?,?)",
                (q["month"], q["habit_id"], q["target"], q.get("progress", 0), q.get("damage", 0),
                 int(q.get("completed", False)), int(q.get("rewarded", False))),
            )
        self.conn.execute("UPDATE player SET xp=? WHERE id=1", (data.get("player", {}).get("xp", 0),))
        self.conn.execute("UPDATE player SET coins=? WHERE id=1", (data.get("player", {}).get("coins", 0),))
        self.conn.execute("UPDATE player SET shields=? WHERE id=1", (data.get("player", {}).get("shields", 0),))
        for e in data.get("xp_log", []):
            self.conn.execute(
                "INSERT INTO xp_log(date, amount, reason, habit_id) VALUES (?,?,?,?)",
                (e["date"], e["amount"], e["reason"], e.get("habit_id")),
            )
        for b in data.get("badges", []):
            self.conn.execute("INSERT OR IGNORE INTO badges(id, label, earned_at) VALUES (?,?,?)",
                              (b["id"], b["label"], b["earned_at"]))
        self.conn.commit()


def load_export_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
