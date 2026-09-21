"""Logging setup with an in-memory ring buffer for the web debug console.

Previously ``sys.stdout``/``sys.stderr`` were replaced by a ``StringIO``
subclass.  That captured output, but the ``StringIO`` also kept *every byte
ever printed* in memory (unbounded growth), and swallowed uvicorn's own
output.  Here we use the standard ``logging`` module:

- ``RingBufferHandler`` keeps the last N formatted lines (bounded memory).
- The same handler also copies lines into the *current job's* log if a job
  is running in this thread, so the UI can show per-action progress.
- Real stderr keeps receiving logs, so ``docker logs`` still works.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Callable, Iterable

DEFAULT_MAXLEN = 1000

# Set by ``jobs.py`` to a callable returning the current job's sink (a list)
# for the calling thread, or ``None`` if no job is running there.
_job_sink_provider: Callable[[], list[str] | None] | None = None


def set_job_sink_provider(provider: Callable[[], list[str] | None] | None) -> None:
    global _job_sink_provider
    _job_sink_provider = provider


class RingBufferHandler(logging.Handler):
    def __init__(self, maxlen: int = DEFAULT_MAXLEN) -> None:
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=maxlen)
        self.lock_ = threading.Lock()
        self.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # pragma: no cover
            self.handleError(record)
            return
        with self.lock_:
            for part in line.splitlines() or [line]:
                self.buffer.append(part)
        sink = _job_sink_provider() if _job_sink_provider else None
        if sink is not None:
            sink.extend(line.splitlines() or [line])

    def get_lines(self) -> list[str]:
        with self.lock_:
            return list(self.buffer)

    def clear(self) -> None:
        with self.lock_:
            self.buffer.clear()


ring_handler = RingBufferHandler()

# Third-party loggers that are noisy at INFO but useful at WARNING.
_QUIET_LOGGERS: Iterable[tuple[str, int]] = (
    ("discord", logging.WARNING),
    ("googleapiclient.discovery_cache", logging.ERROR),
    ("urllib3", logging.WARNING),
    ("httpx", logging.WARNING),
    ("httpcore", logging.WARNING),
    ("uvicorn.access", logging.WARNING),
)

_configured = False


def setup_logging(level: int = logging.INFO) -> RingBufferHandler:
    """Idempotent: attach the ring buffer + a stderr handler to the root logger."""
    global _configured
    if _configured:
        return ring_handler
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(ring_handler)
    if not any(isinstance(h, logging.StreamHandler) and h is not ring_handler for h in root.handlers):
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(stream)
    for name, lvl in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(lvl)
    _configured = True
    return ring_handler
