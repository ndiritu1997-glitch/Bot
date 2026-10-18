"""Entry script: simulate typing HTML source into Visual Studio Code.

Usage:
    python filehtml.py
    python filehtml.py --dry-run
    python filehtml.py --fresh

Reads inputs/inputhtml.html and types it, character for character, into the
active VS Code editor.
"""

from __future__ import annotations

import sys

import config
from controller import RunSpec, run
from document_readers import read_code_file


def main() -> int:
    input_path = config.INPUT_DIR / config.INPUT_FILES["html"]
    spec = RunSpec(
        script="filehtml",
        target="vscode",
        target_label="Visual Studio Code (HTML)",
        input_path=input_path,
        kind="text",
        load_text=lambda: read_code_file(input_path),
        instructions=[
            "Open VS Code and create/open an EMPTY destination .html file.",
            "Click in the editor so the cursor is at the top of an empty file.",
            "Make sure focus is the editor, NOT the terminal, sidebar, or search.",
            "Tip: disable auto-indent/format-on-type for exact indentation "
            "(see README), or accept the editor's reformatting.",
        ],
    )
    return run(spec)


if __name__ == "__main__":
    sys.exit(main())
