from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from backend.db.connection import get_db_pool
from backend.metrics.aggregator import get_snapshot
from backend.metrics.collector import (
    active_worker_count,
    queue_depths,
)

router = APIRouter()


@router.get("")
async def get_metrics(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    return await get_snapshot(pool)


@router.get("/queue")
async def get_queue_metrics(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """Queue depth by priority — lightweight endpoint for quick checks."""
    depths = await queue_depths(pool)
    total = sum(depths.values())
    return {"queue_depth": depths, "total_queued": total}


@router.get("/workers")
async def get_worker_metrics(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """Active worker count — used by the worker status widget."""
    count = await active_worker_count(pool)
    return {"active_workers": count}
