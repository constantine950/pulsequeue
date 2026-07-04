"""
models/worker.py — Worker entity and related schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class WorkerStatus(str, Enum):
    active = "active"
    stale = "stale"
    stopped = "stopped"


class Worker(BaseModel):
    id:                 uuid.UUID
    hostname:           str
    pid:                int
    status:             WorkerStatus
    queues:             list[str]
    concurrency:        int
    last_heartbeat_at:  datetime
    jobs_processed:     int
    jobs_failed:        int
    started_at:         datetime
    stopped_at:         datetime | None
    updated_at:         datetime

    class Config:
        from_attributes = True

    @property
    def is_alive(self) -> bool:
        return self.status == WorkerStatus.active


class WorkerResponse(BaseModel):
    id:                uuid.UUID
    hostname:          str
    pid:               int
    status:            WorkerStatus
    queues:            list[str]
    concurrency:       int
    last_heartbeat_at: datetime
    jobs_processed:    int
    jobs_failed:       int
    started_at:        datetime

    class Config:
        from_attributes = True
