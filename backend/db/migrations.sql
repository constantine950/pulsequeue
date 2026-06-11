-- PulseQueue Migrations
-- Applied in order after schema.sql on new versions.
-- Each migration is idempotent (IF NOT EXISTS / IF EXISTS guards).
-- Format: -- [YYYY-MM-DD] description

-- ─────────────────────────────────────────────
-- [initial] schema.sql covers baseline — no migrations yet
-- ─────────────────────────────────────────────

-- Example future migration format:
--
-- -- [2024-07-01] add tags column to jobs
-- ALTER TABLE jobs ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
-- CREATE INDEX IF NOT EXISTS idx_jobs_tags ON jobs USING GIN (tags);