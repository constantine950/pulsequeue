import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def api(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}


def post_job(task_name, payload=None, priority="normal", max_retries=3, timeout=300):
    return api("POST", "/jobs", {
        "task_name": task_name,
        "payload": payload or {},
        "priority": priority,
        "max_retries": max_retries,
        "timeout_seconds": timeout,
    })


def get_job(job_id):
    return api("GET", f"/jobs/{job_id}")


def wait_for_terminal(job_id, timeout_s=60, poll=1.0):
    """Poll until job reaches a terminal state."""
    terminal = {"completed", "failed", "dead", "cancelled"}
    elapsed = 0
    while elapsed < timeout_s:
        job = get_job(job_id)
        status = job.get("status", "")
        if status in terminal:
            return job
        time.sleep(poll)
        elapsed += poll
    return get_job(job_id)


def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


# ── Scenarios ─────────────────────────────────────────────────────────────────

def scenario_retry():
    section("SCENARIO: Retry with backoff")
    print("Enqueueing always_fail with max_retries=2...")
    job = post_job("always_fail", max_retries=2)
    job_id = job["id"]
    print(f"  Job ID: {job_id}")
    print("  Waiting for dead status (attempt 1 → backoff → attempt 2 → backoff → dead)...")
    final = wait_for_terminal(job_id, timeout_s=60)
    print(f"  Final status : {final['status']}")
    print(f"  Attempts     : {final['attempt']}")
    print(f"  Error        : {final['error_message']}")

    retries = api("GET", f"/jobs/{job_id}/retries")
    print(f"  Retry log    : {len(retries)} entries")
    for r in retries:
        print(
            f"    attempt {r['attempt']} → backoff {r['backoff_seconds']}s → next_retry_at: {r['next_retry_at']}")


def scenario_dead():
    section("SCENARIO: Exhaust retries → dead letter queue")
    print("Enqueueing always_fail with max_retries=1...")
    job = post_job("always_fail", max_retries=1)
    job_id = job["id"]
    final = wait_for_terminal(job_id, timeout_s=30)
    print(f"  Status: {final['status']} (expected: dead)")

    dead = api("GET", "/jobs/dead")
    matching = [j for j in dead.get("items", []) if j["id"] == job_id]
    print(f"  Found in DLQ: {'YES' if matching else 'NO'}")

    print("  Re-queueing from DLQ...")
    requeued = api("POST", f"/jobs/{job_id}/requeue")
    print(
        f"  Status after requeue: {requeued.get('status')} (expected: queued)")
    final2 = wait_for_terminal(job_id, timeout_s=30)
    print(f"  Final status after requeue: {final2['status']}")


def scenario_cancel():
    section("SCENARIO: Cancel a queued job")

    # Enqueue a slow job so we can cancel it before it runs
    # Use always_fail to be safe — even if worker grabs it first, it just fails
    print("Enqueueing a job and immediately cancelling...")

    # Stop the queue from processing by enqueueing to low priority
    job = post_job("slow_task", {"duration": 0.1},
                   priority="low", max_retries=0)
    job_id = job["id"]
    print(f"  Job ID: {job_id}")

    # Try to cancel — may already be running depending on timing
    result = api("DELETE", f"/jobs/{job_id}")
    if "error" in result:
        print(f"  Cancel result: already picked up (status conflict — OK)")
    else:
        print(f"  Cancelled: {result}")

    final = get_job(job_id)
    print(f"  Final status: {final['status']}")


def scenario_priority():
    section("SCENARIO: Priority ordering")
    print("Enqueueing low x3, normal x2, high x2 in that order...")
    ids = []

    for i in range(3):
        j = post_job("noop", {"msg": f"low-{i+1}"}, priority="low")
        ids.append(("low", j["id"]))

    for i in range(2):
        j = post_job("noop", {"msg": f"normal-{i+1}"}, priority="normal")
        ids.append(("normal", j["id"]))

    for i in range(2):
        j = post_job("noop", {"msg": f"high-{i+1}"}, priority="high")
        ids.append(("high", j["id"]))

    print(f"  Enqueued {len(ids)} jobs. Waiting for completion...")
    time.sleep(5)

    print("\n  Completion order (by completed_at):")
    results = []
    for priority, job_id in ids:
        j = get_job(job_id)
        results.append(
            (j.get("completed_at", "pending"), priority, job_id[:8]))

    for completed_at, priority, short_id in sorted(results):
        print(f"    {completed_at}  [{priority:6}]  {short_id}...")


def scenario_mixed():
    section("SCENARIO: Mixed load")
    print("Enqueueing 10 mixed jobs...")
    tasks = [
        ("send_email",     {"to": "a@test.com"},  "high"),
        ("noop",           {"msg": "quick"},       "normal"),
        ("always_fail",    {},                     "normal"),
        ("generate_report", {"report_id": 99},      "low"),
        ("send_email",     {"to": "b@test.com"},   "normal"),
        ("noop",           {"msg": "fast"},         "high"),
        ("always_fail",    {},                     "low"),
        ("send_webhook",   {"url": "http://x.com"}, "normal"),
        ("noop",           {"msg": "bg"},           "low"),
        ("send_email",     {"to": "c@test.com"},   "high"),
    ]

    job_ids = []
    for task, payload, priority in tasks:
        j = post_job(task, payload, priority=priority, max_retries=1)
        print(f"  [{priority:6}] {task:20} → {j['id'][:8]}...")
        job_ids.append(j["id"])

    print(f"\n  Waiting 15s for jobs to process...")
    time.sleep(15)

    statuses = {}
    for job_id in job_ids:
        j = get_job(job_id)
        s = j.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1

    print("\n  Results:")
    for status, count in sorted(statuses.items()):
        print(f"    {status:12} : {count}")


# ── Main ──────────────────────────────────────────────────────────────────────

SCENARIOS = {
    "retry":    scenario_retry,
    "dead":     scenario_dead,
    "cancel":   scenario_cancel,
    "priority": scenario_priority,
    "mixed":    scenario_mixed,
}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("PulseQueue Failure Simulation")
    print(f"API: {BASE_URL}")

    # Health check
    health = api("GET", "/health")
    if health.get("status") != "ok":
        print(f"ERROR: API not reachable at {BASE_URL}")
        sys.exit(1)
    print(f"Status: {health['status']} (v{health['version']})\n")

    if arg == "all":
        for name, fn in SCENARIOS.items():
            fn()
    elif arg in SCENARIOS:
        SCENARIOS[arg]()
    else:
        print(
            f"Unknown scenario '{arg}'. Choose from: {', '.join(SCENARIOS)} or 'all'")
        sys.exit(1)

    print("\n\nSimulation complete.")


if __name__ == "__main__":
    main()
