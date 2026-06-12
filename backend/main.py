"""
main.py — PulseQueue API server entry point.

Starts FastAPI, manages connection lifecycle via lifespan,
mounts all routers, and configures structured logging.

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
import backend.db.connection as db


# ── Logging setup ─────────────────────────────────────────────────────────────
# Configure structlog before anything else imports it.

def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
    )


configure_logging()
log = structlog.get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────
# Runs once at startup and once at shutdown. Owns all shared resources.

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("pulsequeue.starting", version=settings.app_version)

    # ── Startup ──
    db.db_pool = await db.create_db_pool()
    db.redis_client = await db.create_redis_client()

    log.info("pulsequeue.ready")
    yield
    # ── Shutdown ──
    log.info("pulsequeue.stopping")

    if db.db_pool:
        await db.close_db_pool(db.db_pool)
    if db.redis_client:
        await db.close_redis_client(db.redis_client)

    log.info("pulsequeue.stopped")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Distributed background job orchestration system",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — open for local dashboard dev; lock down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
# Imported here to avoid circular imports. Each router is filled in its day.

from backend.api.routes import jobs, workers, schedules, metrics  # noqa: E402

app.include_router(jobs.router,      prefix="/jobs",      tags=["jobs"])
app.include_router(workers.router,   prefix="/workers",   tags=["workers"])
app.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
app.include_router(metrics.router,   prefix="/metrics",   tags=["metrics"])


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness probe — returns 200 if the server is up."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/ready", tags=["system"])
async def ready() -> dict:
    """
    Readiness probe — checks DB and Redis connectivity.
    Returns 200 only when both are reachable.
    """
    checks: dict[str, str] = {}

    try:
        async with db.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    try:
        await db.redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )