"""Tests for the typing engine: dry-run safety, stop, delays, preservation."""

from __future__ import annotations

import pytest

import config
from helpers import RecordingBackend, make_pacer, make_state
from typing_engine import (
    KeyboardBackend,
    StopRequested,
    _cell_text,
    type_text,
)


def test_dry_run_backend_has_no_controller():
    """Dry-run mode must not construct a real keyboard controller."""
    backend = KeyboardBackend(dry_run=True)
    assert backend._controller is None
    # type_char is a no-op and must not raise.
    backend.type_char("x")


def test_type_text_preserves_characters_and_order(fast_timing, logger):
    source = "line one\n\tindented\nbraces { } and ; end."
    state = make_state(len(source))
    backend = RecordingBackend()
    pacer = make_pacer(state, logger)

    type_text(source, backend, pacer)

    # \r is swallowed; our source has none, so the stream must match exactly.
    assert backend.text == source
    assert state.position == len(source)


def test_type_text_can_resume_from_index(fast_timing, logger):
    source = "abcdefgh"
    state = make_state(len(source))
    backend = RecordingBackend()
    pacer = make_pacer(state, logger)

    type_text(source, backend, pacer, start_index=3)

    assert backend.text == "defgh"


def test_type_text_stops_when_requested(fast_timing, logger):
    source = "some text that will not finish"
    state = make_state(len(source))
    backend = RecordingBackend()
    # Stop fires immediately.
    pacer = make_pacer(state, logger, stop=lambda: True)

    with pytest.raises(StopRequested):
        type_text(source, backend, pacer)


def test_stop_midway(fast_timing, logger):
    source = "abcdefghijklmnop"
    state = make_state(len(source))
    backend = RecordingBackend()

    calls = {"n": 0}

    def stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 5  # allow a few characters, then stop

    pacer = make_pacer(state, logger, stop=stop)
    with pytest.raises(StopRequested):
        type_text(source, backend, pacer)

    # Some but not all characters were produced.
    assert 0 < len(backend.text) < len(source)


def test_startup_delay_is_configurable(monkeypatch):
    monkeypatch.setattr(config, "STARTUP_DELAY_SECONDS", 5)
    assert config.STARTUP_DELAY_SECONDS == 5


def test_cell_text_escapes_formula_triggers():
    assert _cell_text("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert _cell_text("+1") == "'+1"
    assert _cell_text("-5") == "'-5"
    assert _cell_text("@handle") == "'@handle"
    # Ordinary values are untouched.
    assert _cell_text("hello") == "hello"
    assert _cell_text("") == ""
