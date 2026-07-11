from __future__ import annotations

import time
import traceback as tb_module
import uuid
from datetime import datetime, timezone

import asyncpg
import structlog

from backend.core.retry.backoff import compute_backoff

log = structlog.get_logger(__name__)

# Redis sorted set key for delayed retries
DELAYED_QUEUE_KEY = "pulsequeue:delayed"


async def handle_failure(
    job,
    error: Exception,
    pool: asyncpg.Pool,
    redis,
) -> None:
    """
    Called after a job fails. Writes retry log, then either:
      - Schedules a delayed retry via Redis sorted set (non-blocking)
      - Marks job as dead and pushes to dead letter queue
    """
    attempt = job.attempt
    error_msg = str(error)
    error_tb = tb_module.format_exc()
    now = datetime.now(timezone.utc)

    can_retry = attempt < job.max_retries

    if can_retry:
        backoff_seconds = compute_backoff(attempt)
        due_at = now.timestamp() + backoff_seconds
        next_retry_at = datetime.fromtimestamp(due_at, tz=timezone.utc)
    else:
        backoff_seconds = 0
        due_at = None
        next_retry_at = None

    # ── Write retry log ───────────────────────────────────────────────────────
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO retries
                (id, job_id, attempt, error_message, error_traceback,
                 retried_at, next_retry_at, backoff_seconds)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            uuid.uuid4(),
            job.id,
            attempt,
            error_msg,
            error_tb,
            now,
            next_retry_at,
            backoff_seconds,
        )

    if can_retry:
        log.info(
            "job.retry_scheduled",
            job_id=str(job.id),
            task=job.task_name,
            attempt=attempt,
            max_retries=job.max_retries,
            backoff_seconds=backoff_seconds,
        )

        # Update status → retrying
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET status = 'retrying', updated_at = NOW() WHERE id = $1",
                job.id,
            )

        # Push into delayed sorted set with score = due timestamp
        # Worker is NOT blocked — it immediately processes next job
        await redis.zadd(DELAYED_QUEUE_KEY, {str(job.id): due_at})

    else:
        log.warning(
            "job.dead",
            job_id=str(job.id),
            task=job.task_name,
            attempt=attempt,
            max_retries=job.max_retries,
        )

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET status = 'dead', updated_at = NOW() WHERE id = $1",
                job.id,
            )

        await redis.lpush("pulsequeue:dead", str(job.id))


async def move_delayed_jobs(redis, pool: asyncpg.Pool) -> int:
    """
    Move jobs whose backoff delay has elapsed from the delayed sorted set
    back into their priority queue.

    Called every second by the worker's background task (or scheduler).
    Returns number of jobs moved.
    """
    import json
    now_score = time.time()

    # Atomically pop all members with score <= now
    due_job_ids = await redis.zrangebyscore(
        DELAYED_QUEUE_KEY, "-inf", now_score
    )

    if not due_job_ids:
        return 0

    moved = 0
    for job_id_str in due_job_ids:
        # Load priority from DB to push into the right queue
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT priority FROM jobs WHERE id = $1",
                uuid.UUID(job_id_str),
            )

        if row:
            from backend.core.queue.priority import queue_key_for
            from backend.models.job import JobPriority
            priority = JobPriority(row["priority"])
            queue_key = queue_key_for(priority)
            await redis.lpush(queue_key, job_id_str)

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE jobs SET status = 'queued', updated_at = NOW() WHERE id = $1",
                    uuid.UUID(job_id_str),
                )

            log.info("job.retry_ready", job_id=job_id_str)
            moved += 1

        # Remove from delayed set
        await redis.zrem(DELAYED_QUEUE_KEY, job_id_str)

    return moved
