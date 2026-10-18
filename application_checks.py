"""Best-effort checks that the intended target application is available.

These checks reduce the risk of typing into the wrong place, but they are
NOT a guarantee. Checking that a process is running does not prove the correct
document, slide, cell, or editor is focused. The 30-second countdown plus
clear on-screen instructions are the primary safety mechanism; these checks
are a secondary guard.

On non-Windows systems (tests/development) every check degrades gracefully to
"unknown" rather than raising.
"""

from __future__ import annotations

import os
from typing import Iterable

# Process names we look for per target application.
_PROCESS_NAMES = {
    "word": ("WINWORD.EXE",),
    "excel": ("EXCEL.EXE",),
    "powerpoint": ("POWERPNT.EXE",),
    "vscode": ("Code.exe",),
}


def _running_process_names() -> set[str]:
    """Return the set of running process executable names (Windows only).

    Uses psutil if available; otherwise returns an empty set and callers treat
    the result as 'unknown'.
    """
    try:
        import psutil  # type: ignore
    except Exception:
        return set()

    names: set[str] = set()
    for proc in psutil.process_iter(["name"]):
        name = proc.info.get("name")
        if name:
            names.add(name)
    return names


def is_application_running(target: str) -> bool | None:
    """True/False if we can tell, or None if we cannot determine it.

    `target` is one of: word, excel, powerpoint, vscode.
    """
    target = target.lower()
    wanted: Iterable[str] = _PROCESS_NAMES.get(target, ())
    if not wanted:
        return None

    if os.name != "nt":
        return None  # cannot meaningfully check off-Windows

    running = _running_process_names()
    if not running:
        return None  # psutil missing -> unknown

    running_lower = {n.lower() for n in running}
    return any(w.lower() in running_lower for w in wanted)


def describe_check(target: str) -> str:
    """Human-readable line for the startup banner."""
    result = is_application_running(target)
    if result is True:
        return f"Target application ({target}) detected as running."
    if result is False:
        return (
            f"WARNING: could not detect {target} running. "
            f"Make sure it is open and focused before the countdown ends."
        )
    return (
        f"NOTE: cannot verify whether {target} is running on this system. "
        f"Make sure it is open and focused before the countdown ends."
    )
