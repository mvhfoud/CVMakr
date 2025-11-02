"""File-system helpers for generated resumes and local assets."""

from __future__ import annotations

import shutil
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create ``path`` (and parents) if missing, returning the resolved directory."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_template(src: Path, dst: Path) -> None:
    """Copy the LaTeX template to the destination path."""

    ensure_dir(dst.parent)
    shutil.copy(src, dst)

