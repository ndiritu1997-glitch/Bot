"""Shared pytest fixtures.

Tests import the project's top-level modules (config, typing_engine, ...), so
run pytest from the project root:

    python -m pytest tests/
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# Make the project root importable when pytest is run from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture
def fast_timing(monkeypatch, tmp_path):
    """Zero out all delays and push breaks out of reach, and redirect state
    writes to a temp dir, so engine tests run instantly and never touch the
    real state directory."""
    for name in (
        "MIN_KEY_DELAY", "MAX_KEY_DELAY",
        "WORD_PAUSE_MIN", "WORD_PAUSE_MAX",
        "PUNCT_PAUSE_MIN", "PUNCT_PAUSE_MAX",
        "LINE_PAUSE_MIN", "LINE_PAUSE_MAX",
        "PARAGRAPH_PAUSE_MIN", "PARAGRAPH_PAUSE_MAX",
    ):
        monkeypatch.setattr(config, name, 0.0)
    monkeypatch.setattr(config, "BREAK_AFTER_MIN_SECONDS", 10**9)
    monkeypatch.setattr(config, "BREAK_AFTER_MAX_SECONDS", 10**9)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(config, "ENABLE_TYPOS", False)
    return tmp_path


@pytest.fixture
def logger():
    lg = logging.getLogger("test")
    lg.addHandler(logging.NullHandler())
    return lg
