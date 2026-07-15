-- PulseQueue Database Schema

-- Extensions

CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- Enums

CREATE TYPE job_status AS ENUM (
    'queued',
    'scheduled',
    'running',
    'completed',
    'failed',
    'retrying',
    'dead',
    'cancelled'
);

CREATE TYPE job_priority AS ENUM (
    'high',
    'normal',
    'low'
);

CREATE TYPE worker_status AS ENUM (
    'active',
    'stale',
    'stopped'
);


-- Table: jobs
-- Core job record. Every job that enters the system
-- gets exactly one row here for its entire lifetime.

CREATE TABLE jobs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name           VARCHAR(255)    NOT NULL,
    payload             JSONB           NOT NULL DEFAULT '{}',
    status              job_status      NOT NULL DEFAULT 'queued',
    priority            job_priority    NOT NULL DEFAULT 'normal',
    queue               VARCHAR(100)    NOT NULL DEFAULT 'default',

    -- Scheduling
    run_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    scheduled_for       TIMESTAMPTZ     NULL,       -- set when status = 'scheduled'

    -- Execution tracking
    worker_id           UUID            NULL,       -- which worker is/was running this
    started_at          TIMESTAMPTZ     NULL,
    completed_at        TIMESTAMPTZ     NULL,
    timeout_seconds     INTEGER         NOT NULL DEFAULT 300,

    -- Retry config
    max_retries         INTEGER         NOT NULL DEFAULT 3,
    attempt             INTEGER         NOT NULL DEFAULT 0,

    -- Result / error
    result              JSONB           NULL,
    error_message       TEXT            NULL,
    error_traceback     TEXT            NULL,

    -- Metadata
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes for the most common worker and API queries
CREATE INDEX idx_jobs_status          ON jobs (status);
CREATE INDEX idx_jobs_status_priority ON jobs (status, priority);
CREATE INDEX idx_jobs_worker_id       ON jobs (worker_id) WHERE worker_id IS NOT NULL;
CREATE INDEX idx_jobs_run_at          ON jobs (run_at)    WHERE status IN ('queued', 'scheduled');
CREATE INDEX idx_jobs_scheduled_for   ON jobs (scheduled_for) WHERE status = 'scheduled';
CREATE INDEX idx_jobs_task_name       ON jobs (task_name);
CREATE INDEX idx_jobs_created_at      ON jobs (created_at DESC);

-- Auto-update updated_at on every write
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- Table: workers
-- One row per worker process. Heartbeat updated
-- every 10 seconds while the worker is alive.

CREATE TABLE workers (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname            VARCHAR(255)    NOT NULL,
    pid                 INTEGER         NOT NULL,
    status              worker_status   NOT NULL DEFAULT 'active',
    queues              TEXT[]          NOT NULL DEFAULT ARRAY['default'],  -- which queues this worker pulls from
    concurrency         INTEGER         NOT NULL DEFAULT 1,

    -- Heartbeat
    last_heartbeat_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- Stats (cumulative, reset on restart)
    jobs_processed      INTEGER         NOT NULL DEFAULT 0,
    jobs_failed         INTEGER         NOT NULL DEFAULT 0,

    started_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    stopped_at          TIMESTAMPTZ     NULL
);

CREATE INDEX idx_workers_status          ON workers (status);
CREATE INDEX idx_workers_last_heartbeat  ON workers (last_heartbeat_at) WHERE status = 'active';

CREATE TRIGGER trg_workers_updated_at
    BEFORE UPDATE ON workers
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- workers table doesn't have updated_at but we use the trigger pattern for future-proofing
-- Add the column now so the trigger doesn't error
ALTER TABLE workers ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();


-- Table: retries
-- Append-only log. One row per retry attempt.
-- Never updated — only inserted.

CREATE TABLE retries (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              UUID            NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    attempt             INTEGER         NOT NULL,   -- which attempt number this row records
    error_message       TEXT            NOT NULL,
    error_traceback     TEXT            NULL,
    retried_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    next_retry_at       TIMESTAMPTZ     NULL,       -- NULL means no more retries (dead)
    backoff_seconds     INTEGER         NOT NULL DEFAULT 0
);

CREATE INDEX idx_retries_job_id     ON retries (job_id);
CREATE INDEX idx_retries_retried_at ON retries (retried_at DESC);


-- Table: schedules
-- Cron job definitions. Scheduler reads this table
-- every second and enqueues due jobs.

CREATE TABLE schedules (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255)    NOT NULL UNIQUE,  -- human-readable identifier
    task_name           VARCHAR(255)    NOT NULL,
    payload             JSONB           NOT NULL DEFAULT '{}',
    cron_expression     VARCHAR(100)    NOT NULL,         -- standard 5-field cron: "*/5 * * * *"
    queue               VARCHAR(100)    NOT NULL DEFAULT 'default',
    priority            job_priority    NOT NULL DEFAULT 'normal',
    timeout_seconds     INTEGER         NOT NULL DEFAULT 300,
    max_retries         INTEGER         NOT NULL DEFAULT 3,

    -- State
    enabled             BOOLEAN         NOT NULL DEFAULT TRUE,
    last_run_at         TIMESTAMPTZ     NULL,
    next_run_at         TIMESTAMPTZ     NULL,   -- computed by scheduler after each execution
    last_job_id         UUID            NULL REFERENCES jobs(id) ON DELETE SET NULL,

    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_schedules_next_run_at ON schedules (next_run_at) WHERE enabled = TRUE;
CREATE INDEX idx_schedules_enabled     ON schedules (enabled);

CREATE TRIGGER trg_schedules_updated_at
    BEFORE UPDATE ON schedules
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- View: job_stats
-- Convenience view used by the metrics API.
-- Avoids repeating this aggregation in Python.

CREATE VIEW job_stats AS
SELECT
    status,
    priority,
    COUNT(*)                                            AS count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
        FILTER (WHERE completed_at IS NOT NULL
            AND started_at IS NOT NULL)                 AS avg_duration_seconds,
    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') AS count_last_hour
FROM jobs
GROUP BY status, priority;


-- View: active_workers
-- Workers seen in the last 30 seconds.

CREATE VIEW active_workers AS
SELECT *
FROM workers
WHERE status = 'active'
  AND last_heartbeat_at >= NOW() - INTERVAL '30 seconds';


-- Seed: default queue placeholder (optional)
-- Remove before production use.

-- Example cron schedule (disabled by default)
INSERT INTO schedules (name, task_name, cron_expression, payload, enabled)
VALUES (
    'example-heartbeat',
    'noop',
    '* * * * *',
    '{"msg": "still alive"}',
    FALSE
);