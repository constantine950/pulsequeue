from __future__ import annotations

import asyncio
import json
import traceback as tb_module
import uuid
from datetime import datetime, timezone

import asyncpg
import structlog

from backend.core.retry.backoff import compute_backoff
from backend.models.job import Job, JobStatus

log = structlog.get_logger(__name__)


async def handle_failure(
    job: Job,
    error: Exception,
    pool: asyncpg.Pool,
    redis,
) -> None:
    """
    Called after a job execution fails.

    If attempt < max_retries:
        - log to retries table
        - wait backoff seconds
        - re-push job ID into Redis
        - update job status → retrying

    If attempt >= max_retries:
        - log to retries table with next_retry_at=NULL
        - update job status → dead
        - push to dead letter queue
    """
    attempt = job.attempt  # already incremented by _mark_running
    error_msg = str(error)
    error_tb = tb_module.format_exc()
    now = datetime.now(timezone.utc)

    can_retry = attempt < job.max_retries

    if can_retry:
        backoff_seconds = compute_backoff(attempt)
        next_retry_at = datetime.fromtimestamp(
            now.timestamp() + backoff_seconds, tz=timezone.utc
        )
    else:
        backoff_seconds = 0
        next_retry_at = None

    # ── Write retry log entry ─────────────────────────────────────────────────
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
            "job.retrying",
            job_id=str(job.id),
            task=job.task_name,
            attempt=attempt,
            max_retries=job.max_retries,
            backoff_seconds=backoff_seconds,
        )

        # Update status → retrying
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status     = 'retrying',
                    updated_at = NOW()
                WHERE id = $1
                """,
                job.id,
            )

        # Wait the backoff period, then re-queue
        await asyncio.sleep(backoff_seconds)

        from backend.core.queue.priority import queue_key_for
        queue_key = queue_key_for(job.priority)
        await redis.lpush(queue_key, str(job.id))

        # Update status back to queued so worker picks it up
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status     = 'queued',
                    updated_at = NOW()
                WHERE id = $1
                """,
                job.id,
            )

    else:
        log.warning(
            "job.dead",
            job_id=str(job.id),
            task=job.task_name,
            attempt=attempt,
            max_retries=job.max_retries,
        )

        # Update status → dead
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status     = 'dead',
                    updated_at = NOW()
                WHERE id = $1
                """,
                job.id,
            )

        # Push to dead letter queue
        await redis.lpush("pulsequeue:dead", str(job.id))
