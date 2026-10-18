"""Central configuration for the typing simulator.

Every tunable value lives here so the seven entry scripts and the shared
modules never duplicate configuration logic. Values are plain module-level
constants; override them per run with environment variables where noted, or
edit them directly.

This file contains NO automation logic and imports nothing heavy, so it is
safe to import from tests.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Project root = the folder this file sits in. All relative paths resolve from
# here, so scripts work whether launched from PowerShell, the project folder,
# or a VS Code terminal.
PROJECT_ROOT: Path = Path(__file__).resolve().parent

# Where the source/input files live.
INPUT_DIR: Path = PROJECT_ROOT / "inputs"

# Where run logs are written.
LOG_DIR: Path = PROJECT_ROOT / "logs"

# Where resume/recovery state is saved. The user asked for C:\contenttypingsim.
# On a non-Windows machine (e.g. for tests) that path is invalid, so we fall
# back to a local folder. Override with the CONTENTTYPINGSIM_STATE_DIR env var.
def _default_state_dir() -> Path:
    env = os.environ.get("CONTENTTYPINGSIM_STATE_DIR")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"C:\contenttypingsim")
    # Non-Windows fallback (tests, development on Linux/Mac).
    return PROJECT_ROOT / "contenttypingsim"


STATE_DIR: Path = _default_state_dir()

# ---------------------------------------------------------------------------
# Input filenames (configurable constants, per the spec)
# ---------------------------------------------------------------------------

INPUT_FILES = {
    "docx": "inputdocx.docx",
    "csv": "inputcsv.csv",
    "pptx": "inputppt.pptx",
    "html": "inputhtml.html",
    "css": "inputcss.css",
    "js": "inputjs.js",
    "php": "inputphp.php",
}

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

# Visible countdown (seconds) before typing starts, so the user can focus the
# target window and place the cursor.
STARTUP_DELAY_SECONDS: int = 30

# ---------------------------------------------------------------------------
# Keystroke timing (seconds). These are starting points, not fixed law.
# ---------------------------------------------------------------------------

MIN_KEY_DELAY: float = 0.04
MAX_KEY_DELAY: float = 0.15

WORD_PAUSE_MIN: float = 0.08
WORD_PAUSE_MAX: float = 0.25

# Extra pause after sentence punctuation (. ! ?).
PUNCT_PAUSE_MIN: float = 0.15
PUNCT_PAUSE_MAX: float = 0.50

LINE_PAUSE_MIN: float = 0.15
LINE_PAUSE_MAX: float = 0.45

PARAGRAPH_PAUSE_MIN: float = 0.40
PARAGRAPH_PAUSE_MAX: float = 1.20

# ---------------------------------------------------------------------------
# Long breaks (the "take a rest like a human" behaviour)
# ---------------------------------------------------------------------------

# After this much *active typing time* the bot takes a break. A fresh threshold
# is chosen (uniformly in this range) after every break.
BREAK_AFTER_MIN_SECONDS: int = 90 * 60   # 1h30
BREAK_AFTER_MAX_SECONDS: int = 120 * 60  # 2h00

# How long a break lasts (chosen uniformly in this range each time).
BREAK_LENGTH_MIN_SECONDS: int = 10 * 60  # 10 min
BREAK_LENGTH_MAX_SECONDS: int = 20 * 60  # 20 min

# ---------------------------------------------------------------------------
# Optional realism (off by default; entry scripts can turn these on)
# ---------------------------------------------------------------------------

# Occasionally type a wrong character, pause, backspace, and retype. The final
# text is always identical to the source.
ENABLE_TYPOS: bool = False
TYPO_PROBABILITY: float = 0.01          # per eligible character
TYPO_NOTICE_PAUSE_MIN: float = 0.20     # pause before "noticing" the typo
TYPO_NOTICE_PAUSE_MAX: float = 0.60

# ---------------------------------------------------------------------------
# Progress + state cadence
# ---------------------------------------------------------------------------

# Report progress roughly every N percent (not per keystroke).
PROGRESS_STEP_PERCENT: int = 5

# Save resume state at least every N seconds of typing, and always on break,
# stop, and completion.
STATE_SAVE_EVERY_SECONDS: int = 20

# ---------------------------------------------------------------------------
# Emergency stop
# ---------------------------------------------------------------------------

# Global hotkey (works from any focused window) in pynput GlobalHotKeys format.
# Ctrl+Alt+Shift+S is unlikely to collide with Word/Excel/PowerPoint/VS Code,
# and is harmless if the key event also reaches the app.
STOP_HOTKEY: str = "<ctrl>+<alt>+<shift>+s"
STOP_HOTKEY_HUMAN: str = "Ctrl+Alt+Shift+S"

# ---------------------------------------------------------------------------
# Excel navigation
# ---------------------------------------------------------------------------

# Starting cell for CSV typing. Excel's own behaviour returns the cursor to the
# starting column of the next row when you press Enter after Tabbing across a
# row, which is how row transitions are handled.
EXCEL_START_CELL: str = "A1"

# CSV fields beginning with any of these are prefixed with a leading
# apostrophe so Excel stores them as text and never evaluates them as formulas.
EXCEL_FORMULA_TRIGGERS: tuple[str, ...] = ("=", "+", "-", "@")

# ---------------------------------------------------------------------------
# Destination-content safety policy (VS Code / code files)
# ---------------------------------------------------------------------------

# "prompt"  : warn the user in the countdown instructions to use an empty file.
# The bot never clears or saves the destination itself.
DESTINATION_POLICY: str = "prompt"

# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

# When True, no real keyboard events are sent. The engine logs/prints what it
# *would* type. Entry scripts enable this with the --dry-run flag.
DRY_RUN: bool = False


def describe() -> str:
    """Human-readable summary of the key settings, for logs and startup."""
    return (
        f"startup_delay={STARTUP_DELAY_SECONDS}s "
        f"key_delay=[{MIN_KEY_DELAY},{MAX_KEY_DELAY}]s "
        f"break_after=[{BREAK_AFTER_MIN_SECONDS//60},{BREAK_AFTER_MAX_SECONDS//60}]min "
        f"break_len=[{BREAK_LENGTH_MIN_SECONDS//60},{BREAK_LENGTH_MAX_SECONDS//60}]min "
        f"typos={ENABLE_TYPOS} dry_run={DRY_RUN} "
        f"state_dir={STATE_DIR}"
    )
