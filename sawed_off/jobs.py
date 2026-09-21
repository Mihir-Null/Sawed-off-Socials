"""Background job runner.

Posting to Instagram can take minutes (media processing) and Discord needs a
websocket session.  Running those inside the HTTP request handler froze the
whole server (the event loop was blocked, so even the log endpoint stalled)
and hit reverse-proxy timeouts.

Now ``POST /api/actions/{name}`` starts a *job* in a worker thread and
returns immediately with an id; the UI polls ``GET /api/jobs/{id}`` for
status and the job's own log lines.  Only one job runs at a time - these
actions are not safe to interleave (two Discord clients, double posts).
"""

from __future__ import annotations

import logging
import threading
import traceback
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from . import logbuffer

log = logging.getLogger(__name__)

MAX_KEPT_JOBS = 25
MAX_JOB_LOG_LINES = 2000

_thread_local = threading.local()


def _current_sink() -> list[str] | None:
    job = getattr(_thread_local, "job", None)
    if job is None:
        return None
    if len(job.log) >= MAX_JOB_LOG_LINES:
        return None
    return job.log


logbuffer.set_job_sink_provider(_current_sink)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    action: str
    status: str = "queued"  # queued | running | succeeded | failed
    created_at: str = field(default_factory=_now)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: Any = None
    log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "result": self.result,
            "log": list(self.log),
            "done": self.status in ("succeeded", "failed"),
        }


class JobAlreadyRunning(RuntimeError):
    pass


class JobManager:
    def __init__(self) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._running: Job | None = None

    @property
    def running(self) -> Job | None:
        return self._running

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(reversed(self._jobs.values()))

    def start(self, action: str, fn: Callable[[], Any]) -> Job:
        """Run ``fn`` in a daemon thread. Raises ``JobAlreadyRunning`` if busy."""
        with self._lock:
            if self._running is not None and self._running.status == "running":
                raise JobAlreadyRunning(
                    f"'{self._running.action}' is still running (job {self._running.id}). "
                    "Wait for it to finish before starting another action."
                )
            job = Job(id=uuid.uuid4().hex[:12], action=action)
            self._jobs[job.id] = job
            while len(self._jobs) > MAX_KEPT_JOBS:
                self._jobs.popitem(last=False)
            self._running = job
            job.status = "running"
            job.started_at = _now()

        thread = threading.Thread(target=self._run, args=(job, fn), name=f"job-{job.id}", daemon=True)
        thread.start()
        return job

    def _run(self, job: Job, fn: Callable[[], Any]) -> None:
        _thread_local.job = job
        try:
            log.info("[Job %s] Starting '%s'", job.id, job.action)
            job.result = fn()
            job.status = "succeeded"
            log.info("[Job %s] '%s' finished successfully", job.id, job.action)
        except Exception as exc:  # noqa: BLE001 - we want every failure reported to the UI
            job.status = "failed"
            job.error = str(exc) or exc.__class__.__name__
            # "all" attaches per-step results to its exception so the UI can
            # show which steps worked even though the job as a whole failed.
            job.result = getattr(exc, "partial_result", None)
            log.error("[Job %s] '%s' FAILED: %s", job.id, job.action, job.error)
            log.debug("Traceback:\n%s", traceback.format_exc())
        finally:
            job.finished_at = _now()
            _thread_local.job = None
            with self._lock:
                if self._running is job:
                    self._running = None


manager = JobManager()
