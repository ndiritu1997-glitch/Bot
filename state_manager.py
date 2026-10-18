"""Resume / recovery state.

The bot saves its progress to a JSON file in the state directory
(C:\\contenttypingsim on Windows). If the run is stopped, crashes, or exits
during a break, it can pick up from where it left off the next time the same
source file is run.

State is keyed by script name, so each file type resumes independently. The
source file's SHA-256 is stored; if the source changed since the saved state,
the bot will not blindly resume (it asks the user).
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import config


@dataclass
class RunState:
    """Everything needed to resume a run."""

    script: str               # e.g. "filehtml"
    source_name: str          # e.g. "inputhtml.html"
    source_hash: str          # SHA-256 of the source file at run start
    total_units: int          # total chars / cells / slides to type
    position: int             # next unit index to type (0-based)
    active_seconds: float     # cumulative active typing time
    status: str               # "typing" | "on_break" | "stopped" | "completed"
    updated_at: float = field(default_factory=time.time)

    @property
    def is_resumable(self) -> bool:
        return self.status in ("typing", "on_break", "stopped") and (
            self.position < self.total_units
        )


def sha256_of(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _state_path(script: str) -> Path:
    return config.STATE_DIR / f"{script}.state.json"


def ensure_state_dir() -> Path:
    """Create the state directory if it does not exist. Returns the path."""
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    return config.STATE_DIR


def save_state(state: RunState) -> None:
    """Write state atomically so a crash mid-write can't corrupt the file."""
    ensure_state_dir()
    state.updated_at = time.time()
    target = _state_path(state.script)

    # Write to a temp file in the same directory, then replace.
    fd, tmp_name = tempfile.mkstemp(dir=str(config.STATE_DIR), suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            json.dump(asdict(state), fh, indent=2)
        tmp_path.replace(target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def load_state(script: str) -> Optional[RunState]:
    """Load saved state for a script, or None if there is none / it is unreadable."""
    path = _state_path(script)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunState(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def clear_state(script: str) -> None:
    """Remove saved state (e.g. after a clean completion)."""
    path = _state_path(script)
    if path.exists():
        path.unlink(missing_ok=True)
