"""
Kairos FastAPI application.

Registers all routers, mounts static/media files, initialises the database
schema on first run, and starts APScheduler for source polling.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from kairos.config import BASE_DIR, MEDIA_DIR
from kairos.database import engine, validate_schema_columns
from kairos import models

# ── Create / migrate tables before starting routers ───────────────────────────
models.Base.metadata.create_all(bind=engine)
validate_schema_columns(models.Base)

logger = logging.getLogger(__name__)

# ── APScheduler setup ─────────────────────────────────────────────────────────
_scheduler = None

def _start_scheduler():
    """Start APScheduler with SQLite job store for source polling."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from kairos.config import DATABASE_URL

    global _scheduler
    try:
        jobstores = {
            "default": SQLAlchemyJobStore(url=DATABASE_URL)
        }
        _scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
        _scheduler.start()
        logger.info("APScheduler started (SQLite job store)")
    except Exception as exc:
        logger.warning("APScheduler failed to start (non-fatal): %s", exc)
        _scheduler = None


def _stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped")
        except Exception as exc:
            logger.warning("APScheduler shutdown error (non-fatal): %s", exc)


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is already created above, but re-run validate in case of drift
    validate_schema_columns(models.Base)
    _start_scheduler()
    logger.info("Kairos API started on port %s", app.extra.get("port", "8400"))
    yield
    _stop_scheduler()
    logger.info("Kairos API shutdown")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Kairos — Local AI Video Clipping Platform",
    description=(
        "Acquire, transcribe, clip, and assemble videos locally. "
        "No cloud required."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

_perf_logger = logging.getLogger("kairos.perf")


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log every API request with elapsed time."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    path = request.url.path

    # Skip static assets
    if path.startswith(("/media/", "/frontend/")) or path == "/favicon.ico":
        return response

    if elapsed_ms > 500:
        _perf_logger.warning(
            "SLOW  %s %s → %d  %.0f ms",
            request.method, path, response.status_code, elapsed_ms,
        )
    elif elapsed_ms > 100:
        _perf_logger.info(
            "TIMING %s %s → %d  %.0f ms",
            request.method, path, response.status_code, elapsed_ms,
        )
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
from kairos.routers import system, acquisition, library, transcription, analysis, clips, stories, timelines, render, captions  # noqa: E402

app.include_router(system.router)
app.include_router(acquisition.router)
app.include_router(library.router)
app.include_router(transcription.router)
app.include_router(analysis.router)
app.include_router(clips.router)
app.include_router(stories.router)
app.include_router(timelines.router)
app.include_router(render.router)
app.include_router(captions.router)


# ── Static file mounts ────────────────────────────────────────────────────────
# Serve media files (audio, thumbs, clips, renders) at /media
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Serve frontend if built
_frontend_dist = BASE_DIR / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/frontend", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


# ── Root route ────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    if _frontend_dist.exists():
        return RedirectResponse(url="/frontend/index.html")
    return JSONResponse({
        "name": "Kairos",
        "version": "0.1.0",
        "docs": "/api/docs",
        "health": "/api/health",
    })


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)
