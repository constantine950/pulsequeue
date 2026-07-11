"""
core/worker/worker.py — Day 14 update.

Added: _recovery_loop() background task that runs every 15s,
marks stale workers, and re-queues their orphaned jobs.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import traceback
import uuid
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as aioredis
import structlog

from backend.config import settings
from backend.db.connection import create_db_pool, create_redis_client
from backend.core.queue.dequeue import dequeue
from backend.core.worker.executor import execute_job
from backend.core.worker.heartbeat import run_recovery_cycle
from backend.core.retry.retry import handle_failure, move_delayed_jobs
from backend.models.job import Job, JobStatus

log = structlog.get_logger(__name__)
_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    log.info("worker.shutdown_signal", signal=sig)
    _shutdown = True


def _row_to_job(row) -> Job:
    data = dict(row)
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    if isinstance(data.get("result"), str):
        data["result"] = json.loads(data["result"])
    return Job(**data)


class Worker:
    def __init__(self, worker_id: uuid.UUID | None = None):
        self.worker_id = worker_id or uuid.uuid4()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.pool: asyncpg.Pool | None = None
        self.redis: aioredis.Redis | None = None
        self.jobs_processed = 0
        self.jobs_failed = 0

    async def start(self) -> None:
        log.info("worker.starting", worker_id=str(
            self.worker_id), pid=self.pid)
        self.pool = await create_db_pool()
        self.redis = await create_redis_client()
        await self._register()
        await self._run_loop()
        await self._deregister()
        await self.pool.close()
        await self.redis.aclose()
        log.info("worker.stopped", worker_id=str(self.worker_id))

    async def _register(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workers
                    (id, hostname, pid, status, queues, started_at, updated_at)
                VALUES ($1, $2, $3, 'active', $4, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET status = 'active', pid = $3, updated_at = NOW()
                """,
                self.worker_id, self.hostname, self.pid, ["default"],
            )
        log.info("worker.registered", worker_id=str(self.worker_id))

    async def _deregister(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE workers
                SET status = 'stopped', stopped_at = NOW(), updated_at = NOW()
                WHERE id = $1
                """,
                self.worker_id,
            )

    async def _run_loop(self) -> None:
        log.info("worker.ready", worker_id=str(self.worker_id))

        background = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._delay_mover_loop()),
            asyncio.create_task(self._recovery_loop()),
        ]

        try:
            while not _shutdown:
                job_id = await dequeue(self.redis)
                if job_id is None:
                    continue
                await self._process(job_id)
        finally:
            for task in background:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _heartbeat_loop(self) -> None:
        while not _shutdown:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE workers
                        SET last_heartbeat_at = NOW(),
                            jobs_processed    = $1,
                            jobs_failed       = $2,
                            updated_at        = NOW()
                        WHERE id = $3
                        """,
                        self.jobs_processed, self.jobs_failed, self.worker_id,
                    )
                log.debug("worker.heartbeat", worker_id=str(self.worker_id))
            except Exception as e:
                log.warning("worker.heartbeat_failed", error=str(e))
            await asyncio.sleep(settings.worker_heartbeat_interval)

    async def _delay_mover_loop(self) -> None:
        while not _shutdown:
            try:
                moved = await move_delayed_jobs(self.redis, self.pool)
                if moved:
                    log.info("delay_mover.moved", count=moved)
            except Exception as e:
                log.warning("delay_mover.error", error=str(e))
            await asyncio.sleep(1.0)

    async def _recovery_loop(self) -> None:
        """Check for stale workers and recover their jobs every 15 seconds."""
        while not _shutdown:
            await asyncio.sleep(15)
            try:
                await run_recovery_cycle(self.pool, self.redis)
            except Exception as e:
                log.warning("recovery.error", error=str(e))

    async def _process(self, job_id: str) -> None:
        job = await self._load_job(job_id)
        if job is None:
            log.warning("job.not_found", job_id=job_id)
            return

        if job.status not in (JobStatus.queued, JobStatus.retrying):
            log.info("job.skipped", job_id=job_id, status=job.status.value)
            return

        log.info(
            "job.starting",
            job_id=job_id,
            task=job.task_name,
            attempt=job.attempt,
            priority=job.priority.value,
        )

        await self._mark_running(job)
        job = await self._load_job(job_id)

        success, result, error = await execute_job(job)

        if success:
            await self._mark_completed(job, result)
            self.jobs_processed += 1
            log.info("job.completed", job_id=job_id, task=job.task_name)
        else:
            await self._mark_failed(job, error)
            self.jobs_failed += 1
            log.warning(
                "job.failed",
                job_id=job_id,
                task=job.task_name,
                attempt=job.attempt,
                error=str(error),
            )
            await handle_failure(job, error, self.pool, self.redis)

    async def _load_job(self, job_id: str) -> Job | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM jobs WHERE id = $1", uuid.UUID(job_id)
            )
        if not row:
            return None
        return _row_to_job(row)

    async def _mark_running(self, job: Job) -> None:
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status     = 'running',
                    worker_id  = $1,
                    started_at = $2,
                    attempt    = attempt + 1,
                    updated_at = $2
                WHERE id = $3
                """,
                self.worker_id, now, job.id,
            )

    async def _mark_completed(self, job: Job, result: dict) -> None:
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status       = 'completed',
                    completed_at = $1,
                    result       = $2::jsonb,
                    updated_at   = $1
                WHERE id = $3
                """,
                now, json.dumps(result), job.id,
            )

    async def _mark_failed(self, job: Job, error: Exception) -> None:
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status          = 'failed',
                    completed_at    = $1,
                    error_message   = $2,
                    error_traceback = $3,
                    updated_at      = $1
                WHERE id = $4
                """,
                now, str(error), traceback.format_exc(), job.id,
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
    worker = Worker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
