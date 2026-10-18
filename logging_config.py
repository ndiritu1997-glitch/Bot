"""Logging setup for the typing simulator.

Records run metadata (script, timestamps, input file, target app, config,
completion/interruption status, errors/warnings). It does NOT log every
character typed, and it does not log window contents, passwords, or other
sensitive data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import config


def setup_logger(script_name: str) -> logging.Logger:
    """Return a configured logger that writes to both console and a log file.

    One log file per script per day keeps things tidy and greppable.
    """
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if setup_logger is called twice in one process.
    if logger.handlers:
        return logger

    stamp = datetime.now().strftime("%Y%m%d")
    log_path: Path = config.LOG_DIR / f"{script_name}_{stamp}.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    )

    logger.addHandler(file_handler)
    logger.propagate = False

    logger.info("=" * 60)
    logger.info("Logger started for %s", script_name)
    logger.info("Log file: %s", log_path)
    return logger
