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

    def find_by_name_and_phone(
        self,
        name: str,
        phone: str | None,
        *,
        exclude_id: int | None = None,
    ) -> Member | None:
        """Return a member matching the (name, phone) composite key, or None.

        Used to enforce "no two members with the same name + phone" at the
        service layer. `exclude_id` is set on UPDATE so a member doesn't
        collide with themselves.

        Phone NULLs use SQL's normal "NULL is never equal" semantics — two
        members named "Alice" both with NULL phone don't collide here.
        """
        sql_parts = ["SELECT * FROM members WHERE name = ?"]
        params: list = [name]
        if phone is None:
            sql_parts.append("AND phone IS NULL")
        else:
            sql_parts.append("AND phone = ?")
            params.append(phone)
        if exclude_id is not None:
            sql_parts.append("AND id <> ?")
            params.append(exclude_id)
        sql_parts.append("LIMIT 1")
        row = self._conn.execute(" ".join(sql_parts), params).fetchone()
        return Member.from_row(row) if row else None
