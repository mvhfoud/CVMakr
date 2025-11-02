"""Helpers for reading and mutating LaTeX templates."""

from __future__ import annotations

import re
from pathlib import Path


_PLACEHOLDER_PATTERN = re.compile(r"\?\?\*(\d+)\*\?\?")


def replace_placeholder_in_file_inplace(file_path: Path, target_int: int, replacement: str) -> None:
    """
    Replace tokens of the form ``??*<n>*??`` with the provided replacement.

    This preserves the legacy template behaviour while letting the rest of the
    application treat templates as plain files on disk.
    """

    text = file_path.read_text(encoding="utf-8")

    def _repl(match: re.Match[str]) -> str:
        num = int(match.group(1))
        return replacement if num == target_int else match.group(0)

    new_text = _PLACEHOLDER_PATTERN.sub(_repl, text)
    file_path.write_text(new_text, encoding="utf-8")

