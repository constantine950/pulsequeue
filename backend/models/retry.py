"""
models/retry.py — RetryAttempt entity.
Append-only log of every retry per job.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RetryAttempt(BaseModel):
    id:              uuid.UUID
    job_id:          uuid.UUID
    attempt:         int
    error_message:   str
    error_traceback: str | None
    retried_at:      datetime
    next_retry_at:   datetime | None   # None = no more retries (job → dead)
    backoff_seconds: int

    class Config:
        from_attributes = True


class RetryAttemptResponse(BaseModel):
    id:              uuid.UUID
    job_id:          uuid.UUID
    attempt:         int
    error_message:   str
    retried_at:      datetime
    next_retry_at:   datetime | None
    backoff_seconds: int

    class Config:
        from_attributes = True
