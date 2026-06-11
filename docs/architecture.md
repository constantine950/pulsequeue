# PulseQueue — Architecture

## System Overview

```
Producers ──► API Server ──► Redis Queues ──► Workers ──► Task Registry
                  │               ▲               │
                  ▼               │               ▼
             PostgreSQL       Scheduler       PostgreSQL
                  ▲                               │
                  └──────── Metrics API ◄─────────┘
                                  │
                             Dashboard (React)
```

---

## Components

### 1. Producers

Any external service, cron trigger, or script that calls `POST /jobs`. They hand off a
task name and JSON payload — they never execute the work themselves.

### 2. API Server (`backend/main.py`, `backend/api/`)

- **Framework**: FastAPI + Uvicorn
- **Responsibilities**:
  - Accept job submissions, validate payload
  - Write job record to PostgreSQL with status `queued`
  - Push job ID into the correct Redis priority queue
  - Expose `DELETE /jobs/:id` for cancellation
  - Expose `GET /metrics` for the dashboard
- **Does not** execute jobs — it only accepts and routes them

### 3. Redis Queues (`backend/core/queue/`)

- **Role**: Fast, atomic job ID buffer between API and workers
- **Structure**:
  - `pulsequeue:high` — Redis list (LPUSH / BRPOP)
  - `pulsequeue:normal` — Redis list
  - `pulsequeue:low` — Redis list
  - `pulsequeue:scheduled` — Redis sorted set (score = run_at UNIX timestamp)
- **Why Redis**: Sub-millisecond enqueue/dequeue, atomic list ops prevent double-processing,
  BRPOP gives workers efficient blocking wait with no polling loop

### 4. Workers (`backend/core/worker/`)

- **Role**: Long-running processes that consume and execute jobs
- **Loop**:
  1. BRPOP from high → normal → low (strict priority order)
  2. Load full job record from PostgreSQL
  3. Resolve `task_name` to a Python callable via task registry
  4. Execute with job's `payload`
  5. On success: update status → `completed`
  6. On failure: hand off to retry engine
- **Heartbeat**: writes a timestamp to the `workers` table every 10 seconds
- Multiple workers can run in parallel — each processes a different job

### 5. Task Registry (`backend/tasks/registry.py`)

- A Python dict mapping `task_name` strings to callables
- Workers use this to execute the right function for each job
- All task functions live in `backend/tasks/sample_tasks.py`

### 6. PostgreSQL (`backend/db/`)

- **Role**: Single source of truth for all job state
- **Tables**:
  - `jobs` — job record, status, payload, attempt count, timing
  - `workers` — registered workers + last heartbeat
  - `retries` — log of every retry attempt
  - `schedules` — cron job definitions + next_run_at
- Workers write to PostgreSQL; Redis only holds job IDs (not payloads)
- If Redis is flushed, jobs can be re-queued from PostgreSQL

### 7. Retry Engine (`backend/core/retry/`)

- On job failure: check `attempt < max_retries`
- If yes: compute delay via exponential backoff (`base * 2^attempt` + jitter),
  schedule re-enqueue after delay, log to `retries` table
- If no: move job to `dead` status, push to dead letter queue in Redis

### 8. Scheduler (`backend/core/scheduler/`)

- Runs in a background thread or separate process
- **Every second**: queries PostgreSQL for jobs with `status = scheduled` and
  `run_at <= now()` — pushes them into the appropriate Redis queue
- **Cron jobs**: after each execution, computes the next `run_at` from the
  cron expression and updates the `schedules` table

### 9. Metrics API (`backend/api/routes/metrics.py`)

- Aggregates from PostgreSQL on request:
  - Queue depth per priority (count of `queued` jobs)
  - Failure rate last 1 hour
  - Average job runtime last 1 hour
  - Active worker count (heartbeat seen in last 30s)

### 10. Dashboard (`frontend/`)

- **Stack**: React 18, Vite, Tailwind CSS
- Polls the Metrics API for live stats
- Displays job list with status badges, active workers, retry/failure UI, and charts

---

## Data Flow: Happy Path

```
1. Producer calls POST /jobs { task_name: "send_email", payload: {...} }

2. API Server:
   a. Validates request
   b. Inserts job row into PostgreSQL  (status: queued)
   c. LPUSHes job_id into Redis pulsequeue:normal

3. Worker (blocking on BRPOP):
   a. Pops job_id from Redis
   b. Loads job row from PostgreSQL
   c. Resolves task_name → send_email() via registry
   d. Updates status → running, sets started_at
   e. Calls send_email(payload)
   f. Updates status → completed, sets completed_at

4. Dashboard polls GET /metrics → shows 1 completed job
```

## Data Flow: Retry Path

```
3e. send_email() raises an exception

3f. Worker catches error:
    - increments attempt counter
    - logs to retries table
    - if attempt < max_retries:
        computes backoff delay (e.g. 4s, 8s, 16s)
        re-pushes job_id into Redis after delay
        status → queued
    - if attempt >= max_retries:
        status → dead
        pushes into pulsequeue:dead
```

## Data Flow: Scheduled Job

```
1. Producer calls POST /jobs { ..., run_at: "2024-06-15T14:00:00Z" }

2. API Server:
   a. Inserts job with status: scheduled (NOT pushed to Redis yet)

3. Scheduler (every 1s):
   a. SELECT * FROM jobs WHERE status='scheduled' AND run_at <= now()
   b. For each due job: LPUSH into Redis + update status → queued

4. Worker picks up and executes normally
```

---

## Key Design Decisions

| Decision                   | Choice                            | Reason                                                            |
| -------------------------- | --------------------------------- | ----------------------------------------------------------------- |
| Queue backend              | Redis lists + sorted sets         | Atomic, fast, BRPOP blocks without polling                        |
| Job payload storage        | PostgreSQL only                   | Redis holds IDs; DB is source of truth                            |
| Worker communication       | Redis → Postgres read             | No direct worker-to-worker or worker-to-API calls                 |
| Priority                   | 3 separate Redis lists            | Workers poll high before normal before low — strict, not weighted |
| Retry delay                | Exponential backoff + jitter      | Prevents thundering herd on transient failures                    |
| Heartbeat failure recovery | Scheduler re-queues orphaned jobs | Workers dying mid-job don't lose work                             |

---

## File Map

```
backend/
├── main.py                     entry point, mounts routers
├── config.py                   env vars (DB URL, Redis URL, etc.)
├── api/
│   ├── routes/jobs.py          POST /jobs, DELETE /jobs/:id, GET /jobs
│   ├── routes/workers.py       GET /workers
│   ├── routes/schedules.py     POST /schedules, cron management
│   └── routes/metrics.py       GET /metrics
├── core/
│   ├── queue/
│   │   ├── redis_client.py     Redis connection singleton
│   │   ├── enqueue.py          push job ID into correct queue
│   │   ├── dequeue.py          BRPOP loop for workers
│   │   ├── priority.py         queue name resolution
│   │   └── dead_letter.py      push/read dead queue
│   ├── worker/
│   │   ├── worker.py           main worker loop
│   │   ├── executor.py         resolve + call task function
│   │   ├── heartbeat.py        10s heartbeat writes
│   │   └── timeout.py          wall-clock timeout enforcement
│   ├── scheduler/
│   │   ├── scheduler.py        polling loop for due jobs
│   │   └── cron.py             cron expression → next_run_at
│   └── retry/
│       ├── retry.py            retry decision + re-enqueue
│       └── backoff.py          exponential backoff calculation
├── models/
│   ├── job.py                  Job dataclass / Pydantic model
│   ├── worker.py               Worker model
│   ├── retry.py                RetryAttempt model
│   └── schedule.py             Schedule model
├── db/
│   ├── schema.sql              table definitions
│   ├── migrations.sql          schema changes
│   └── connection.py           asyncpg pool setup
├── metrics/
│   ├── collector.py            query aggregates from DB
│   └── aggregator.py           compute rates + averages
└── tasks/
    ├── registry.py             { "task_name": callable } map
    └── sample_tasks.py         demo task functions
```
