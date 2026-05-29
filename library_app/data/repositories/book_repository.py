from __future__ import annotations

import sqlite3

from ...domain import Book, BookWithDetails


class BookRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(
        self,
        title: str,
        author: str,
        isbn: str | None,
        year: int | None,
        category_id: int | None,
        language_id: int | None,
        total_copies: int,
    ) -> int:
        cur = self._conn.execute(
            """INSERT INTO books (title, author, isbn, year, category_id,
                                  language_id, total_copies, available_copies)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, author, isbn, year, category_id, language_id,
             total_copies, total_copies),
        )
        return cur.lastrowid

    def update(
        self,
        book_id: int,
        title: str,
        author: str,
        isbn: str | None,
        year: int | None,
        category_id: int | None,
        language_id: int | None,
        total_copies: int,
        available_copies: int,
    ) -> None:
        self._conn.execute(
            """UPDATE books
               SET title=?, author=?, isbn=?, year=?, category_id=?,
                   language_id=?, total_copies=?, available_copies=?
               WHERE id=?""",
            (title, author, isbn, year, category_id, language_id,
             total_copies, available_copies, book_id),
        )

    def adjust_available(self, book_id: int, delta: int) -> None:
        """Increment or decrement available_copies (used by loan flow)."""
        self._conn.execute(
            "UPDATE books SET available_copies = available_copies + ? "
            "WHERE id=?",
            (delta, book_id),
        )

    def delete(self, book_id: int) -> None:
        self._conn.execute("DELETE FROM loans WHERE book_id=?", (book_id,))
        self._conn.execute("DELETE FROM books WHERE id=?", (book_id,))

    def get(self, book_id: int) -> Book | None:
        row = self._conn.execute(
            "SELECT * FROM books WHERE id=?", (book_id,)
        ).fetchone()
        return Book.from_row(row) if row else None

    def list_all(
        self,
        search: str = "",
        category_id: int | None = None,
        language_id: int | None = None,
    ) -> list[Book]:
        sql = "SELECT * FROM books WHERE 1=1"
        params: list = []

        if search:
            like = f"%{search}%"
            sql += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
            params.extend([like, like, like])
        if category_id is not None:
            sql += " AND category_id = ?"
            params.append(category_id)
        if language_id is not None:
            sql += " AND language_id = ?"
            params.append(language_id)

        sql += " ORDER BY title"
        rows = self._conn.execute(sql, params).fetchall()
        return [Book.from_row(r) for r in rows]

    def list_with_details(
        self,
        search: str = "",
        category_id: int | None = None,
        language_id: int | None = None,
    ) -> list[BookWithDetails]:
        """List books with their category/language names in a single JOIN.

        Use this when rendering a list to the UI — avoids one extra lookup per
        row for category and language names.
        """
        sql = """SELECT books.*,
                        categories.name AS category_name,
                        languages.name  AS language_name
                 FROM books
                 LEFT JOIN categories ON categories.id = books.category_id
                 LEFT JOIN languages  ON languages.id  = books.language_id
                 WHERE 1=1"""
        params: list = []

        if search:
            like = f"%{search}%"
            sql += " AND (books.title LIKE ? OR books.author LIKE ? OR books.isbn LIKE ?)"
            params.extend([like, like, like])
        if category_id is not None:
            sql += " AND books.category_id = ?"
            params.append(category_id)
        if language_id is not None:
            sql += " AND books.language_id = ?"
            params.append(language_id)

        sql += " ORDER BY books.title"
        rows = self._conn.execute(sql, params).fetchall()
        return [BookWithDetails.from_row(r) for r in rows]

    def has_active_loans(self, book_id: int) -> int:
        """Return count of active loans for the book."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM loans "
            "WHERE book_id=? AND returned_on IS NULL",
            (book_id,),
        ).fetchone()
        return row["cnt"]
