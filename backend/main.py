"""
main.py — FastAPI application entry point.

Run locally with:
    uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import logging
import time
import os

# ── Logging config ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dynacalorie_api")

from backend.routers import auth, dashboard, logs, actions

# ── App initialization ─────────────────────────────────────────────────────
app = FastAPI(
    title="DynaCalorie AI API",
    description=(
        "Phase 2 backend powering the DynaCalorie AI mobile app. "
        "Provides metabolic calculations, weekly budget tracking, "
        "14-day recalibration, and muscle protection guardrails."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS middleware ────────────────────────────────────────────────────────
# Allows all origins during development; restrict to your domain in production.
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


# ── Mount static files for 3D Avatar WebView ───────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "DynaCalorie AI API v2"}
