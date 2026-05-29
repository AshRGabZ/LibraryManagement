from __future__ import annotations

import sqlite3

from ...domain import Category


class CategoryRepository:
    """CRUD operations for categories. Operates on the injected connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )
        return cur.lastrowid

    def get(self, category_id: int) -> Category | None:
        row = self._conn.execute(
            "SELECT * FROM categories WHERE id=?", (category_id,)
        ).fetchone()
        return Category.from_row(row) if row else None

    def list_all(self, search: str = "") -> list[Category]:
        if search:
            rows = self._conn.execute(
                "SELECT * FROM categories WHERE name LIKE ? ORDER BY name",
                (f"%{search}%",),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM categories ORDER BY name"
            ).fetchall()
        return [Category.from_row(r) for r in rows]

    def delete(self, category_id: int) -> None:
        """Soft-detach: null out references then delete the row."""
        self._conn.execute(
            "UPDATE books SET category_id=NULL WHERE category_id=?",
            (category_id,),
        )
        self._conn.execute(
            "DELETE FROM categories WHERE id=?", (category_id,)
        )
