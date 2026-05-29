"""Database connection manager.

Owns the SQLite connection lifecycle. A single `Database` instance is created
at application startup and passed (via DI) to repositories that need it.

Transactions are handled via the `transaction()` context manager. Services use
it to group multiple repository calls into one atomic unit — guaranteeing the
A (atomicity) and C (consistency) in ACID.
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .schema import SCHEMA_SQL, apply_migrations


_log = logging.getLogger(__name__)


class Database:
    """Owns the SQLite connection and exposes transaction context managers."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Foreign keys + WAL for better concurrent-reader behavior. WAL also
        # gives us crash safety on power loss without sacrificing perf.
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._initialize()
        _log.info("Database ready: %s", path)

    # ------------------------------------------------------------- lifecycle #

    def _initialize(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        apply_migrations(self._conn)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ----------------------------------------------------------- connection #

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the raw connection. Prefer `transaction()` for writes."""
        return self._conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a block of repository calls atomically.

        Commits on success, rolls back on any exception. This is the unit of
        work boundary for services.
        """
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            _log.exception("Transaction rolled back")
            raise
