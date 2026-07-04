"""
models/job.py — Job entity and all related Pydantic schemas.

Three layers:
  - JobStatus / JobPriority  — enums matching the DB types
  - Job                      — internal dataclass (mirrors DB row)
  - JobCreate                — what the API accepts on POST /jobs
  - JobResponse              — what the API returns
  - JobUpdate                — internal use for status transitions
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    queued = "queued"
    scheduled = "scheduled"
    running = "running"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    dead = "dead"
    cancelled = "cancelled"


class JobPriority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"


# ── Internal model (mirrors DB row exactly) ───────────────────────────────────

class Job(BaseModel):
    """
    Full job record as stored in PostgreSQL.
    Populated by loading a row from the jobs table.
    Workers operate on this object.
    """
    id:               uuid.UUID
    task_name:        str
    payload:          dict[str, Any]
    status:           JobStatus
    priority:         JobPriority
    queue:            str

    run_at:           datetime
    scheduled_for:    datetime | None

    worker_id:        uuid.UUID | None
    started_at:       datetime | None
    completed_at:     datetime | None
    timeout_seconds:  int

    max_retries:      int
    attempt:          int

    result:           dict[str, Any] | None
    error_message:    str | None
    error_traceback:  str | None

    created_at:       datetime
    updated_at:       datetime

    class Config:
        # Allow construction from asyncpg Record objects
        from_attributes = True

    # ── Derived helpers ───────────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        """True if the job will never be executed again."""
        return self.status in {
            JobStatus.completed,
            JobStatus.dead,
            JobStatus.cancelled,
        }

    @property
    def can_retry(self) -> bool:
        return self.attempt < self.max_retries

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def redis_queue_key(self) -> str:
        """The Redis list key this job belongs to based on priority."""
        return f"pulsequeue:{self.priority.value}"


# ── API request schema ─────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """
    Payload accepted by POST /jobs.
    Only task_name is required — everything else has a sensible default.
    """
    task_name:       str = Field(...,
                                 description="Registered task function name")
    payload:         dict[str, Any] = Field(default_factory=dict)
    queue:           str = Field(default="default")
    priority:        JobPriority = Field(default=JobPriority.normal)
    run_at:          datetime | None = Field(
        default=None,
        description="Schedule for future execution. None = run immediately."
    )
    max_retries:     int = Field(default=3, ge=0, le=20)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_name": "send_email",
                    "payload": {"to": "user@example.com", "subject": "Hello"},
                    "priority": "normal",
                    "max_retries": 3,
                },
                {
                    "task_name": "generate_report",
                    "payload": {"report_id": 42},
                    "priority": "high",
                    "run_at": "2024-07-01T09:00:00Z",
                    "timeout_seconds": 600,
                },
            ]
        }
    }


# ── API response schema ────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    """
    Returned by GET /jobs and POST /jobs.
    Subset of Job — omits internal fields like error_traceback.
    """
    id:              uuid.UUID
    task_name:       str
    payload:         dict[str, Any]
    status:          JobStatus
    priority:        JobPriority
    queue:           str

    run_at:          datetime
    scheduled_for:   datetime | None

    worker_id:       uuid.UUID | None
    started_at:      datetime | None
    completed_at:    datetime | None
    timeout_seconds: int

    max_retries:     int
    attempt:         int

    result:          dict[str, Any] | None
    error_message:   str | None

    created_at:      datetime
    updated_at:      datetime

    # Computed field included for the dashboard
    duration_seconds: float | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        return cls(
            **job.model_dump(exclude={"error_traceback"}),
            duration_seconds=job.duration_seconds,
        )


class JobListResponse(BaseModel):
    items:  list[JobResponse]
    total:  int
    limit:  int
    offset: int


# ── Internal update schema ─────────────────────────────────────────────────────

class JobUpdate(BaseModel):
    """
    Used internally when workers update job state.
    All fields optional — only set what changed.
    """
    status:          JobStatus | None = None
    worker_id:       uuid.UUID | None = None
    started_at:      datetime | None = None
    completed_at:    datetime | None = None
    attempt:         int | None = None
    result:          dict[str, Any] | None = None
    error_message:   str | None = None
    error_traceback: str | None = None
