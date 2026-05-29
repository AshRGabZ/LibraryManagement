"""Database schema and migration definitions.

Schema lives here as plain SQL so it can be inspected, version-controlled, and
applied idempotently. Migrations bring older databases up to the current schema
without losing user data — a desktop app must never silently drop tables.
"""
from __future__ import annotations

import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT UNIQUE,
    year INTEGER,
    category_id INTEGER,
    language_id INTEGER,
    total_copies INTEGER NOT NULL DEFAULT 1,
    available_copies INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (language_id) REFERENCES languages(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    joined TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    borrowed_on TEXT NOT NULL DEFAULT (DATE('now')),
    due_on TEXT,
    returned_on TEXT,
    renew_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_loans_book   ON loans(book_id);
CREATE INDEX IF NOT EXISTS idx_loans_member ON loans(member_id);
CREATE INDEX IF NOT EXISTS idx_loans_active ON loans(returned_on);
"""


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    return column in cols


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Bring an existing database up to the current schema.

    Each migration is idempotent — running this twice is safe. New migrations
    should be appended below; never edit a previously shipped one.
    """
    # 001 — renew_count on loans
    if not _column_exists(conn, "loans", "renew_count"):
        conn.execute(
            "ALTER TABLE loans ADD COLUMN renew_count INTEGER NOT NULL DEFAULT 0"
        )

    # 002 — category_id on books
    if not _column_exists(conn, "books", "category_id"):
        conn.execute(
            "ALTER TABLE books ADD COLUMN category_id INTEGER "
            "REFERENCES categories(id) ON DELETE SET NULL"
        )

    # 003 — language_id on books
    if not _column_exists(conn, "books", "language_id"):
        conn.execute(
            "ALTER TABLE books ADD COLUMN language_id INTEGER "
            "REFERENCES languages(id) ON DELETE SET NULL"
        )
