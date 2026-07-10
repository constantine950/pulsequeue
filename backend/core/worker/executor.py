"""
core/worker/executor.py — filled on Day 9 (task registry + dynamic execution).
Stub returns success for any job so the worker loop can be tested today.
"""

from __future__ import annotations

from backend.models.job import Job


async def execute_job(job: Job) -> tuple[bool, dict, Exception | None]:
    """
    Execute a job's task function.

    Returns:
        (success, result_dict, error_or_None)

    Day 8 stub: always succeeds with a placeholder result.
    Real implementation added on Day 9.
    """
    return True, {"status": "stub — executor not yet implemented"}, None
