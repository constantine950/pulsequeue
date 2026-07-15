from __future__ import annotations

import asyncpg
import redis.asyncio as aioredis
import structlog

from backend.config import settings

log = structlog.get_logger(__name__)

# Module-level references — set during app lifespan startup
db_pool: asyncpg.Pool | None = None
redis_client: aioredis.Redis | None = None


# PostgreSQL

async def create_db_pool() -> asyncpg.Pool:
    """Create and return the asyncpg connection pool."""
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
        command_timeout=60,
    )
    log.info("db.pool.created", min=settings.db_min_connections,
             max=settings.db_max_connections)
    return pool


async def close_db_pool(pool: asyncpg.Pool) -> None:
    await pool.close()
    log.info("db.pool.closed")


async def get_db_pool() -> asyncpg.Pool:
    if db_pool is None:
        raise RuntimeError(
            "Database pool not initialised. Did the app lifespan run?")
    return db_pool


# Redis

async def create_redis_client() -> aioredis.Redis:
    """Create and return a Redis client with connection pool."""
    client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    # Verify connectivity immediately
    await client.ping()
    log.info("redis.connected", url=settings.redis_url)
    return client


async def close_redis_client(client: aioredis.Redis) -> None:
    await client.aclose()
    log.info("redis.disconnected")


async def get_redis() -> aioredis.Redis:
    if redis_client is None:
        raise RuntimeError(
            "Redis client not initialised. Did the app lifespan run?")
    return redis_client
