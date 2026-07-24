import { useState } from "react";
import { jobsApi } from "../../api/jobs";

const SAMPLE_TASKS = [
  {
    name: "send_email",
    payload: '{\n  "to": "user@example.com",\n  "subject": "Hello"\n}',
  },
  {
    name: "generate_report",
    payload: '{\n  "report_id": 1,\n  "type": "daily"\n}',
  },
  {
    name: "resize_image",
    payload: '{\n  "url": "https://example.com/img.jpg",\n  "width": 800\n}',
  },
  {
    name: "send_webhook",
    payload:
      '{\n  "url": "https://example.com/hook",\n  "event": "user.created"\n}',
  },
  { name: "noop", payload: '{\n  "msg": "hello"\n}' },
  { name: "always_fail", payload: "{}" },
  { name: "slow_task", payload: '{\n  "duration": 5\n}' },
];

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export function EnqueueModal({ onClose, onSuccess }: Props) {
  const [taskName, setTaskName] = useState("send_email");
  const [customTask, setCustomTask] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [payload, setPayload] = useState(SAMPLE_TASKS[0].payload);
  const [priority, setPriority] = useState("normal");
  const [maxRetries, setMaxRetries] = useState(3);
  const [timeoutSec, setTimeoutSec] = useState(300);
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [runAtLocal, setRunAtLocal] = useState("");
  const [payloadError, setPayloadError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function handleTaskSelect(name: string) {
    setTaskName(name);
    setUseCustom(false);
    const sample = SAMPLE_TASKS.find((t) => t.name === name);
    if (sample) setPayload(sample.payload);
    setPayloadError("");
  }

  function validatePayload() {
    try {
      JSON.parse(payload);
      setPayloadError("");
      return true;
    } catch {
      setPayloadError("Invalid JSON");
      return false;
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validatePayload()) return;

    // Only use run_at if the user explicitly enabled scheduling and filled it in
    let run_at: string | undefined;
    if (scheduleEnabled && runAtLocal) {
      run_at = new Date(runAtLocal).toISOString();
    }

    setSubmitting(true);
    setError("");
    try {
      await jobsApi.create({
        task_name: useCustom ? customTask.trim() : taskName,
        payload: JSON.parse(payload),
        priority,
        max_retries: maxRetries,
        timeout_seconds: timeoutSec,
        run_at,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to enqueue job");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-panel border border-border rounded-xl w-full max-w-lg mx-4 shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-semibold text-gray-100">Enqueue Job</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-gray-300 text-xl leading-none"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Task picker */}
          <div>
            <label className="text-xs text-muted font-mono block mb-1.5">
              task
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {SAMPLE_TASKS.map((t) => (
                <button
                  key={t.name}
                  type="button"
                  onClick={() => handleTaskSelect(t.name)}
                  className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                    !useCustom && taskName === t.name
                      ? "bg-primary text-white"
                      : "bg-surface border border-border text-muted hover:text-gray-300"
                  }`}
                >
                  {t.name}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setUseCustom(true)}
                className={`px-2 py-1 rounded text-xs font-mono transition-colors ${
                  useCustom
                    ? "bg-primary text-white"
                    : "bg-surface border border-border text-muted hover:text-gray-300"
                }`}
              >
                custom…
              </button>
            </div>
            {useCustom && (
              <input
                type="text"
                value={customTask}
                onChange={(e) => setCustomTask(e.target.value)}
                placeholder="my_task_name"
                required
                className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
              />
            )}
          </div>

          {/* Payload */}
          <div>
            <label className="text-xs text-muted font-mono block mb-1.5">
              payload (JSON)
            </label>
            <textarea
              value={payload}
              onChange={(e) => {
                setPayload(e.target.value);
                setPayloadError("");
              }}
              onBlur={validatePayload}
              rows={4}
              className={`w-full bg-surface border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none resize-none ${
                payloadError
                  ? "border-danger"
                  : "border-border focus:border-primary"
              }`}
            />
            {payloadError && (
              <p className="text-xs text-danger font-mono mt-1">
                {payloadError}
              </p>
            )}
          </div>

          {/* Priority / retries / timeout */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-muted font-mono block mb-1.5">
                priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full bg-surface border border-border rounded px-2 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
              >
                <option value="high">high</option>
                <option value="normal">normal</option>
                <option value="low">low</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted font-mono block mb-1.5">
                max retries
              </label>
              <input
                type="number"
                min={0}
                max={20}
                value={maxRetries}
                onChange={(e) => setMaxRetries(Number(e.target.value))}
                className="w-full bg-surface border border-border rounded px-2 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="text-xs text-muted font-mono block mb-1.5">
                timeout (s)
              </label>
              <input
                type="number"
                min={1}
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(Number(e.target.value))}
                className="w-full bg-surface border border-border rounded px-2 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* Schedule toggle — keeps datetime-local out of the form unless explicitly enabled */}
          <div>
            <label className="flex items-center gap-2 text-xs text-muted font-mono cursor-pointer select-none mb-2">
              <input
                type="checkbox"
                checked={scheduleEnabled}
                onChange={(e) => {
                  setScheduleEnabled(e.target.checked);
                  if (!e.target.checked) setRunAtLocal("");
                }}
                className="accent-primary"
              />
              schedule for later (optional)
            </label>
            {scheduleEnabled && (
              <input
                type="datetime-local"
                value={runAtLocal}
                onChange={(e) => setRunAtLocal(e.target.value)}
                required={scheduleEnabled}
                className="w-full bg-surface border border-border rounded px-3 py-2 text-sm font-mono text-gray-200 focus:outline-none focus:border-primary"
              />
            )}
          </div>

          {error && (
            <p className="text-xs text-danger font-mono bg-danger/10 border border-danger/20 rounded px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-mono text-muted hover:text-gray-300 transition-colors"
            >
              cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded bg-primary text-white text-sm font-mono hover:bg-primary/80 disabled:opacity-50 transition-colors"
            >
              {submitting ? "enqueueing…" : "enqueue"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
