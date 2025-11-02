"""Utilities for persisting per-step job metrics to disk."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Iterable, Mapping

LOG_DIR = Path("data") / "logs"
LOG_FILE = LOG_DIR / "resume_job_metrics.csv"

_LOCK = Lock()
_FIELDNAMES = [
    "timestamp_utc",
    "job_id",
    "step",
    "duration_seconds",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
]


def log_job_metrics(job_id: str | None, metrics: Iterable[Mapping[str, float | int | str]]) -> None:
    """Append metric rows for a given job to the CSV log."""

    if job_id is None:
        job_id = "unknown"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int]] = []
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    for entry in metrics:
        duration = float(entry.get("duration_seconds", 0.0) or 0.0)
        row = {
            "timestamp_utc": timestamp,
            "job_id": job_id,
            "step": str(entry.get("step", "unknown")),
            "duration_seconds": f"{duration:.4f}",
            "prompt_tokens": int(entry.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(entry.get("completion_tokens", 0) or 0),
            "total_tokens": int(entry.get("total_tokens", 0) or 0),
        }
        rows.append(row)

    with _LOCK:
        write_header = not LOG_FILE.exists()
        with LOG_FILE.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=_FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerows(rows)
