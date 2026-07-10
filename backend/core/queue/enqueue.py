"""
core/queue/enqueue.py
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as aioredis
import structlog

from backend.models.job import Job, JobCreate, JobPriority, JobStatus
from backend.core.queue.priority import queue_key_for

log = structlog.get_logger(__name__)


def _row_to_job(row) -> Job:
    """Convert asyncpg Record to Job, deserializing JSONB fields."""
    data = dict(row)
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    if isinstance(data.get("result"), str):
        data["result"] = json.loads(data["result"])
    return Job(**data)


async def enqueue_job(
    job_in: JobCreate,
    pool: asyncpg.Pool,
    redis: aioredis.Redis,
) -> Job:
    now = datetime.now(timezone.utc)
    job_id = uuid.uuid4()

    is_scheduled = job_in.run_at is not None and job_in.run_at > now
    status = JobStatus.scheduled if is_scheduled else JobStatus.queued

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO jobs (
                id, task_name, payload, status, priority, queue,
                run_at, scheduled_for,
                max_retries, timeout_seconds,
                attempt, created_at, updated_at
            ) VALUES (
                $1, $2, $3::jsonb, $4, $5, $6,
                $7, $8,
                $9, $10,
                0, $11, $11
            )
            RETURNING *
            """,
            job_id,
            job_in.task_name,
            json.dumps(job_in.payload),
            status.value,
            job_in.priority.value,
            job_in.queue,
            now,
            job_in.run_at if is_scheduled else None,
            job_in.max_retries,
            job_in.timeout_seconds,
            now,
        )

    job = _row_to_job(row)

    if not is_scheduled:
        queue_key = queue_key_for(job.priority)
        await redis.lpush(queue_key, str(job.id))
        log.info("job.enqueued", job_id=str(job.id),
                 task=job.task_name, queue=queue_key)
    else:
        log.info("job.scheduled", job_id=str(job.id),
                 task=job.task_name, run_at=str(job.scheduled_for))

    return job


async def requeue_job(
    job_id: uuid.UUID,
    priority: JobPriority,
    redis: aioredis.Redis,
) -> None:
    queue_key = queue_key_for(priority)
    await redis.lpush(queue_key, str(job_id))
    log.info("job.requeued", job_id=str(job_id), queue=queue_key)
