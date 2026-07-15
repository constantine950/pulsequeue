from __future__ import annotations

import uuid

import asyncpg
import structlog

from backend.config import settings

log = structlog.get_logger(__name__)


async def mark_stale_workers(pool: asyncpg.Pool) -> list[uuid.UUID]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE workers
            SET status     = 'stale',
                updated_at = NOW()
            WHERE status = 'active'
              AND last_heartbeat_at < NOW() - ($1 || ' seconds')::INTERVAL
            RETURNING id
            """,
            str(settings.worker_stale_threshold),
        )
    stale_ids = [r["id"] for r in rows]
    if stale_ids:
        log.warning("heartbeat.workers_stale", count=len(
            stale_ids), ids=[str(i) for i in stale_ids])
    return stale_ids


async def recover_orphaned_jobs(
    stale_worker_ids: list[uuid.UUID],
    pool: asyncpg.Pool,
    redis,
) -> int:
    if not stale_worker_ids:
        return 0

    recovered = 0

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, priority FROM jobs
            WHERE status = 'running'
              AND worker_id = ANY($1::uuid[])
            """,
            stale_worker_ids,
        )

        for row in rows:
            job_id = row["id"]
            priority = row["priority"]

            # Reset to queued so worker picks it up fresh
            await conn.execute(
                """
                UPDATE jobs
                SET status     = 'queued',
                    worker_id  = NULL,
                    started_at = NULL,
                    updated_at = NOW()
                WHERE id = $1
                """,
                job_id,
            )

            from backend.core.queue.priority import queue_key_for
            from backend.models.job import JobPriority
            queue_key = queue_key_for(JobPriority(priority))
            await redis.lpush(queue_key, str(job_id))

            log.info(
                "heartbeat.job_recovered",
                job_id=str(job_id),
                queue=queue_key,
            )
            recovered += 1

    if recovered:
        log.info("heartbeat.recovery_complete", recovered=recovered)

    return recovered


async def run_recovery_cycle(pool: asyncpg.Pool, redis) -> None:
    """
    Single recovery cycle: mark stale workers → recover their jobs.
    Called every 15s from the worker's background task.
    """
    stale_ids = await mark_stale_workers(pool)
    await recover_orphaned_jobs(stale_ids, pool, redis)
