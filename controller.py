"""Shared run orchestration for every entry script.

Flow for a run:
  1. Set up logging and the state directory.
  2. Validate the input file (exists, readable, non-empty, supported).
  3. Load content and compute the total unit count.
  4. Offer to resume if matching saved state exists.
  5. Start the emergency-stop listener (global hotkey) + handle Ctrl+C.
  6. Show a banner, warnings, prep instructions, and a 30s countdown.
  7. Type, with human delays, long breaks, progress, and periodic state saves.
  8. Finalise: clear state on completion, keep it on stop/crash for resume.

Entry scripts build a RunSpec and call `run(spec)`.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence

import application_checks
import config
from logging_config import setup_logger
from state_manager import (
    RunState,
    clear_state,
    ensure_state_dir,
    load_state,
    save_state,
    sha256_of,
)
from typing_engine import (
    KeyboardBackend,
    Pacer,
    ProgressInfo,
    StopRequested,
    type_fragment,
    type_rows,
    type_text,
)


@dataclass
class RunSpec:
    script: str                 # "filehtml", "filedocx", ...
    target: str                 # "word" | "excel" | "powerpoint" | "vscode"
    target_label: str           # "Microsoft Word", "Visual Studio Code", ...
    input_path: Path
    kind: str                   # "text" | "csv" | "pptx"
    instructions: List[str]     # what the user must prepare during countdown
    load_text: Optional[Callable[[], str]] = None
    load_rows: Optional[Callable[[], Sequence[Sequence[str]]]] = None
    load_slides: Optional[Callable[[], list]] = None
    warnings_fn: Optional[Callable[[], List[str]]] = None


# ---------------------------------------------------------------------------
# CLI flags shared by every entry script
# ---------------------------------------------------------------------------


def parse_common_args(script: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=f"python {script}.py")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be typed without sending any keyboard events.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore any saved resume state and start from the beginning.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Answer yes to prompts (e.g. resume) without asking.",
    )
    parser.add_argument(
        "--typos",
        action="store_true",
        help="Enable occasional typo-and-correct behaviour.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Small console helpers
# ---------------------------------------------------------------------------


def _hr() -> None:
    print("-" * 60)


def _countdown(seconds: int, stop_check: Callable[[], bool]) -> bool:
    """Show a visible countdown. Returns False if a stop was requested."""
    for remaining in range(seconds, 0, -1):
        if stop_check():
            return False
        print(f"  Starting in {remaining:>2d}s ...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 40, end="\r")
    return True


def _ask_yes_no(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return True  # non-interactive: default to yes (resume)
    try:
        answer = input(f"{question} [Y/n] ").strip().lower()
    except EOFError:
        return True
    return answer in ("", "y", "yes")


# ---------------------------------------------------------------------------
# Resume handling
# ---------------------------------------------------------------------------


def _resolve_start(
    spec: RunSpec,
    total_units: int,
    source_hash: str,
    args: argparse.Namespace,
    logger,
) -> RunState:
    """Decide whether to resume or start fresh; return the RunState to use."""
    fresh_state = RunState(
        script=spec.script,
        source_name=spec.input_path.name,
        source_hash=source_hash,
        total_units=total_units,
        position=0,
        active_seconds=0.0,
        status="typing",
    )

    if args.fresh:
        return fresh_state

    saved = load_state(spec.script)
    if saved is None or not saved.is_resumable:
        return fresh_state

    if saved.source_hash != source_hash:
        print(
            "  Found saved progress, but the source file has CHANGED since then.\n"
            "  Starting fresh to avoid typing mismatched content."
        )
        logger.info("Saved state ignored: source hash changed.")
        return fresh_state

    done_pct = int(saved.position * 100 / max(total_units, 1))
    print(
        f"  Saved progress found: {saved.position}/{total_units} units "
        f"(~{done_pct}%), status '{saved.status}'."
    )
    if _ask_yes_no("  Resume from where it left off?", args.yes):
        saved.status = "typing"
        saved.total_units = total_units  # in case of harmless re-count
        logger.info("Resuming from unit %d of %d.", saved.position, total_units)
        print(
            "  NOTE: during the countdown, place the cursor at the END of the\n"
            "  text already typed so new content continues correctly."
        )
        return saved

    logger.info("User chose to start fresh.")
    return fresh_state


# ---------------------------------------------------------------------------
# Stop listener (global hotkey)
# ---------------------------------------------------------------------------


def _start_hotkey_listener(stop_event: threading.Event, logger):
    """Start a global hotkey listener. Returns the listener or None."""
    try:
        from pynput import keyboard  # type: ignore
    except Exception:
        logger.info("pynput not available; global stop hotkey disabled.")
        return None

    def on_activate() -> None:
        logger.info("Stop hotkey pressed.")
        stop_event.set()

    try:
        listener = keyboard.GlobalHotKeys({config.STOP_HOTKEY: on_activate})
        listener.start()
        return listener
    except Exception as exc:
        logger.info("Could not start hotkey listener: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Progress / break callbacks
# ---------------------------------------------------------------------------


def _make_callbacks(logger):
    def on_progress(info: ProgressInfo) -> None:
        print(f"  Progress: {info.percent:>3d}%  ({info.position}/{info.total})")
        logger.info("Progress %d%% (%d/%d)", info.percent, info.position, info.total)

    def on_break(minutes: int) -> None:
        print(
            f"\n  [break] Pausing for about {minutes} minutes, like a human would.\n"
            f"  The run will continue automatically. Progress is saved."
        )

    def on_resume_from_break() -> None:
        print("  [break] Back to typing.\n")

    return on_progress, on_break, on_resume_from_break


# ---------------------------------------------------------------------------
# PowerPoint run loop
# ---------------------------------------------------------------------------


def _run_pptx(
    spec: RunSpec,
    state: RunState,
    backend: KeyboardBackend,
    pacer: Pacer,
    logger,
) -> None:
    slides = spec.load_slides()  # type: ignore[misc]

    if backend.dry_run:
        for idx in range(state.position, len(slides)):
            s = slides[idx]
            print(f"  [dry-run] Slide {idx + 1}: title={s.title!r} "
                  f"body_lines={s.body.count(chr(10)) + 1 if s.body else 0}")
            pacer.checkpoint(idx + 1, force=True)
            pacer.report_progress(idx + 1)
        return

    # Real typing via COM to create slides + select placeholders.
    from powerpoint_reader import PowerPointComError, PowerPointComSession

    try:
        session = PowerPointComSession()
    except PowerPointComError as exc:
        raise RuntimeError(
            f"PowerPoint automation unavailable: {exc}\n"
            f"Tip: run with --dry-run to preview, or see the README's "
            f"PowerPoint section."
        ) from exc

    for idx in range(state.position, len(slides)):
        pacer.check_stop()
        pacer.maybe_break()
        s = slides[idx]

        session.activate()
        slide = session.add_slide()

        if s.title and session.select_title_placeholder(slide):
            # Enter edit mode on the selected placeholder, then type.
            _enter_edit_mode(backend)
            type_fragment(s.title, backend, pacer)
            _exit_edit_mode(backend)

        if s.body and session.select_body_placeholder(slide):
            _enter_edit_mode(backend)
            type_fragment(s.body, backend, pacer)
            _exit_edit_mode(backend)

        pacer.checkpoint(idx + 1)
        pacer.report_progress(idx + 1)

    pacer.checkpoint(len(slides), force=True)


def _enter_edit_mode(backend: KeyboardBackend) -> None:
    """With a placeholder selected, F2 enters text-edit mode."""
    if backend.dry_run or backend._Key is None:  # noqa: SLF001
        return
    backend._controller.press(backend._Key.f2)   # noqa: SLF001
    backend._controller.release(backend._Key.f2)  # noqa: SLF001
    time.sleep(0.2)


def _exit_edit_mode(backend: KeyboardBackend) -> None:
    """Escape exits edit mode (and then deselects)."""
    if backend.dry_run or backend._Key is None:  # noqa: SLF001
        return
    backend._controller.press(backend._Key.esc)   # noqa: SLF001
    backend._controller.release(backend._Key.esc)  # noqa: SLF001
    time.sleep(0.1)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def run(spec: RunSpec) -> int:
    args = parse_common_args(spec.script)
    config.DRY_RUN = args.dry_run
    config.ENABLE_TYPOS = config.ENABLE_TYPOS or args.typos

    logger = setup_logger(spec.script)
    logger.info("Config: %s", config.describe())
    logger.info("Target: %s | Input: %s", spec.target_label, spec.input_path)

    _hr()
    print(f"  Target application : {spec.target_label}")
    print(f"  Input file         : {spec.input_path}")
    print(f"  Mode               : {'DRY RUN (no keys sent)' if args.dry_run else 'LIVE'}")
    _hr()

    # --- validate + load -------------------------------------------------
    try:
        ensure_state_dir()
        if spec.kind == "text":
            text = spec.load_text()  # type: ignore[misc]
            total_units = len(text)
        elif spec.kind == "csv":
            rows = spec.load_rows()  # type: ignore[misc]
            from excel_reader import count_cells

            total_units = count_cells(list(rows))
        elif spec.kind == "pptx":
            slides = spec.load_slides()  # type: ignore[misc]
            total_units = len(slides)
        else:
            raise RuntimeError(f"Unknown kind: {spec.kind}")
    except Exception as exc:
        logger.error("Validation/load failed: %s", exc)
        print(f"\n  ERROR: {exc}\n")
        return 2

    if total_units == 0:
        print("\n  ERROR: nothing to type (no content found).\n")
        logger.error("No content to type.")
        return 2

    source_hash = sha256_of(spec.input_path)

    # --- warnings about unsupported content ------------------------------
    if spec.warnings_fn:
        for w in spec.warnings_fn():
            print(f"  WARNING: {w}")
            logger.info("WARNING: %s", w)

    # --- application availability ----------------------------------------
    print("  " + application_checks.describe_check(spec.target))

    # --- resume decision -------------------------------------------------
    state = _resolve_start(spec, total_units, source_hash, args, logger)

    # --- instructions ----------------------------------------------------
    _hr()
    print("  PREPARE THE DESTINATION NOW:")
    for line in spec.instructions:
        print(f"    - {line}")
    print(f"    - To STOP at any time: press {config.STOP_HOTKEY_HUMAN} (works from")
    print(f"      any window), or press Ctrl+C in this terminal. Progress is saved.")
    _hr()

    # --- stop machinery --------------------------------------------------
    stop_event = threading.Event()
    listener = _start_hotkey_listener(stop_event, logger)
    stop_check = stop_event.is_set

    backend = KeyboardBackend(dry_run=args.dry_run)
    on_progress, on_break, on_resume = _make_callbacks(logger)
    pacer = Pacer(
        state=state,
        stop_check=stop_check,
        logger=logger,
        on_progress=on_progress,
        on_break=on_break,
        on_resume_from_break=on_resume,
    )

    # --- countdown -------------------------------------------------------
    print(f"  Preparation time: {config.STARTUP_DELAY_SECONDS} seconds")
    if not _countdown(config.STARTUP_DELAY_SECONDS, stop_check):
        print("\n  Cancelled before typing started.")
        logger.info("Cancelled during countdown.")
        if listener:
            listener.stop()
        return 0

    print("  Starting typing simulation...\n")
    logger.info("Typing started at unit %d/%d.", state.position, total_units)

    # --- type ------------------------------------------------------------
    exit_code = 0
    try:
        if spec.kind == "text":
            type_text(text, backend, pacer, start_index=state.position)
        elif spec.kind == "csv":
            type_rows(list(rows), backend, pacer, start_index=state.position)
        elif spec.kind == "pptx":
            _run_pptx(spec, state, backend, pacer, logger)

        state.status = "completed"
        save_state(state)
        clear_state(spec.script)  # clean completion: no resume needed
        print("\n  Progress: 100%")
        print("  Typing simulation completed.")
        logger.info("Completed successfully.")

    except StopRequested:
        backend.release_all()
        state.status = "stopped"
        save_state(state)
        print(f"\n  Stopped by user at {state.position}/{total_units}. "
              f"Run again to resume.")
        logger.info("Stopped by user at %d/%d.", state.position, total_units)
        exit_code = 130

    except KeyboardInterrupt:
        backend.release_all()
        state.status = "stopped"
        save_state(state)
        print(f"\n  Ctrl+C: stopped at {state.position}/{total_units}. "
              f"Run again to resume.")
        logger.info("Stopped via Ctrl+C at %d/%d.", state.position, total_units)
        exit_code = 130

    except Exception as exc:  # unexpected error: save, report stage, don't continue
        backend.release_all()
        state.status = "stopped"
        save_state(state)
        print(f"\n  ERROR during typing at {state.position}/{total_units}: {exc}")
        logger.exception("Error during typing: %s", exc)
        exit_code = 1

    finally:
        if listener:
            listener.stop()

    return exit_code
