"""
config.py — application settings loaded from environment variables.

All settings have defaults so the app starts in development without
a .env file. Production deployments override via environment or Docker.

Usage anywhere in the codebase:
    from backend.config import settings
    print(settings.database_url)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    app_name: str = "PulseQueue"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── PostgreSQL ───────────────────────────────────────────────────
    # asyncpg DSN — postgres:// scheme (not postgresql+asyncpg)
    database_url: str = "postgresql://postgres:postgres@localhost:5432/pulsequeue"

    # Connection pool sizing
    db_min_connections: int = 2
    db_max_connections: int = 10

    # ── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # BRPOP timeout in seconds (0 = block forever, >0 = wake up to check shutdown)
    redis_brpop_timeout: int = 5

    # ── Queue names ──────────────────────────────────────────────────
    queue_high: str = "pulsequeue:high"
    queue_normal: str = "pulsequeue:normal"
    queue_low: str = "pulsequeue:low"
    queue_scheduled: str = "pulsequeue:scheduled"
    queue_dead: str = "pulsequeue:dead"

    # ── Worker ───────────────────────────────────────────────────────
    worker_heartbeat_interval: int = 10        # seconds between heartbeat writes
    # seconds before a worker is considered stale
    worker_stale_threshold: int = 30
    # jobs processed concurrently per worker process
    worker_default_concurrency: int = 1

    # ── Retry / backoff ──────────────────────────────────────────────
    retry_base_delay: int = 4                  # seconds — delay for attempt 1
    retry_max_delay: int = 3600                # cap backoff at 1 hour
    retry_jitter: bool = True                  # add ±25% random jitter to backoff

    # ── Scheduler ────────────────────────────────────────────────────
    scheduler_poll_interval: float = 1.0      # seconds between due-job polls

    # ── Jobs ─────────────────────────────────────────────────────────
    job_default_timeout: int = 300             # seconds
    job_default_max_retries: int = 3


settings = Settings()
