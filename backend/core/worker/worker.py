"""
core/worker/worker.py

The main worker loop. Run this as a separate process from the API server:

    python -m backend.core.worker.worker

Loop:
  1. BRPOP job ID from Redis (blocks until available)
  2. Load full job record from PostgreSQL
  3. Mark job as running
  4. Hand off to executor
  5. Handle success / failure
  6. Repeat
"""

from __future__ import annotations

import asyncio
import signal
import socket
import os
import uuid
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as aioredis
import structlog

from backend.config import settings
from backend.db.connection import create_db_pool, create_redis_client
from backend.core.queue.dequeue import dequeue
from backend.core.worker.executor import execute_job
from backend.models.job import Job, JobStatus

log = structlog.get_logger(__name__)

# Graceful shutdown flag — set by SIGINT/SIGTERM
_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    log.info("worker.shutdown_signal", signal=sig)
    _shutdown = True


class Worker:
    def __init__(self, worker_id: uuid.UUID | None = None):
        self.worker_id = worker_id or uuid.uuid4()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self.pool: asyncpg.Pool | None = None
        self.redis: aioredis.Redis | None = None
        self.jobs_processed = 0
        self.jobs_failed = 0

    # Lifecycle

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
        """Insert a row into the workers table."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workers (id, hostname, pid, status, queues, started_at, updated_at)
                VALUES ($1, $2, $3, 'active', $4, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET status = 'active', pid = $3, updated_at = NOW()
                """,
                self.worker_id,
                self.hostname,
                self.pid,
                ["default"],
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
        log.info("worker.deregistered", worker_id=str(self.worker_id))

    # Main loop

    async def _run_loop(self) -> None:
        log.info("worker.ready", worker_id=str(self.worker_id))

        # Start heartbeat as a background task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while not _shutdown:
                job_id = await dequeue(self.redis)

                if job_id is None:
                    # BRPOP timeout — loop and check _shutdown
                    continue

                await self._process(job_id)

        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _process(self, job_id: str) -> None:
        """Load and execute one job."""
        job = await self._load_job(job_id)

        if job is None:
            log.warning("job.not_found", job_id=job_id)
            return

        if job.status not in (JobStatus.queued, JobStatus.retrying):
            # Job was cancelled between enqueue and dequeue
            log.info("job.skipped", job_id=job_id, status=job.status.value)
            return

        log.info("job.starting", job_id=job_id,
                 task=job.task_name, attempt=job.attempt)
        await self._mark_running(job)

        success, result, error = await execute_job(job)

        if success:
            await self._mark_completed(job, result)
            self.jobs_processed += 1
            log.info("job.completed", job_id=job_id, task=job.task_name)
        else:
            await self._mark_failed(job, error)
            self.jobs_failed += 1
            log.warning("job.failed", job_id=job_id,
                        task=job.task_name, error=str(error))

    # DB helpers

    async def _load_job(self, job_id: str) -> Job | None:
        import json
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM jobs WHERE id = $1", uuid.UUID(job_id))
        if not row:
            return None
        data = dict(row)
        if isinstance(data.get("payload"), str):
            data["payload"] = json.loads(data["payload"])
        if isinstance(data.get("result"), str):
            data["result"] = json.loads(data["result"])
        return Job(**data)

    async def _mark_running(self, job: Job) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    worker_id = $1,
                    started_at = $2,
                    updated_at = $2
                WHERE id = $3
                """,
                self.worker_id,
                datetime.now(timezone.utc),
                job.id,
            )

    async def _mark_completed(self, job: Job, result: dict) -> None:
        import json
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'completed',
                    completed_at = $1,
                    result = $2::jsonb,
                    updated_at = $1
                WHERE id = $3
                """,
                now,
                json.dumps(result),
                job.id,
            )

    async def _mark_failed(self, job: Job, error: Exception) -> None:
        import traceback
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    completed_at = $1,
                    error_message = $2,
                    error_traceback = $3,
                    updated_at = $1
                WHERE id = $4
                """,
                now,
                str(error),
                traceback.format_exc(),
                job.id,
            )

    # Heartbeat

    async def _heartbeat_loop(self) -> None:
        while not _shutdown:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE workers
                        SET last_heartbeat_at = NOW(),
                            jobs_processed = $1,
                            jobs_failed = $2,
                            updated_at = NOW()
                        WHERE id = $3
                        """,
                        self.jobs_processed,
                        self.jobs_failed,
                        self.worker_id,
                    )
                log.debug("worker.heartbeat", worker_id=str(self.worker_id))
            except Exception as e:
                log.warning("worker.heartbeat_failed", error=str(e))

            await asyncio.sleep(settings.worker_heartbeat_interval)


# Entrypoint

async def main():
    import logging
    import structlog

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
