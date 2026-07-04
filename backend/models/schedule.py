"""
models/schedule.py — Schedule entity for cron jobs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.models.job import JobPriority


class Schedule(BaseModel):
    id:              uuid.UUID
    name:            str
    task_name:       str
    payload:         dict[str, Any]
    cron_expression: str
    queue:           str
    priority:        JobPriority
    timeout_seconds: int
    max_retries:     int
    enabled:         bool
    last_run_at:     datetime | None
    next_run_at:     datetime | None
    last_job_id:     uuid.UUID | None
    created_at:      datetime
    updated_at:      datetime

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    name:            str = Field(...,
                                 description="Unique human-readable identifier")
    task_name:       str
    payload:         dict[str, Any] = Field(default_factory=dict)
    cron_expression: str = Field(...,
                                 description='Standard 5-field cron e.g. "*/5 * * * *"')
    queue:           str = Field(default="default")
    priority:        JobPriority = Field(default=JobPriority.normal)
    timeout_seconds: int = Field(default=300, ge=1)
    max_retries:     int = Field(default=3, ge=0)
    enabled:         bool = Field(default=True)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "daily-report",
                    "task_name": "generate_report",
                    "payload": {"type": "daily"},
                    "cron_expression": "0 9 * * *",
                    "priority": "normal",
                }
            ]
        }
    }


class ScheduleResponse(BaseModel):
    id:              uuid.UUID
    name:            str
    task_name:       str
    cron_expression: str
    enabled:         bool
    last_run_at:     datetime | None
    next_run_at:     datetime | None
    last_job_id:     uuid.UUID | None
    created_at:      datetime

    class Config:
        from_attributes = True
