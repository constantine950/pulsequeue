# PulseQueue — Product Requirements Document

## One-Line Description

PulseQueue is a distributed background job orchestration system that queues, schedules, retries, and monitors asynchronous tasks across distributed workers.

---

## Problem Statement

Web applications frequently need to execute work that should not happen inside an HTTP request — sending emails, processing uploads, calling slow third-party APIs, generating reports, running ML inference. Doing this work synchronously means slow responses, timeouts, and cascading failures.

The solution is a **background job system**: the application enqueues a description of work, a separate worker process picks it up and executes it, and the result is stored. The application and the worker are fully decoupled.

PulseQueue is a self-hosted, production-grade implementation of this pattern.

---

## Core Concepts

### Queue

A queue is a data structure that holds job payloads waiting to be processed. Jobs enter at the back and are consumed from the front (FIFO). PulseQueue uses Redis as the queue backend because Redis list/sorted-set operations are atomic and extremely fast.

### Worker

A worker is a long-running process that loops: pull a job from the queue → execute it → record the result → repeat. Workers run independently of the API server. Multiple workers can run in parallel, each consuming different jobs concurrently.

### Async Execution

Jobs are not executed in the thread that enqueued them. The enqueueing process (API server) simply writes a payload to Redis and returns immediately. Execution happens later, in a separate process, on potentially a separate machine.

### Job Lifecycle

```
CREATED → QUEUED → RUNNING → COMPLETED
                          ↘ FAILED → RETRYING → QUEUED (retry)
                                              ↘ DEAD (max retries exceeded)
```

---

## MVP Scope

### Must Have

- Enqueue jobs via REST API with arbitrary JSON payloads
- Workers consume and execute jobs from Redis queues
- Job state persisted in PostgreSQL (queued, running, completed, failed)
- Automatic retry with configurable max attempts
- Exponential backoff between retries
- Dead letter queue for permanently failed jobs
- Delayed/scheduled job execution (run at a future time)
- Recurring cron jobs (run on a schedule)
- Priority queues (high / normal / low)
- Job cancellation for queued jobs
- Timeout enforcement on running jobs
- Worker heartbeat and liveness tracking
- Metrics API: queue depth, failure rate, average job runtime
- React dashboard: jobs, workers, metrics, failed jobs

### Out of Scope (v1)

- Job dependencies / DAG workflows
- Multi-tenant queue isolation
- Fan-out / broadcast patterns
- Job result streaming
- External webhook callbacks on completion

---

## System Actors

| Actor          | Description                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------- |
| **Producer**   | Any service or script that calls the enqueue API to submit a job                             |
| **API Server** | FastAPI app that accepts job submissions, handles cancellation, exposes metrics              |
| **Redis**      | Queue backend — stores pending job payloads in lists/sorted sets                             |
| **Worker**     | Python process that dequeues and executes jobs                                               |
| **PostgreSQL** | Persistent store for all job records, retry history, schedules, worker state                 |
| **Scheduler**  | Background thread/process that pushes delayed and cron jobs into the queue at the right time |
| **Dashboard**  | React frontend for visibility into the system                                                |

---

## Functional Requirements

### FR-1: Job Enqueueing

- `POST /jobs` accepts: `task_name`, `payload` (JSON), `queue` (default: `default`), `priority` (high/normal/low), `run_at` (optional ISO datetime), `max_retries` (default: 3), `timeout_seconds` (default: 300)
- Returns a job ID immediately
- Writes the job record to PostgreSQL with status `queued`
- Pushes the job ID into the appropriate Redis queue

### FR-2: Job Execution

- Workers pull job IDs from Redis, load the full job record from PostgreSQL
- Resolve `task_name` to a Python callable via the task registry
- Execute the callable with the job's `payload`
- Update job status to `running` with a `started_at` timestamp
- On success: status → `completed`, store result
- On failure: status → `failed`, store error traceback

### FR-3: Retry & Backoff

- Failed jobs with `attempt < max_retries` are re-queued after a delay
- Delay formula: `base_delay * (2 ^ attempt)` with optional jitter
- Each retry increments `attempt` counter and logs to the `retries` table
- Jobs exceeding `max_retries` move to `dead` status and the dead letter queue

### FR-4: Scheduled Jobs

- Jobs with `run_at` in the future are stored with status `scheduled`
- Scheduler polls every second and pushes due jobs into the Redis queue
- Cron jobs have a `cron_expression` field; scheduler computes next run time after each execution

### FR-5: Priority Queues

- Three Redis queues: `pulsequeue:high`, `pulsequeue:normal`, `pulsequeue:low`
- Workers check high before normal before low (strict priority)

### FR-6: Job Cancellation

- `DELETE /jobs/{id}` sets status to `cancelled` if job is still `queued`
- Running jobs cannot be cancelled via API (only timed out)

### FR-7: Timeout

- Workers track wall-clock time from `started_at`
- Jobs exceeding `timeout_seconds` are killed and marked `failed` with reason `timeout`
- Eligible for retry like any other failure

### FR-8: Worker Heartbeat

- Each worker writes a heartbeat timestamp to PostgreSQL every 10 seconds
- Workers not seen in 30 seconds are marked `stale`
- Any jobs that were `running` on a stale worker are re-queued

### FR-9: Metrics

- `GET /metrics` returns: queue depth per priority, total jobs by status, failure rate (last 1h), average job runtime (last 1h), active worker count

---

## Non-Functional Requirements

| Concern           | Target                                                                          |
| ----------------- | ------------------------------------------------------------------------------- |
| **Throughput**    | ≥ 500 jobs/min on a single worker process                                       |
| **Latency**       | Job picked up within 1 second of enqueue under normal load                      |
| **Durability**    | No job lost if API server crashes after enqueue (Redis + Postgres both written) |
| **Observability** | Every job state transition logged with timestamp                                |
| **Portability**   | Runs fully via Docker Compose, no managed cloud services                        |

---

## Tech Stack

| Layer     | Technology                         |
| --------- | ---------------------------------- |
| API       | Python 3.11, FastAPI, Uvicorn      |
| Queue     | Redis 7                            |
| Database  | PostgreSQL 15                      |
| Worker    | Python multiprocessing / asyncio   |
| Scheduler | APScheduler or custom polling loop |
| Frontend  | React 18, Vite, Tailwind CSS       |
| Infra     | Docker Compose                     |

---

## Data Model (Preview)

**jobs** — core job record (status, payload, timing, retry state)
**workers** — registered worker processes and heartbeat timestamps
**retries** — log of every retry attempt per job
**schedules** — cron job definitions with next_run_at

Full schema delivered on Day 3.

---

## Success Criteria

- [ ] Enqueue a job via API and watch it execute in a worker
- [ ] Simulate a failure and observe automatic retry with backoff
- [ ] Schedule a cron job and watch it repeat on interval
- [ ] Kill a worker mid-job and watch the job recover on another worker
- [ ] Open the dashboard and see live queue depth, worker status, and failure rate
