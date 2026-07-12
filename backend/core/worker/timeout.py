from __future__ import annotations

import uuid
from datetime import datetime, timezone

import asyncpg
import structlog

log = structlog.get_logger(__name__)


def is_timeout_error(error: Exception) -> bool:
    """Return True if the error is a timeout."""
    return isinstance(error, (TimeoutError, asyncio.TimeoutError))


async def find_stuck_jobs(pool: asyncpg.Pool) -> list[dict]:
    """
    Find jobs that have been in 'running' state longer than their timeout.
    These are jobs where the worker died without marking them failed.
    (Normal timeout is caught by executor.py — this catches edge cases.)
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, task_name, timeout_seconds, started_at, worker_id
            FROM jobs
            WHERE status = 'running'
              AND started_at IS NOT NULL
              AND started_at < NOW() - (timeout_seconds || ' seconds')::INTERVAL
            """
        )
    return [dict(r) for r in rows]


async def kill_stuck_jobs(pool: asyncpg.Pool, redis) -> int:
    """
    Mark stuck running jobs as failed with a timeout error message.
    Called periodically by the recovery loop (supplements heartbeat recovery).
    Returns number of jobs killed.
    """
    stuck = await find_stuck_jobs(pool)
    if not stuck:
        return 0

    killed = 0
    for job in stuck:
        job_id = job["id"]
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status          = 'failed',
                    completed_at    = NOW(),
                    error_message   = $1,
                    updated_at      = NOW()
                WHERE id = $2
                  AND status = 'running'
                """,
                f"Job exceeded timeout of {job['timeout_seconds']}s and was killed by timeout recovery",
                job_id,
            )

        log.warning(
            "timeout.job_killed",
            job_id=str(job_id),
            task=job["task_name"],
            timeout_seconds=job["timeout_seconds"],
        )

        # Hand off to retry engine
        from backend.models.job import Job
        import json
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
        if row:
            data = dict(row)
            if isinstance(data.get("payload"), str):
                data["payload"] = json.loads(data["payload"])
            if isinstance(data.get("result"), str):
                data["result"] = json.loads(data["result"])
            job_obj = Job(**data)
            from backend.core.retry.retry import handle_failure
            await handle_failure(
                job_obj,
                TimeoutError(f"Exceeded timeout of {job['timeout_seconds']}s"),
                pool,
                redis,
            )

        killed += 1

    if killed:
        log.warning("timeout.recovery_complete", killed=killed)

    return killed


import asyncio  # noqa: E402 — imported here to avoid circular at module level
