"""Entry script: simulate typing Word document text into Microsoft Word.

Usage (from PowerShell or the VS Code terminal):
    python filedocx.py
    python filedocx.py --dry-run
    python filedocx.py --fresh

Reads inputs/inputdocx.docx and types its paragraph text into the Word
document you have open and focused. Does not reproduce tables, images, or
formatting (you will be warned if those are present).
"""

from __future__ import annotations

import sys

import config
from controller import RunSpec, run
from document_readers import detect_unsupported_docx, read_docx_text


def main() -> int:
    input_path = config.INPUT_DIR / config.INPUT_FILES["docx"]
    spec = RunSpec(
        script="filedocx",
        target="word",
        target_label="Microsoft Word",
        input_path=input_path,
        kind="text",
        load_text=lambda: read_docx_text(input_path),
        warnings_fn=lambda: detect_unsupported_docx(input_path),
        instructions=[
            "Open Microsoft Word and the destination document.",
            "Use an EMPTY document (the bot types wherever the cursor is).",
            "Click in the document body so the cursor is blinking there.",
        ],
    )
    return run(spec)


if __name__ == "__main__":
    sys.exit(main())
