from __future__ import annotations

import asyncio
import json
import signal
import uuid
from datetime import datetime, timezone

import asyncpg
import structlog

from backend.config import settings
from backend.db.connection import create_db_pool, create_redis_client
from backend.core.queue.priority import queue_key_for
from backend.core.scheduler.cron import next_run
from backend.models.job import JobPriority

log = structlog.get_logger(__name__)

_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    log.info("scheduler.shutdown_signal", signal=sig)
    _shutdown = True


class Scheduler:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.redis = None
        self.jobs_dispatched = 0

    async def start(self) -> None:
        log.info("scheduler.starting")
        self.pool = await create_db_pool()
        self.redis = await create_redis_client()
        await self._run_loop()
        await self.pool.close()
        await self.redis.aclose()
        log.info("scheduler.stopped")

    async def _run_loop(self) -> None:
        log.info("scheduler.ready",
                 poll_interval=settings.scheduler_poll_interval)
        while not _shutdown:
            try:
                d1 = await self._dispatch_due_jobs()
                d2 = await self._dispatch_cron_jobs()
                total = d1 + d2
                if total:
                    log.info("scheduler.dispatched", count=total)
                    self.jobs_dispatched += total
            except Exception as e:
                log.error("scheduler.poll_error", error=str(e))
            await asyncio.sleep(settings.scheduler_poll_interval)

    # ── One-shot scheduled jobs ───────────────────────────────────────────────

    async def _dispatch_due_jobs(self) -> int:
        """Push one-shot scheduled jobs that are now due."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                UPDATE jobs
                SET status     = 'queued',
                    updated_at = NOW()
                WHERE status = 'scheduled'
                  AND run_at <= NOW()
                RETURNING id, priority
                """
            )

        for row in rows:
            priority = JobPriority(row["priority"])
            await self.redis.lpush(queue_key_for(priority), str(row["id"]))
            log.info("scheduler.job_queued", job_id=str(row["id"]))

        return len(rows)

    # ── Cron recurring jobs ───────────────────────────────────────────────────

    async def _dispatch_cron_jobs(self) -> int:
        """
        Find enabled cron schedules whose next_run_at has passed.
        For each:
          1. Create a new job row in jobs table
          2. Push job ID into Redis
          3. Update schedule: last_run_at, last_job_id, next_run_at
        """
        async with self.pool.acquire() as conn:
            schedules = await conn.fetch(
                """
                SELECT * FROM schedules
                WHERE enabled = TRUE
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= NOW()
                """
            )

        dispatched = 0
        for sched in schedules:
            job_id = await self._create_cron_job(sched)
            if job_id:
                await self._advance_schedule(sched, job_id)
                dispatched += 1

        return dispatched

    async def _create_cron_job(self, sched) -> uuid.UUID | None:
        """Insert a new job row for a cron schedule tick."""
        now = datetime.now(timezone.utc)
        job_id = uuid.uuid4()
        priority = sched["priority"]

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO jobs (
                        id, task_name, payload, status, priority, queue,
                        run_at, max_retries, timeout_seconds,
                        attempt, created_at, updated_at
                    ) VALUES (
                        $1, $2, $3::jsonb, 'queued', $4, $5,
                        $6, $7, $8,
                        0, $6, $6
                    )
                    """,
                    job_id,
                    sched["task_name"],
                    sched["payload"] if isinstance(
                        sched["payload"], str) else json.dumps(sched["payload"] or {}),
                    priority,
                    sched["queue"],
                    now,
                    sched["max_retries"],
                    sched["timeout_seconds"],
                )

            queue_key = queue_key_for(JobPriority(priority))
            await self.redis.lpush(queue_key, str(job_id))

            log.info(
                "scheduler.cron_fired",
                schedule=sched["name"],
                job_id=str(job_id),
                task=sched["task_name"],
            )
            return job_id

        except Exception as e:
            log.error(
                "scheduler.cron_error",
                schedule=sched["name"],
                error=str(e),
            )
            return None

    async def _advance_schedule(self, sched, last_job_id: uuid.UUID) -> None:
        """Compute next_run_at and update the schedule row."""
        try:
            next_run_at = next_run(sched["cron_expression"])
        except ValueError as e:
            log.error(
                "scheduler.bad_cron",
                schedule=sched["name"],
                error=str(e),
            )
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE schedules
                SET last_run_at  = NOW(),
                    last_job_id  = $1,
                    next_run_at  = $2,
                    updated_at   = NOW()
                WHERE id = $3
                """,
                last_job_id,
                next_run_at,
                sched["id"],
            )

        log.info(
            "scheduler.schedule_advanced",
            schedule=sched["name"],
            next_run_at=str(next_run_at),
        )


async def main():
    import logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    scheduler = Scheduler()
    await scheduler.start()


if __name__ == "__main__":
    asyncio.run(main())
