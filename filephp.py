"""Entry script: simulate typing PHP source into Visual Studio Code.

Usage:
    python filephp.py
    python filephp.py --dry-run
    python filephp.py --fresh

Reads inputs/inputphp.php and types it, character for character, into the
active VS Code editor. PHP tags (<?php ... ?>) and multiline syntax are typed
exactly like any other source text.
"""

from __future__ import annotations

import sys

import config
from controller import RunSpec, run
from document_readers import read_code_file


def main() -> int:
    input_path = config.INPUT_DIR / config.INPUT_FILES["php"]
    spec = RunSpec(
        script="filephp",
        target="vscode",
        target_label="Visual Studio Code (PHP)",
        input_path=input_path,
        kind="text",
        load_text=lambda: read_code_file(input_path),
        instructions=[
            "Open VS Code and create/open an EMPTY destination .php file.",
            "Click in the editor so the cursor is at the top of an empty file.",
            "Make sure focus is the editor, NOT the terminal, sidebar, or search.",
            "Tip: disable auto-indent/format-on-type for exact indentation "
            "(see README), or accept the editor's reformatting.",
        ],
    )
    return run(spec)


if __name__ == "__main__":
    sys.exit(main())
