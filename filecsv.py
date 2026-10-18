"""Entry script: simulate typing CSV data into Microsoft Excel.

Usage:
    python filecsv.py
    python filecsv.py --dry-run
    python filecsv.py --fresh

Reads inputs/inputcsv.csv and types it into Excel cell by cell, starting at
the configured start cell (default A1). Within a row it Tabs across; at the
end of a row it presses Enter, and Excel returns to the first column of the
next row.
"""

from __future__ import annotations

import sys

import config
from controller import RunSpec, run
from excel_reader import read_csv_rows


def main() -> int:
    input_path = config.INPUT_DIR / config.INPUT_FILES["csv"]
    spec = RunSpec(
        script="filecsv",
        target="excel",
        target_label="Microsoft Excel",
        input_path=input_path,
        kind="csv",
        load_rows=lambda: read_csv_rows(input_path),
        warnings_fn=lambda: [
            "Cells starting with = + - @ are typed as text (leading apostrophe) "
            "so Excel does not evaluate them as formulas.",
        ],
        instructions=[
            "Open Microsoft Excel and the destination worksheet.",
            f"Click cell {config.EXCEL_START_CELL} so it is the active cell.",
            "Use an empty area so existing data is not overwritten.",
        ],
    )
    return run(spec)


if __name__ == "__main__":
    sys.exit(main())
