"""Database schema and migration definitions.

Schema lives here as plain SQL so it can be inspected, version-controlled, and
applied idempotently. Migrations bring older databases up to the current schema
without losing user data — a desktop app must never silently drop tables.
"""
from __future__ import annotations

import logging
import sqlite3


_log = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS languages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author_id INTEGER,
    isbn TEXT UNIQUE,
    year INTEGER,
    category_id INTEGER,
    language_id INTEGER,
    total_copies INTEGER NOT NULL DEFAULT 1,
    available_copies INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (author_id)   REFERENCES authors(id)    ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (language_id) REFERENCES languages(id)  ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    joined TEXT DEFAULT (DATE('now')),
    -- Soft-delete marker: NULL = active, a date string = archived ("deleted").
    -- Archiving keeps the row (and its loan history) intact and reversible.
    archived_at TEXT
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

-- One physical copy = one row. Serial is human-facing identifier on the
-- spine/label; status mirrors loan state but is the source of truth for
-- "is this specific copy available right now".
CREATE TABLE IF NOT EXISTS book_copies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'borrowed', 'lost', 'damaged')),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_copies_book   ON book_copies(book_id);
CREATE INDEX IF NOT EXISTS idx_copies_status ON book_copies(status);
"""


def _next_copy_serial(conn: sqlite3.Connection, book_id: int, n: int) -> str:
    """Default serial pattern: B<book_id>-<NN>. Library can re-label later."""
    return f"B{book_id}-{n:02d}"


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

    # 004 — uniqueness on (name, phone) for members.
    # SQLite's UNIQUE INDEX treats each NULL as distinct, so this constraint
    # only blocks duplicate (Alice + 9876…) — multiple Alices with no phone
    # still coexist. If a legacy DB already holds duplicates, we log a
    # warning and skip the index; the service layer's pre-check still keeps
    # NEW duplicates out.
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_members_name_phone "
            "ON members(name, phone)"
        )
    except sqlite3.IntegrityError as e:
        dupes = conn.execute(
            "SELECT name, phone, COUNT(*) AS cnt FROM members "
            "GROUP BY name, phone HAVING cnt > 1"
        ).fetchall()
        _log.warning(
            "Could not create unique (name, phone) index — existing duplicates: "
            "%s. Service-layer check will still block new duplicates.",
            [(r["name"], r["phone"], r["cnt"]) for r in dupes],
        )

    # 005 — loans.copy_id (FK to book_copies.id). Nullable so historic loans
    # without copy tracking aren't broken.
    if not _column_exists(conn, "loans", "copy_id"):
        conn.execute(
            "ALTER TABLE loans ADD COLUMN copy_id INTEGER "
            "REFERENCES book_copies(id)"
        )

    # 006 — backfill book_copies for every existing book. Each book gets
    # `total_copies` rows with auto-generated serials. Idempotent: if a book
    # already has copies recorded, leave it alone.
    books_needing_copies = conn.execute(
        """SELECT b.id, b.total_copies
           FROM books b
           LEFT JOIN (
             SELECT book_id, COUNT(*) AS cnt FROM book_copies GROUP BY book_id
           ) c ON c.book_id = b.id
           WHERE COALESCE(c.cnt, 0) < b.total_copies"""
    ).fetchall()
    for b in books_needing_copies:
        existing = conn.execute(
            "SELECT COUNT(*) AS cnt FROM book_copies WHERE book_id=?",
            (b["id"],),
        ).fetchone()["cnt"]
        to_create = b["total_copies"] - existing
        for i in range(existing + 1, existing + to_create + 1):
            conn.execute(
                "INSERT INTO book_copies (book_id, serial_number, status) "
                "VALUES (?, ?, 'available')",
                (b["id"], _next_copy_serial(conn, b["id"], i)),
            )

    # 007 — link active loans to specific copies. For each unlinked active
    # loan, grab the lowest-numbered available copy of that book and bind
    # them together. Maintains the invariant: book_copies.status counts
    # match books.available_copies.
    unlinked_loans = conn.execute(
        "SELECT id, book_id FROM loans "
        "WHERE returned_on IS NULL AND copy_id IS NULL"
    ).fetchall()
    for loan in unlinked_loans:
        copy = conn.execute(
            "SELECT id FROM book_copies "
            "WHERE book_id=? AND status='available' "
            "ORDER BY id LIMIT 1",
            (loan["book_id"],),
        ).fetchone()
        if copy is None:
            # Shouldn't happen if data is consistent, but don't crash the
            # migration over it — just log.
            _log.warning(
                "Loan %s for book %s has no available copy to bind to; "
                "leaving copy_id NULL.", loan["id"], loan["book_id"]
            )
            continue
        conn.execute(
            "UPDATE loans SET copy_id=? WHERE id=?",
            (copy["id"], loan["id"]),
        )
        conn.execute(
            "UPDATE book_copies SET status='borrowed' WHERE id=?",
            (copy["id"],),
        )

    # 008 — author_id on books (FK to the new authors table). The authors
    # table itself is created by SCHEMA_SQL above (idempotent for old DBs).
    if not _column_exists(conn, "books", "author_id"):
        conn.execute(
            "ALTER TABLE books ADD COLUMN author_id INTEGER "
            "REFERENCES authors(id) ON DELETE SET NULL"
        )

    # 009 — promote the legacy free-text `books.author` to real author rows,
    # then drop the column. Idempotent: once `author` is gone we skip entirely.
    # SQLite ≥ 3.35 supports ALTER TABLE … DROP COLUMN; dropping a plain (non
    # indexed, non-FK) column keeps the table name so loans/book_copies FKs
    # that reference books(id) stay valid.
    if _column_exists(conn, "books", "author"):
        legacy = conn.execute(
            "SELECT DISTINCT author FROM books "
            "WHERE author IS NOT NULL AND TRIM(author) <> ''"
        ).fetchall()
        for row in legacy:
            name = row["author"].strip()
            conn.execute(
                "INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,)
            )
            conn.execute(
                "UPDATE books "
                "SET author_id = (SELECT id FROM authors WHERE name = ?) "
                "WHERE author_id IS NULL AND TRIM(author) = ?",
                (name, name),
            )
        conn.execute("ALTER TABLE books DROP COLUMN author")
        _log.info("Migrated %d distinct author name(s) into authors table",
                  len(legacy))

    # 010 — soft-delete for members. archived_at NULL = active; a date string
    # marks the member "deleted" (archived) while keeping the row + loan history.
    if not _column_exists(conn, "members", "archived_at"):
        conn.execute("ALTER TABLE members ADD COLUMN archived_at TEXT")
