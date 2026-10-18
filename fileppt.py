"""Entry script: simulate typing slide text into Microsoft PowerPoint.

Usage:
    python fileppt.py
    python fileppt.py --dry-run
    python fileppt.py --fresh

Reads inputs/inputppt.pptx and recreates each slide's title and body text in
the PowerPoint presentation you have open. New blank slides are created via
PowerPoint COM automation; the text itself is entered with simulated
keystrokes so the activity is observable and recorded.

Requires pywin32 for live typing. Use --dry-run to preview without PowerPoint.
"""

from __future__ import annotations

import sys

import config
from controller import RunSpec, run
from powerpoint_reader import detect_unsupported_pptx, read_pptx_slides


def main() -> int:
    input_path = config.INPUT_DIR / config.INPUT_FILES["pptx"]
    spec = RunSpec(
        script="fileppt",
        target="powerpoint",
        target_label="Microsoft PowerPoint",
        input_path=input_path,
        kind="pptx",
        load_slides=lambda: read_pptx_slides(input_path),
        warnings_fn=lambda: detect_unsupported_pptx(input_path),
        instructions=[
            "Open Microsoft PowerPoint with a presentation (even an empty one).",
            "Leave PowerPoint in Normal editing view and in the foreground.",
            "The bot adds new slides at the end and types into their placeholders.",
            "Do not click away while it is typing, or keystrokes may go elsewhere.",
        ],
    )
    return run(spec)


if __name__ == "__main__":
    sys.exit(main())
