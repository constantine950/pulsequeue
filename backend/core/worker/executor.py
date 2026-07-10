"""
core/worker/executor.py

Resolves task_name → callable via the registry and executes it.
Handles timeout enforcement and unknown task errors.

Returns (success, result, error) tuple — worker decides what to do next.
"""

from __future__ import annotations

import asyncio

import structlog

from backend.config import settings
from backend.models.job import Job
from backend.tasks.registry import get_task

log = structlog.get_logger(__name__)


async def execute_job(job: Job) -> tuple[bool, dict, Exception | None]:
    """
    Resolve and execute the task function for a job.

    Returns:
        (True, result_dict, None)        on success
        (False, {}, exception)           on failure
    """
    # ── 1. Resolve task ───────────────────────────────────────────────────────
    try:
        task_fn = get_task(job.task_name)
    except KeyError as e:
        log.error("executor.unknown_task",
                  task=job.task_name, job_id=str(job.id))
        return False, {}, e

    # ── 2. Execute with timeout ───────────────────────────────────────────────
    timeout = job.timeout_seconds or settings.job_default_timeout

    try:
        result = await asyncio.wait_for(
            task_fn(job.payload),
            timeout=float(timeout),
        )
        return True, result or {}, None

    except asyncio.TimeoutError:
        err = TimeoutError(
            f"Task '{job.task_name}' exceeded timeout of {timeout}s"
        )
        log.warning(
            "executor.timeout",
            task=job.task_name,
            job_id=str(job.id),
            timeout=timeout,
        )
        return False, {}, err

    except Exception as e:
        log.warning(
            "executor.task_error",
            task=job.task_name,
            job_id=str(job.id),
            error=str(e),
        )
        return False, {}, e
