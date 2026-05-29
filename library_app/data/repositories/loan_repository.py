from __future__ import annotations

import sqlite3

from ...domain import Loan, LoanWithDetails


class LoanRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        book_id: int,
        member_id: int,
        borrowed_on: str,
        due_on: str,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO loans (book_id, member_id, borrowed_on, due_on)
               VALUES (?, ?, ?, ?)""",
            (book_id, member_id, borrowed_on, due_on),
        )
        return cur.lastrowid

    def mark_returned(self, loan_id: int, returned_on: str) -> None:
        self._conn.execute(
            "UPDATE loans SET returned_on=? WHERE id=?",
            (returned_on, loan_id),
        )

    def extend_due(self, loan_id: int, new_due_on: str) -> None:
        self._conn.execute(
            "UPDATE loans SET due_on=?, renew_count = renew_count + 1 "
            "WHERE id=?",
            (new_due_on, loan_id),
        )

    def get(self, loan_id: int) -> Loan | None:
        row = self._conn.execute(
            "SELECT * FROM loans WHERE id=?", (loan_id,)
        ).fetchone()
        return Loan.from_row(row) if row else None

    def get_with_details(self, loan_id: int) -> LoanWithDetails | None:
        row = self._conn.execute(
            """SELECT loans.*,
                      books.title  AS book_title,
                      members.name AS member_name
               FROM loans
               JOIN books   ON books.id   = loans.book_id
               JOIN members ON members.id = loans.member_id
               WHERE loans.id=?""",
            (loan_id,),
        ).fetchone()
        return LoanWithDetails.from_row(row) if row else None

    def list_all(
        self,
        active_only: bool = False,
        search: str = "",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[LoanWithDetails]:
        """List loans, optionally filtered.

        `from_date` and `to_date` are inclusive ISO date strings filtering by
        `borrowed_on` — i.e. "loans started between these dates".
        """
        sql = """SELECT loans.*,
                        books.title  AS book_title,
                        members.name AS member_name
                 FROM loans
                 JOIN books   ON books.id   = loans.book_id
                 JOIN members ON members.id = loans.member_id"""
        clauses, params = [], []
        if active_only:
            clauses.append("loans.returned_on IS NULL")
        if search:
            like = f"%{search}%"
            clauses.append("(books.title LIKE ? OR members.name LIKE ?)")
            params.extend([like, like])
        if from_date:
            clauses.append("loans.borrowed_on >= ?")
            params.append(from_date)
        if to_date:
            clauses.append("loans.borrowed_on <= ?")
            params.append(to_date)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY loans.returned_on IS NOT NULL, loans.due_on"
        rows = self._conn.execute(sql, params).fetchall()
        return [LoanWithDetails.from_row(r) for r in rows]
