from __future__ import annotations

import asyncpg


async def queue_depths(pool: asyncpg.Pool) -> dict[str, int]:
    """Count of queued jobs per priority."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT priority, COUNT(*) AS count
            FROM jobs
            WHERE status IN ('queued', 'scheduled')
            GROUP BY priority
            """
        )
    result = {"high": 0, "normal": 0, "low": 0, "scheduled": 0}

    async with pool.acquire() as conn:
        queued = await conn.fetch(
            "SELECT priority, COUNT(*) AS count FROM jobs WHERE status = 'queued' GROUP BY priority"
        )
        scheduled = await conn.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE status = 'scheduled'"
        )

    for row in queued:
        result[row["priority"]] = row["count"]
    result["scheduled"] = scheduled or 0
    return result


async def job_counts_by_status(pool: asyncpg.Pool) -> dict[str, int]:
    """Total job count grouped by status."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
        )
    return {row["status"]: row["count"] for row in rows}


async def failure_rate_last_hour(pool: asyncpg.Pool) -> float:
    """
    Percentage of jobs that failed in the last hour.
    Returns 0.0 if no jobs completed in that window.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('failed', 'dead')) AS failures,
                COUNT(*) AS total
            FROM jobs
            WHERE completed_at >= NOW() - INTERVAL '1 hour'
              AND status IN ('completed', 'failed', 'dead')
            """
        )
    if not row or not row["total"]:
        return 0.0
    return round((row["failures"] / row["total"]) * 100, 2)


async def avg_runtime_last_hour(pool: asyncpg.Pool) -> float | None:
    """
    Average job runtime in seconds for completed jobs in the last hour.
    Returns None if no completed jobs in that window.
    """
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
            FROM jobs
            WHERE status = 'completed'
              AND completed_at >= NOW() - INTERVAL '1 hour'
              AND started_at IS NOT NULL
              AND completed_at IS NOT NULL
            """
        )
    return round(float(val), 3) if val is not None else None


async def throughput_last_hour(pool: asyncpg.Pool) -> int:
    """Number of jobs completed successfully in the last hour."""
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT COUNT(*) FROM jobs
            WHERE status = 'completed'
              AND completed_at >= NOW() - INTERVAL '1 hour'
            """
        )
    return val or 0


async def active_worker_count(pool: asyncpg.Pool) -> int:
    """Number of workers with a heartbeat in the last 30 seconds."""
    async with pool.acquire() as conn:
        val = await conn.fetchval(
            """
            SELECT COUNT(*) FROM workers
            WHERE status = 'active'
              AND last_heartbeat_at >= NOW() - INTERVAL '30 seconds'
            """
        )
    return val or 0


async def retry_stats(pool: asyncpg.Pool) -> dict:
    """Retry volume and average backoff over the last hour."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total_retries,
                AVG(backoff_seconds) AS avg_backoff_seconds
            FROM retries
            WHERE retried_at >= NOW() - INTERVAL '1 hour'
            """
        )
    return {
        "total_last_hour": row["total_retries"] or 0,
        "avg_backoff_seconds": round(float(row["avg_backoff_seconds"]), 1)
        if row["avg_backoff_seconds"] else 0.0,
    }
