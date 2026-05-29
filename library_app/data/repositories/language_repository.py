from __future__ import annotations

import sqlite3

from ...domain import Language


class LanguageRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO languages (name) VALUES (?)", (name,)
        )
        return cur.lastrowid

    def get(self, language_id: int) -> Language | None:
        row = self._conn.execute(
            "SELECT * FROM languages WHERE id=?", (language_id,)
        ).fetchone()
        return Language.from_row(row) if row else None

    def list_all(self, search: str = "") -> list[Language]:
        if search:
            rows = self._conn.execute(
                "SELECT * FROM languages WHERE name LIKE ? ORDER BY name",
                (f"%{search}%",),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM languages ORDER BY name"
            ).fetchall()
        return [Language.from_row(r) for r in rows]

    def delete(self, language_id: int) -> None:
        self._conn.execute(
            "UPDATE books SET language_id=NULL WHERE language_id=?",
            (language_id,),
        )
        self._conn.execute(
            "DELETE FROM languages WHERE id=?", (language_id,)
        )
