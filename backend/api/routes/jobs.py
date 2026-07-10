"""
api/routes/jobs.py
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

import asyncpg
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.db.connection import get_db_pool, get_redis
from backend.models.job import Job, JobCreate, JobListResponse, JobResponse, JobStatus
from backend.core.queue.enqueue import enqueue_job

log = structlog.get_logger(__name__)
router = APIRouter()


def _row_to_job(row) -> Job:
    data = dict(row)
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    if isinstance(data.get("result"), str):
        data["result"] = json.loads(data["result"])
    return Job(**data)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate,
    pool: asyncpg.Pool = Depends(get_db_pool),
    redis: aioredis.Redis = Depends(get_redis),
) -> JobResponse:
    job = await enqueue_job(job_in, pool, redis)
    return JobResponse.from_job(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
    task_name: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> JobListResponse:
    conditions, params = [], []
    i = 1
    if job_status:
        conditions.append(f"status = ${i}")
        params.append(job_status.value)
        i += 1
    if task_name:
        conditions.append(f"task_name = ${i}")
        params.append(task_name)
        i += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM jobs {where} ORDER BY created_at DESC LIMIT ${i} OFFSET ${i+1}",
            *params, limit, offset,
        )
        total = await conn.fetchval(f"SELECT COUNT(*) FROM jobs {where}", *params)

    items = [JobResponse.from_job(_row_to_job(r)) for r in rows]
    return JobListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> JobResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse.from_job(_row_to_job(row))


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_id: uuid.UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT status FROM jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Job {job_id} not found")
        if row["status"] not in ("queued", "scheduled"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot cancel job with status '{row['status']}'.",
            )
        await conn.execute(
            "UPDATE jobs SET status = 'cancelled', updated_at = NOW() WHERE id = $1",
            job_id,
        )
    log.info("job.cancelled", job_id=str(job_id))
    return {"cancelled": str(job_id)}
