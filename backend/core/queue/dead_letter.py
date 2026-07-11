from __future__ import annotations

import json
import uuid

import asyncpg
import structlog

from backend.models.job import Job

log = structlog.get_logger(__name__)

DLQ_KEY = "pulsequeue:dead"


def _row_to_job(row) -> Job:
    data = dict(row)
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    if isinstance(data.get("result"), str):
        data["result"] = json.loads(data["result"])
    return Job(**data)


async def push_to_dlq(job_id: str, redis) -> None:
    """Push a job ID onto the dead letter queue."""
    await redis.lpush(DLQ_KEY, job_id)
    log.warning("dlq.pushed", job_id=job_id)


async def list_dead_jobs(pool: asyncpg.Pool, limit: int = 50) -> list[Job]:
    """
    Return dead job records from PostgreSQL ordered by most recent first.
    Reads from DB not Redis — DB is source of truth.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM jobs
            WHERE status = 'dead'
            ORDER BY updated_at DESC
            LIMIT $1
            """,
            limit,
        )
    return [_row_to_job(r) for r in rows]


async def requeue_dead_job(
    job_id: uuid.UUID,
    pool: asyncpg.Pool,
    redis,
) -> Job:
    """
    Manually re-queue a dead job — resets attempt counter and pushes
    back into the priority queue. Used by the dashboard retry button.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)

        if not row:
            raise ValueError(f"Job {job_id} not found")

        job = _row_to_job(row)

        if job.status.value != "dead":
            raise ValueError(
                f"Job {job_id} is not dead (status: {job.status.value}). "
                "Only dead jobs can be manually re-queued."
            )

        # Reset for a fresh run
        await conn.execute(
            """
            UPDATE jobs
            SET status          = 'queued',
                attempt         = 0,
                error_message   = NULL,
                error_traceback = NULL,
                started_at      = NULL,
                completed_at    = NULL,
                worker_id       = NULL,
                updated_at      = NOW()
            WHERE id = $1
            """,
            job_id,
        )

    from backend.core.queue.priority import queue_key_for
    queue_key = queue_key_for(job.priority)
    await redis.lpush(queue_key, str(job_id))

    log.info("dlq.requeued", job_id=str(job_id), queue=queue_key)

    # Return refreshed job
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    return _row_to_job(row)


async def dlq_depth(redis) -> int:
    """Return the number of job IDs currently in the DLQ Redis list."""
    return await redis.llen(DLQ_KEY)


async def purge_dlq(redis) -> int:
    """
    Remove all entries from the DLQ Redis list.
    Does NOT change job status in PostgreSQL — jobs remain 'dead' in DB.
    Returns number of entries removed.
    """
    depth = await dlq_depth(redis)
    if depth:
        await redis.delete(DLQ_KEY)
    log.warning("dlq.purged", count=depth)
    return depth
