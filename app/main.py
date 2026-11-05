"""FastAPI application for habitquest."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db as db_mod
from . import gamification as g
from . import service

app = FastAPI(title="habitquest", version="0.1.0")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "habitquest.db"
_database: db_mod.Database | None = None


def get_db() -> db_mod.Database:
    global _database
    if _database is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _database = db_mod.Database(DB_PATH)
    return _database


class HabitIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    icon: str = Field(default="✅", max_length=8)
    schedule: str = Field(default="daily", pattern="^(daily|weekly)$")
    target_per_period: int = Field(default=1, ge=1, le=7)


class CheckIn(BaseModel):
    habit_id: int
    date: str | None = None
    note: str = ""


class FreezeIn(BaseModel):
    habit_id: int
    date: str | None = None


class QuestIn(BaseModel):
    habit_id: int
    target: int = Field(ge=1, le=31)
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


@app.get("/api/state")
def state() -> dict:
    return service.full_state(get_db())


@app.post("/api/habits")
def create_habit(payload: HabitIn) -> dict:
    hid = get_db().add_habit(payload.name, payload.icon, payload.schedule, payload.target_per_period, date.today().isoformat())
    return {"id": hid}


@app.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: int) -> dict:
    get_db().delete_habit(habit_id)
    return {"deleted": habit_id}


@app.post("/api/checkin")
def checkin(payload: CheckIn) -> dict:
    try:
        return service.checkin(get_db(), payload.habit_id, payload.date, payload.note)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/checkin/{habit_id}/{day}")
def undo_checkin(habit_id: int, day: str) -> dict:
    ok = get_db().remove_checkin(habit_id, day)
    if not ok:
        raise HTTPException(404, "no such check-in")
    service._sync_quests_for(get_db(), habit_id, day)
    return {"removed": True, "player_xp": get_db().xp()}


@app.post("/api/quests")
def create_quest(payload: QuestIn) -> dict:
    try:
        return service.create_quest(get_db(), payload.habit_id, payload.target, payload.month)
    except ValueError as e:
        msg = str(e)
        code = 404 if "unknown habit" in msg else 400
        raise HTTPException(code, msg)


@app.get("/api/quests")
def list_quests(month: str | None = None) -> dict:
    return {"quests": service.list_quests(get_db(), month)}


@app.post("/api/freeze")
def freeze(payload: FreezeIn) -> dict:
    try:
        return service.use_freeze(get_db(), payload.habit_id, payload.date)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/heatmap")
def heatmap(weeks: int = 12) -> dict:
    dates = get_db().checkin_dates()
    return g.week_grid(dates, weeks)


@app.get("/api/stats")
def stats() -> dict:
    return service.stats(get_db())


@app.get("/api/export")
def export() -> dict:
    return get_db().export()


@app.post("/api/import")
def import_data(data: dict) -> dict:
    get_db().import_data(data)
    return {"imported": True, "player_xp": get_db().xp()}


@app.get("/api/achievements")
def achievements() -> dict:
    return {"all": g.load_achievement_defs()}


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
