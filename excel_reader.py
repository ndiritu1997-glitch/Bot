"""Reader for CSV source files.

Reads tabular data using the standard-library csv module, preserving row and
column order, empty cells, blank rows, quoted fields, and delimiters. Never
modifies the source file.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from document_readers import SourceError


def read_csv_rows(path: Path) -> List[List[str]]:
    """Return the CSV as a list of rows (each a list of string cells).

    Uses csv.Sniffer to detect the delimiter where possible, falling back to a
    comma. Quoted fields are handled by the csv module.
    """
    if not path.exists():
        raise SourceError(f"Input file not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8-sig")  # tolerate a BOM
    except OSError as exc:
        raise SourceError(f"Could not read {path}: {exc}") from exc

    if raw.strip() == "":
        raise SourceError(f"Input file is empty: {path}")

    # Detect delimiter from a sample; default to comma if detection fails.
    try:
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel  # standard comma dialect

    rows: List[List[str]] = []
    reader = csv.reader(raw.splitlines(), dialect)
    for row in reader:
        rows.append(list(row))

    if not rows:
        raise SourceError(f"No rows parsed from {path}.")
    return rows


def count_cells(rows: List[List[str]]) -> int:
    """Total number of cells the typer will process (for progress/total)."""
    total = 0
    for row in rows:
        total += len(row) if row else 1  # a blank row counts as one unit
    return total
