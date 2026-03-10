"""
main.py — FastAPI application entry point.

Run locally with:
    uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import logging
import time
import os

# ── Logging config ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dynacalorie_api")

# ── Initialize SQLite database ─────────────────────────────────────────────
from backend.database_local import init_db
init_db()
logger.info("SQLite database initialized.")

from backend.routers import auth, dashboard, logs, actions

# ── App initialization ─────────────────────────────────────────────────────
app = FastAPI(
    title="DynaCalorie AI API",
    description=(
        "Phase 2 backend powering the DynaCalorie AI app. "
        "Provides metabolic calculations, weekly budget tracking, "
        "14-day recalibration, and muscle protection guardrails."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS middleware ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(logs.router)
app.include_router(actions.router)


# ── Food Database API ──────────────────────────────────────────────────────
from backend.database_local import search_foods, get_all_foods, add_meal_entry, get_meal_entries_for_date, delete_meal_entry, upsert_daily_log, get_weekly_budget, update_weekly_budget_remaining
from backend.auth_utils import get_current_user
from fastapi import Depends, Query
from datetime import date as date_type, timedelta


@app.get("/foods", tags=["Foods"])
async def list_foods(q: str = Query(default="", description="Search query")) -> list:
    if q.strip():
        return search_foods(q.strip())
    return get_all_foods()


@app.post("/meals", tags=["Meals"])
async def create_meal(payload: dict, user_id: str = Depends(get_current_user)) -> dict:
    meal_date = payload.get("date", str(date_type.today()))
    meal_type = payload.get("meal_type", "snack")
    food_name = payload.get("food_name", "Custom Food")
    servings = float(payload.get("servings", 1))
    calories = float(payload.get("calories", 0))
    protein_g = float(payload.get("protein_g", 0))
    carbs_g = float(payload.get("carbs_g", 0))
    fat_g = float(payload.get("fat_g", 0))

    entry_id = add_meal_entry(user_id, meal_date, meal_type, food_name, servings, calories, protein_g, carbs_g, fat_g)

    # Also update daily log and weekly budget
    upsert_daily_log(user_id, meal_date, calories, protein_g)

    today = date_type.today()
    week_start = today - timedelta(days=today.weekday())
    budget = get_weekly_budget(user_id, str(week_start))
    if budget:
        new_remaining = budget["remaining_budget"] - calories
        update_weekly_budget_remaining(budget["id"], new_remaining)

    return {"id": entry_id, "message": "Meal logged."}


@app.get("/meals/{meal_date}", tags=["Meals"])
async def get_meals(meal_date: str, user_id: str = Depends(get_current_user)) -> list:
    return get_meal_entries_for_date(user_id, meal_date)


@app.delete("/meals/{entry_id}", tags=["Meals"])
async def remove_meal(entry_id: str, user_id: str = Depends(get_current_user)) -> dict:
    deleted = delete_meal_entry(entry_id, user_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Meal entry not found.")
    return {"message": "Meal deleted."}

# ── Global Error Logging Middleware ────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - {process_time:.4f}s")
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(f"{request.method} {request.url.path} - Error: {exc} - {process_time:.4f}s", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "A server error occurred. Please try again later."}
        )


# ── Mount static files for frontend ────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Serve the web app at root ──────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serves the main web app."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "DynaCalorie AI API v2 is running. Visit /docs for API documentation."})


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "DynaCalorie AI API v2"}
