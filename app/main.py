"""FastAPI application for habitquest."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db as db_mod
from . import gamification as g
from . import service

app = FastAPI(title="habitquest", version="1.0.0")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "habitquest.db"
ACHIEVEMENTS_PATH = g.ACHIEVEMENTS_FILE
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
    category: str = Field(default="health", pattern="^(health|mind|work|home)$")


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


class WeeklyQuestIn(BaseModel):
    habit_ids: list[int]
    target: int = Field(default=5, ge=1, le=7)


class SettingsIn(BaseModel):
    settings: dict


class BuyIn(BaseModel):
    item: str = "shield"
    qty: int = Field(default=1, ge=1, le=10)


@app.get("/api/state")
def state(category: str | None = None) -> dict:
    if category is not None and category not in g.CATEGORIES:
        raise HTTPException(400, f"unknown category {category!r}; expected one of {g.CATEGORIES}")
    return service.full_state(get_db(), category=category, achievements_path=ACHIEVEMENTS_PATH)


@app.post("/api/habits")
def create_habit(payload: HabitIn) -> dict:
    hid = get_db().add_habit(payload.name, payload.icon, payload.schedule,
                             payload.target_per_period, date.today().isoformat(),
                             payload.category)
    return {"id": hid}


@app.get("/api/templates")
def templates() -> dict:
    return {"templates": g.load_templates()}


class TemplateIn(BaseModel):
    template_id: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=80)


@app.post("/api/habits/from-template")
def habit_from_template(payload: TemplateIn) -> dict:
    try:
        return service.create_from_template(get_db(), payload.template_id, name=payload.name)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/quote")
def quote(date_str: str | None = None) -> dict:
    try:
        day = date.fromisoformat(date_str) if date_str else None
    except ValueError as e:
        raise HTTPException(400, f"invalid date {date_str!r}; expected 'YYYY-MM-DD'") from e
    try:
        return g.quote_of_the_day(day)
    except ValueError as e:
        raise HTTPException(500, str(e))


@app.get("/api/i18n")
def i18n(lang: str | None = None) -> dict:
    """UI strings for a language; `lang` invalid → all languages + supported list."""
    if lang is None:
        return {"languages": list(g.SUPPORTED_LANGS), "dict": g.load_i18n()}
    try:
        return {"languages": list(g.SUPPORTED_LANGS), "lang": lang, "strings": g.strings_for(lang)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/lang")
def get_lang() -> dict:
    return {"lang": service.get_lang(get_db()), "languages": list(g.SUPPORTED_LANGS)}


class LangIn(BaseModel):
    lang: str


@app.put("/api/lang")
def put_lang(payload: LangIn) -> dict:
    try:
        return {"lang": service.set_lang(get_db(), payload.lang)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/first-run")
def first_run() -> dict:
    return {"first_run": service.is_first_run(get_db())}


@app.post("/api/demo")
def demo() -> dict:
    try:
        return service.seed_demo_data(get_db())
    except ValueError as e:
        raise HTTPException(409, str(e))


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
    try:
        return service.undo_checkin(get_db(), habit_id, day)
    except ValueError as e:
        raise HTTPException(404, str(e))


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


@app.post("/api/weekly-quests")
def create_weekly_quest(payload: WeeklyQuestIn) -> dict:
    try:
        return service.create_weekly_quest(get_db(), payload.habit_ids, payload.target)
    except ValueError as e:
        msg = str(e)
        code = 404 if "unknown habit" in msg else 400
        raise HTTPException(code, msg)


@app.get("/api/weekly-quests")
def list_weekly_quests(week: str | None = None) -> dict:
    return {"weekly_quests": service.list_weekly_quests(get_db(), week)}


@app.get("/api/badges")
def badges() -> dict:
    return {"badges": [dict(b) for b in get_db().list_badges()]}


@app.get("/api/recap")
def recap(month: str | None = None) -> dict:
    try:
        return service.recap(get_db(), month)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/freeze")
def freeze(payload: FreezeIn) -> dict:
    try:
        return service.use_freeze(get_db(), payload.habit_id, payload.date)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/settings")
def get_settings() -> dict:
    return service.get_settings(get_db())


@app.patch("/api/settings")
def set_settings(payload: SettingsIn) -> dict:
    try:
        return service.set_settings(get_db(), payload.settings)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/shop")
def shop() -> dict:
    return service.shop_state(get_db())


@app.post("/api/shop/buy")
def shop_buy(payload: BuyIn) -> dict:
    if payload.item != "shield":
        raise HTTPException(400, f"unknown shop item {payload.item!r}")
    try:
        return service.buy_shield(get_db(), payload.qty)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/habits/{habit_id}/series")
def habit_series(habit_id: int, days: int = 30) -> dict:
    try:
        return service.streak_series(get_db(), habit_id, days)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(404 if "unknown habit" in msg else 400, msg)


@app.get("/api/heatmap")
def heatmap(weeks: int = 12) -> dict:
    dates = get_db().checkin_dates()
    return g.week_grid(dates, weeks)


@app.get("/api/stats")
def stats() -> dict:
    return service.stats(get_db())


@app.get("/api/dashboard")
def dashboard() -> dict:
    return service.dashboard(get_db())


@app.get("/api/export")
def export() -> dict:
    return get_db().export()


@app.get("/api/report.pdf")
def report_pdf(month: str | None = None):
    """Monthly recap as a downloadable PDF (kind: application/pdf)."""
    try:
        data = service.report_pdf(get_db(), month)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=habitquest-report.pdf"},
    )


@app.get("/api/export/csv")
def export_csv(kind: str = "habits") -> dict:
    """CSV export (spreadsheet-friendly): kind=habits|checkins."""
    if kind not in ("habits", "checkins"):
        raise HTTPException(400, f"unknown csv kind {kind!r}; expected 'habits' or 'checkins'")
    return get_db().export_csv()


@app.post("/api/import")
def import_data(data: dict) -> dict:
    get_db().import_data(data)
    return {"imported": True, "player_xp": get_db().xp()}


@app.get("/api/achievements")
def achievements() -> dict:
    return {"all": g.load_achievement_defs(ACHIEVEMENTS_PATH)}


class AchievementIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=200)
    metric: str = Field(pattern="^(streak|total_checkins|gap_days)$")
    threshold: int = Field(ge=1, le=100000)


@app.post("/api/achievements")
def add_achievement(payload: AchievementIn) -> dict:
    try:
        defs = g.add_achievement_def(ACHIEVEMENTS_PATH, payload.model_dump())
    except ValueError as e:
        msg = str(e)
        raise HTTPException(409 if "already exists" in msg else 400, msg)
    return {"achievements": defs}


@app.put("/api/achievements/{achievement_id}")
def update_achievement(achievement_id: str, payload: AchievementIn) -> dict:
    try:
        defs = g.update_achievement_def(ACHIEVEMENTS_PATH, achievement_id, payload.model_dump())
    except ValueError as e:
        msg = str(e)
        code = 404 if "unknown achievement" in msg else 409 if "already exists" in msg else 400
        raise HTTPException(code, msg)
    return {"achievements": defs}


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
