"""
core/scheduler/scheduler.py

Polls PostgreSQL every second for jobs with:
  status = 'scheduled' AND run_at <= NOW()

Pushes them into the appropriate Redis priority queue and
updates their status to 'queued'.

Also handles cron jobs (Day 16) — after each execution,
computes next_run_at and re-arms the schedule.

Run alongside the API server or as a standalone process:
  python -m backend.core.scheduler.scheduler
"""

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
                dispatched = await self._dispatch_due_jobs()
                if dispatched:
                    log.info("scheduler.dispatched", count=dispatched)
                    self.jobs_dispatched += dispatched
            except Exception as e:
                log.error("scheduler.poll_error", error=str(e))
            await asyncio.sleep(settings.scheduler_poll_interval)

    async def _dispatch_due_jobs(self) -> int:
        """
        Find all scheduled jobs due right now and push them into Redis.
        Uses a single UPDATE ... RETURNING for atomicity —
        no other process can pick up the same jobs.
        """
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
            job_id = str(row["id"])
            priority = JobPriority(row["priority"])
            queue_key = queue_key_for(priority)
            await self.redis.lpush(queue_key, job_id)
            log.info(
                "scheduler.job_queued",
                job_id=job_id,
                queue=queue_key,
            )

        return len(rows)


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
