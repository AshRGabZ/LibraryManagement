"""Application logging setup.

A packaged desktop app must write diagnostic information somewhere we can find
when a user reports a problem. We log to a rotating file in the same user-data
directory as the SQLite database — 5 files × 1 MB is plenty for a desktop app
and bounds disk usage.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """Set up the root logger with a rotating file + a stderr handler.

    Safe to call multiple times — clears any prior handlers first so test
    suites and re-invocations get a fresh configuration.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "library_app.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    logging.getLogger(__name__).info("Logging configured → %s", log_file)
