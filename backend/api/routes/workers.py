"""
api/routes/workers.py

Endpoints:
  GET /workers        — list all workers with status
  GET /workers/active — only active workers (heartbeat within 30s)
  GET /workers/{id}   — single worker detail
"""

from __future__ import annotations

import uuid

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.db.connection import get_db_pool
from backend.models.worker import WorkerResponse

log = structlog.get_logger(__name__)
router = APIRouter()


def _row_to_worker(row) -> WorkerResponse:
    data = dict(row)
    # asyncpg returns text[] as a list — already correct type
    return WorkerResponse(**data)


@router.get("", response_model=list[WorkerResponse])
async def list_workers(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> list[WorkerResponse]:
    """List all workers ordered by most recently started."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM workers ORDER BY started_at DESC"
        )
    return [_row_to_worker(r) for r in rows]


@router.get("/active", response_model=list[WorkerResponse])
async def list_active_workers(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> list[WorkerResponse]:
    """List workers with a heartbeat in the last 30 seconds."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM workers
            WHERE status = 'active'
              AND last_heartbeat_at >= NOW() - INTERVAL '30 seconds'
            ORDER BY started_at DESC
            """
        )
    return [_row_to_worker(r) for r in rows]


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: uuid.UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> WorkerResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM workers WHERE id = $1", worker_id
        )
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Worker {worker_id} not found")
    return _row_to_worker(row)
