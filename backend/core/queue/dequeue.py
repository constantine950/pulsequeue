from __future__ import annotations

import redis.asyncio as aioredis
import structlog

from backend.config import settings
from backend.core.queue.priority import POLL_ORDER, priority_label

log = structlog.get_logger(__name__)


async def dequeue(redis: aioredis.Redis) -> str | None:
    result = await redis.brpop(
        POLL_ORDER,
        timeout=settings.redis_brpop_timeout,
    )

    if result is None:
        return None

    queue_key, job_id = result
    log.debug(
        "job.dequeued",
        job_id=job_id,
        queue=queue_key,
        priority=priority_label(queue_key),
    )
    return job_id
