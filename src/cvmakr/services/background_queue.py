"""Very small in-process job queue for the Streamlit app.

The API mimics Celery/RQ just enough for future swaps, while currently running
jobs via a configurable pool of daemon threads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


@dataclass
class JobRecord:
    """Minimal metadata kept for each queued resume job."""

    status: str = "queued"  # queued -> running -> finished|failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


__all__ = [
    "JobRecord",
    "ensure_worker",
    "submit_job",
    "get_job",
    "list_jobs",
    "stop_worker",
]


_job_queue: Queue[tuple[str, dict[str, Any]]] | None = None
_job_results: Dict[str, JobRecord] = {}
_worker_threads: List[Thread] = []
_stop_event = Event()
_process_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _worker_loop() -> None:
    """Continuously pull jobs from the queue and process them."""

    assert _process_fn is not None
    assert _job_queue is not None

    while not _stop_event.is_set():
        try:
            task = _job_queue.get(timeout=0.2)
        except Empty:
            continue

        if task is None:
            _job_queue.task_done()
            break

        task_id, payload = task
        if task_id is None:
            _job_queue.task_done()
            break

        record = _job_results.get(task_id)
        if record is None:
            _job_queue.task_done()
            continue

        if isinstance(payload, dict) and "job_id" not in payload:
            payload["job_id"] = task_id

        record.status = "running"
        record.started_at = datetime.utcnow()

        try:
            record.result = _process_fn(payload)
            record.status = "finished"
        except Exception as exc:  # pragma: no cover - surfaced in UI
            record.status = "failed"
            record.error = repr(exc)
        finally:
            record.finished_at = datetime.utcnow()
            _job_queue.task_done()


def ensure_worker(
    process_fn: Callable[[dict[str, Any]], dict[str, Any]],
    concurrency: int = 2,
) -> None:
    """Start background workers (idempotent)."""

    global _worker_threads, _job_queue, _process_fn

    if concurrency < 1:
        concurrency = 1

    if _job_queue is None:
        _job_queue = Queue()

    if _process_fn is None:
        _process_fn = process_fn
    elif _process_fn is not process_fn:
        raise RuntimeError("Worker already initialised with a different process function.")
    _stop_event.clear()

    alive_threads = [thread for thread in _worker_threads if thread.is_alive()]
    _worker_threads = alive_threads

    needed = concurrency - len(_worker_threads)
    for _ in range(max(0, needed)):
        worker = Thread(target=_worker_loop, daemon=True)
        _worker_threads.append(worker)
        worker.start()


def submit_job(payload: dict[str, Any]) -> str:
    """Enqueue a new job and return its id."""

    if _job_queue is None or _process_fn is None or not _worker_threads:
        raise RuntimeError("Worker not initialised. Call ensure_worker() first.")

    task_id = uuid4().hex
    _job_results[task_id] = JobRecord()
    _job_queue.put((task_id, payload))
    return task_id


def get_job(task_id: str) -> Optional[JobRecord]:
    """Return the current job record if available."""

    return _job_results.get(task_id)


def list_jobs(limit: int = 20) -> Dict[str, JobRecord]:
    """Return the most recent job records."""

    items = list(_job_results.items())[-limit:]
    return dict(items)


def stop_worker() -> None:
    """Signal the worker to exit (mainly useful for tests)."""

    if not _worker_threads:
        return

    _stop_event.set()
    if _job_queue:
        for _ in _worker_threads:
            _job_queue.put((None, None))

    for thread in _worker_threads:
        thread.join(timeout=1)
    _worker_threads.clear()
