"""Text-centric helpers that were previously embedded in the Streamlit app."""

from __future__ import annotations

import csv
from pathlib import Path


def parse_first_line_column(csv_path: Path, index: int) -> str:
    """Return the value at ``index`` (1-based) from the first row of the csv."""

    with csv_path.open("r", encoding="utf-8") as file:
        reader = csv.reader(file)
        first_line = next(reader, None)

    if first_line is None:
        raise ValueError("CSV file is empty")
    if index < 1 or index > len(first_line):
        raise IndexError("Column index out of range")
    return first_line[index - 1]

