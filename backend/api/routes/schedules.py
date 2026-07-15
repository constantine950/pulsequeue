from __future__ import annotations

import uuid

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

from backend.db.connection import get_db_pool
from backend.models.schedule import ScheduleCreate, ScheduleResponse

log = structlog.get_logger(__name__)
router = APIRouter()


# POST /schedules

@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    schedule_in: ScheduleCreate,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> ScheduleResponse:
    import json
    from backend.core.scheduler.cron import next_run

    next_run_at = next_run(schedule_in.cron_expression)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO schedules (
                id, name, task_name, payload, cron_expression,
                queue, priority, timeout_seconds, max_retries,
                enabled, next_run_at, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4::jsonb, $5,
                $6, $7, $8, $9,
                $10, $11, NOW(), NOW()
            )
            RETURNING *
            """,
            uuid.uuid4(),
            schedule_in.name,
            schedule_in.task_name,
            json.dumps(schedule_in.payload),
            schedule_in.cron_expression,
            schedule_in.queue,
            schedule_in.priority.value,
            schedule_in.timeout_seconds,
            schedule_in.max_retries,
            schedule_in.enabled,
            next_run_at,
        )

    log.info("schedule.created", name=schedule_in.name,
             cron=schedule_in.cron_expression)
    return ScheduleResponse(**dict(row))


# GET /schedules

@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> list[ScheduleResponse]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM schedules ORDER BY created_at DESC"
        )
    return [ScheduleResponse(**dict(r)) for r in rows]


# GET /schedules/{id}

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: uuid.UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> ScheduleResponse:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM schedules WHERE id = $1", schedule_id
        )
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Schedule {schedule_id} not found")
    return ScheduleResponse(**dict(row))


# PATCH /schedules/{id}

class SchedulePatch(BaseModel):
    enabled: bool


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: uuid.UUID,
    patch: SchedulePatch,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> ScheduleResponse:
    """Enable or disable a schedule without deleting it."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE schedules
            SET enabled    = $1,
                updated_at = NOW()
            WHERE id = $2
            RETURNING *
            """,
            patch.enabled, schedule_id,
        )
    if not row:
        raise HTTPException(
            status_code=404, detail=f"Schedule {schedule_id} not found")
    log.info("schedule.toggled", schedule_id=str(
        schedule_id), enabled=patch.enabled)
    return ScheduleResponse(**dict(row))


# DELETE /schedules/{id}

@router.delete("/{schedule_id}", status_code=200)
async def delete_schedule(
    schedule_id: uuid.UUID,
    pool: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM schedules WHERE id = $1", schedule_id
        )
    if result == "DELETE 0":
        raise HTTPException(
            status_code=404, detail=f"Schedule {schedule_id} not found")
    log.info("schedule.deleted", schedule_id=str(schedule_id))
    return {"deleted": str(schedule_id)}
