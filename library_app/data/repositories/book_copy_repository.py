from __future__ import annotations

import re
import sqlite3

from ...domain import BookCopy
from ...domain.book_copy import (
    BookCopyWithBorrower,
    STATUS_AVAILABLE,
    STATUS_BORROWED,
)


class BookCopyRepository:
    """CRUD over physical copies. The `book_copies` table is the source of
    truth for per-copy state; the counter on `books` is just a denormalized
    cache for fast availability queries."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------ create  #

    def add(self, book_id: int, serial_number: str,
            status: str = STATUS_AVAILABLE) -> int:
        cur = self._conn.execute(
            "INSERT INTO book_copies (book_id, serial_number, status) "
            "VALUES (?, ?, ?)",
            (book_id, serial_number, status),
        )
        return cur.lastrowid

    # ------------------------------------------------------------ reads   #

    def list_for_book(self, book_id: int) -> list[BookCopy]:
        rows = self._conn.execute(
            "SELECT * FROM book_copies WHERE book_id=? ORDER BY id",
            (book_id,),
        ).fetchall()
        return [BookCopy.from_row(r) for r in rows]

    def count_for_book(self, book_id: int) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM book_copies WHERE book_id=?",
            (book_id,),
        ).fetchone()["cnt"]

    def get(self, copy_id: int) -> BookCopy | None:
        row = self._conn.execute(
            "SELECT * FROM book_copies WHERE id=?", (copy_id,)
        ).fetchone()
        return BookCopy.from_row(row) if row else None

    def find_available(self, book_id: int) -> BookCopy | None:
        """Return the lowest-id available copy of a book, or None.

        Lowest id == lowest serial in our default scheme, which gives stable,
        predictable copy assignment ("you'll get -01 first, then -02…").
        """
        row = self._conn.execute(
            "SELECT * FROM book_copies WHERE book_id=? AND status=? "
            "ORDER BY id LIMIT 1",
            (book_id, STATUS_AVAILABLE),
        ).fetchone()
        return BookCopy.from_row(row) if row else None

    def list_available_for_book(self, book_id: int) -> list[BookCopy]:
        """Available copies in serial order — used to populate copy pickers."""
        rows = self._conn.execute(
            "SELECT * FROM book_copies WHERE book_id=? AND status=? "
            "ORDER BY id",
            (book_id, STATUS_AVAILABLE),
        ).fetchall()
        return [BookCopy.from_row(r) for r in rows]

    # ------------------------------------------------------------ writes  #

    def set_status(self, copy_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE book_copies SET status=? WHERE id=?",
            (status, copy_id),
        )

    def update_serial(self, copy_id: int, new_serial: str) -> None:
        """Rename a copy. The UNIQUE constraint on `serial_number` enforces
        uniqueness; service layer translates the IntegrityError to a
        ValidationError with a friendly message."""
        self._conn.execute(
            "UPDATE book_copies SET serial_number=? WHERE id=?",
            (new_serial, copy_id),
        )

    def delete(self, copy_id: int) -> None:
        self._conn.execute("DELETE FROM book_copies WHERE id=?", (copy_id,))

    # ---------------------------------------------------- joined queries  #

    def list_with_borrower(self, book_id: int) -> list[BookCopyWithBorrower]:
        """All copies of a book joined with the current borrower (if any).

        Single query — used by the Books tab to render copies under each
        book and by the Admin "Manage Copies" dialog.
        """
        rows = self._conn.execute(
            """SELECT bc.*,
                      m.name      AS borrower_name,
                      l.due_on    AS borrower_due_on
               FROM book_copies bc
               LEFT JOIN loans   l ON l.copy_id = bc.id
                                  AND l.returned_on IS NULL
               LEFT JOIN members m ON m.id = l.member_id
               WHERE bc.book_id = ?
               ORDER BY bc.id""",
            (book_id,),
        ).fetchall()
        return [BookCopyWithBorrower.from_row(r) for r in rows]

    # ------------------------------------------------------------ sync    #

    # Default serial pattern is "B<book_id>-<NN>". This regex pulls back the
    # numeric suffix so we can find "the highest -NN ever used for this book".
    _SERIAL_SUFFIX_RE = re.compile(r"-(\d+)\s*$")

    def _next_serial_suffix(self, book_id: int) -> int:
        """Return the next unused -NN suffix for this book.

        "Highest existing + 1", NOT "count + 1". The difference matters when
        copies have been deleted from the middle of the range — e.g. you
        reduced from 5 to 3 while B1-02 and B1-04 were on loan, so the
        remaining set is {B1-01, B1-02, B1-04}. Using count+1 would try to
        create B1-04 (collision); using max+1 creates B1-05 (safe). It also
        gives "never reuse" semantics, which is how libraries actually treat
        physical accession numbers — a label that's gone is gone.
        """
        rows = self._conn.execute(
            "SELECT serial_number FROM book_copies WHERE book_id=?",
            (book_id,),
        ).fetchall()
        max_suffix = 0
        for r in rows:
            m = self._SERIAL_SUFFIX_RE.search(r["serial_number"])
            if m:
                n = int(m.group(1))
                if n > max_suffix:
                    max_suffix = n
        return max_suffix + 1

    def sync_count(self, book_id: int, target: int) -> None:
        """Bring this book's copy count to `target`.

        - If fewer than target → create new copies starting from
          (max existing suffix + 1). Serials are never reused.
        - If more than target → remove the highest-numbered AVAILABLE copies.
          Raises ValueError if there aren't enough available copies to drop
          (caller — `BookService.update` — pre-validates this with a clearer
          error).
        """
        current = self.count_for_book(book_id)
        if current < target:
            to_add = target - current
            next_n = self._next_serial_suffix(book_id)
            for n in range(next_n, next_n + to_add):
                self.add(book_id, f"B{book_id}-{n:02d}")
        elif current > target:
            to_remove = current - target
            removable = self._conn.execute(
                "SELECT id FROM book_copies "
                "WHERE book_id=? AND status=? "
                "ORDER BY id DESC LIMIT ?",
                (book_id, STATUS_AVAILABLE, to_remove),
            ).fetchall()
            if len(removable) < to_remove:
                raise ValueError(
                    f"Cannot reduce total copies — only {len(removable)} of "
                    f"the {to_remove} extra copies are available to remove."
                )
            for r in removable:
                self.delete(r["id"])
