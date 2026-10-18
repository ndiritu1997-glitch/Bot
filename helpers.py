"""Test helpers: a recording keyboard backend and a Pacer builder."""

from __future__ import annotations

from typing import List

from state_manager import RunState
from typing_engine import KeyboardBackend, Pacer


class RecordingBackend(KeyboardBackend):
    """A dry-run backend that records the exact key stream, so tests can
    reconstruct what would have been typed and assert ordering/preservation.
    Sends no real key events."""

    def __init__(self) -> None:
        super().__init__(dry_run=True)
        self.out: List[str] = []

    def type_char(self, ch: str) -> None:
        self.out.append(ch)

    def press_enter(self) -> None:
        self.out.append("\n")

    def press_tab(self) -> None:
        self.out.append("\t")

    def press_backspace(self) -> None:
        if self.out:
            self.out.pop()

    @property
    def text(self) -> str:
        return "".join(self.out)


def make_state(total_units: int, script: str = "test") -> RunState:
    return RunState(
        script=script,
        source_name="source",
        source_hash="hash",
        total_units=total_units,
        position=0,
        active_seconds=0.0,
        status="typing",
    )


def make_pacer(state: RunState, logger, stop=lambda: False) -> Pacer:
    return Pacer(state=state, stop_check=stop, logger=logger)
