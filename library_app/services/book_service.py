from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import BookCopyRepository, BookRepository
from ..domain import Book, BookCopy, BookCopyWithBorrower, BookWithDetails
from ..exceptions import (
    ActiveLoansError,
    NotFoundError,
    ValidationError,
)


class BookService:
    """Business operations for books — validation, capacity rules, deletion."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # -------------------------------------------------------------- writes #

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
        title, author = title.strip(), author.strip()
        if not title:
            raise ValidationError("Title is required.")
        if not author:
            raise ValidationError("Author is required.")
        if total_copies < 1:
            raise ValidationError("Total copies must be at least 1.")

        try:
            with self._db.transaction() as conn:
                book_id = BookRepository(conn).add(
                    title, author, isbn or None, year,
                    category_id, language_id, total_copies,
                )
                # Create one row per physical copy. Serials are auto-generated
                # by sync_count → B<book_id>-01, B<book_id>-02, …
                BookCopyRepository(conn).sync_count(book_id, total_copies)
                return book_id
        except sqlite3.IntegrityError as e:
            if "isbn" in str(e).lower():
                raise ValidationError(f"A book with ISBN '{isbn}' already exists.")
            raise

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
    ) -> None:
        title, author = title.strip(), author.strip()
        if not title:
            raise ValidationError("Title is required.")
        if not author:
            raise ValidationError("Author is required.")

        with self._db.transaction() as conn:
            repo = BookRepository(conn)
            copies_repo = BookCopyRepository(conn)
            existing = repo.get(book_id)
            if existing is None:
                raise NotFoundError(f"Book #{book_id} not found.")

            loaned_out = existing.total_copies - existing.available_copies
            if total_copies < loaned_out:
                raise ValidationError(
                    f"Cannot set total copies below {loaned_out} "
                    f"(that many are currently borrowed)."
                )
            new_available = total_copies - loaned_out

            try:
                repo.update(
                    book_id, title, author, isbn or None, year,
                    category_id, language_id, total_copies, new_available,
                )
                # Reconcile physical copies with the new total. sync_count
                # only removes *available* copies; the check above ensures we
                # don't try to remove more than that.
                copies_repo.sync_count(book_id, total_copies)
            except sqlite3.IntegrityError as e:
                if "isbn" in str(e).lower():
                    raise ValidationError(
                        f"A book with ISBN '{isbn}' already exists."
                    )
                raise

    def delete(self, book_id: int) -> None:
        with self._db.transaction() as conn:
            repo = BookRepository(conn)
            book = repo.get(book_id)
            if book is None:
                raise NotFoundError(f"Book #{book_id} not found.")
            active = repo.has_active_loans(book_id)
            if active > 0:
                raise ActiveLoansError(
                    f"'{book.title}' has {active} active loan(s). "
                    "Please ensure all copies are returned first."
                )
            repo.delete(book_id)

    # -------------------------------------------------------------- reads  #

    def get(self, book_id: int) -> Book | None:
        return BookRepository(self._db.connection).get(book_id)

    def list_all(
        self,
        search: str = "",
        category_id: int | None = None,
        language_id: int | None = None,
    ) -> list[Book]:
        return BookRepository(self._db.connection).list_all(
            search=search, category_id=category_id, language_id=language_id
        )

    def list_with_details(
        self,
        search: str = "",
        category_id: int | None = None,
        language_id: int | None = None,
    ) -> list[BookWithDetails]:
        """Books joined with category/language names — single SQL query.

        Prefer this in UI code over `list_all()` + per-row name lookups.
        """
        return BookRepository(self._db.connection).list_with_details(
            search=search, category_id=category_id, language_id=language_id
        )

    def list_copies(self, book_id: int) -> list[BookCopy]:
        """Every physical copy of a book, in serial order."""
        return BookCopyRepository(self._db.connection).list_for_book(book_id)

    def get_copy(self, copy_id: int) -> BookCopy | None:
        """Fetch one copy by id — used by the label preview to look up the
        serial without round-tripping through the parent book."""
        return BookCopyRepository(self._db.connection).get(copy_id)

    def list_copies_with_borrower(
        self, book_id: int
    ) -> list[BookCopyWithBorrower]:
        """Copies joined with the current borrower (single SQL query)."""
        return BookCopyRepository(self._db.connection).list_with_borrower(book_id)

    def update_copy_serial(self, copy_id: int, new_serial: str) -> None:
        """Rename one physical copy.

        Validates: non-empty + unique. The UNIQUE constraint at the DB level
        still catches a race in a future multi-user scenario; we translate
        either layer's error to a friendly ValidationError.
        """
        new_serial = new_serial.strip()
        if not new_serial:
            raise ValidationError("Serial number cannot be empty.")
        try:
            with self._db.transaction() as conn:
                repo = BookCopyRepository(conn)
                copy = repo.get(copy_id)
                if copy is None:
                    raise NotFoundError(f"Copy #{copy_id} not found.")
                if new_serial == copy.serial_number:
                    return  # no-op
                repo.update_serial(copy_id, new_serial)
        except sqlite3.IntegrityError:
            raise ValidationError(
                f"Serial '{new_serial}' is already in use by another copy."
            )
