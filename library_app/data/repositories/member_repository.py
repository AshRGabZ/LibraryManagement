from __future__ import annotations

import sqlite3

from ...domain import Member


class MemberRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str, email: str | None, phone: str | None) -> int:
        cur = self._conn.execute(
            "INSERT INTO members (name, email, phone) VALUES (?, ?, ?)",
            (name, email, phone),
        )
        return cur.lastrowid

    def update(
        self, member_id: int, name: str, email: str | None, phone: str | None
    ) -> None:
        self._conn.execute(
            "UPDATE members SET name=?, email=?, phone=? WHERE id=?",
            (name, email, phone, member_id),
        )

    def delete(self, member_id: int) -> None:
        self._conn.execute("DELETE FROM loans WHERE member_id=?", (member_id,))
        self._conn.execute("DELETE FROM members WHERE id=?", (member_id,))

    def get(self, member_id: int) -> Member | None:
        row = self._conn.execute(
            "SELECT * FROM members WHERE id=?", (member_id,)
        ).fetchone()
        return Member.from_row(row) if row else None

    def list_all(self, search: str = "") -> list[Member]:
        if search:
            like = f"%{search}%"
            rows = self._conn.execute(
                """SELECT * FROM members
                   WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
                   ORDER BY name""",
                (like, like, like),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM members ORDER BY name"
            ).fetchall()
        return [Member.from_row(r) for r in rows]

    def has_active_loans(self, member_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM loans "
            "WHERE member_id=? AND returned_on IS NULL",
            (member_id,),
        ).fetchone()
        return row["cnt"]
