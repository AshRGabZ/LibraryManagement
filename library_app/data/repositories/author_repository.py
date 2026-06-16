from __future__ import annotations

import sqlite3

from ...domain import Author


class AuthorRepository:
    """CRUD operations for authors. Operates on the injected connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO authors (name) VALUES (?)", (name,)
        )
        return cur.lastrowid

    def update(self, author_id: int, name: str) -> None:
        """Rename an author. Every book referencing this author_id instantly
        reflects the new name (the name is read via JOIN, not stored on books)."""
        self._conn.execute(
            "UPDATE authors SET name=? WHERE id=?", (name, author_id)
        )

    def get(self, author_id: int) -> Author | None:
        row = self._conn.execute(
            "SELECT * FROM authors WHERE id=?", (author_id,)
        ).fetchone()
        return Author.from_row(row) if row else None

    def list_all(self, search: str = "") -> list[Author]:
        if search:
            rows = self._conn.execute(
                "SELECT * FROM authors WHERE name LIKE ? ORDER BY name",
                (f"%{search}%",),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM authors ORDER BY name"
            ).fetchall()
        return [Author.from_row(r) for r in rows]

    def delete(self, author_id: int) -> None:
        """Soft-detach: null out references then delete the row."""
        self._conn.execute(
            "UPDATE books SET author_id=NULL WHERE author_id=?", (author_id,)
        )
        self._conn.execute(
            "DELETE FROM authors WHERE id=?", (author_id,)
        )
