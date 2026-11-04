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
"""


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- habits -------------------------------------------------------------
    def add_habit(self, name: str, icon: str, schedule: str, target: int, created: str) -> int:
        cur = self.conn.execute(
            """INSERT INTO habits(id, name, icon, schedule, target_per_period, created_at)
               VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM habits), ?, ?, ?, ?, ?)""",
            (name, icon, schedule, target, created),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_habit(self, habit_id: int) -> None:
        self.conn.execute("DELETE FROM checkins WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM freezes WHERE habit_id=?", (habit_id,))
        self.conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
        self.conn.commit()

    def list_habits(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM habits ORDER BY id").fetchall()

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

    # -- player -------------------------------------------------------------
    def add_xp(self, amount: int) -> int:
        self.conn.execute("UPDATE player SET xp = xp + ? WHERE id = 1", (amount,))
        self.conn.commit()
        return self.conn.execute("SELECT xp FROM player WHERE id=1").fetchone()["xp"]

    def xp(self) -> int:
        return self.conn.execute("SELECT xp FROM player WHERE id=1").fetchone()["xp"]

    # -- portability ----------------------------------------------------------
    def export(self) -> dict:
        habits = [dict(r) for r in self.list_habits()]
        checkins = [dict(r) for r in self.conn.execute("SELECT habit_id, date, note FROM checkins")]
        freezes = [dict(r) for r in self.conn.execute("SELECT habit_id, date FROM freezes")]
        return {"version": 1, "player": {"xp": self.xp()}, "habits": habits, "checkins": checkins, "freezes": freezes}

    def import_data(self, data: dict) -> None:
        self.conn.execute("DELETE FROM checkins")
        self.conn.execute("DELETE FROM freezes")
        self.conn.execute("DELETE FROM habits")
        for h in data.get("habits", []):
            self.conn.execute(
                "INSERT INTO habits(id, name, icon, schedule, target_per_period, created_at) VALUES (?,?,?,?,?,?)",
                (h["id"], h["name"], h.get("icon", "✅"), h.get("schedule", "daily"), h.get("target_per_period", 1), h["created_at"]),
            )
        for c in data.get("checkins", []):
            self.conn.execute("INSERT OR IGNORE INTO checkins(habit_id, date, note) VALUES (?,?,?)", (c["habit_id"], c["date"], c.get("note", "")))
        for f in data.get("freezes", []):
            self.conn.execute("INSERT OR IGNORE INTO freezes(habit_id, date) VALUES (?,?)", (f["habit_id"], f["date"]))
        self.conn.execute("UPDATE player SET xp=? WHERE id=1", (data.get("player", {}).get("xp", 0),))
        self.conn.commit()


def load_export_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
