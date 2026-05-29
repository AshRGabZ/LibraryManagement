from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import BookRepository
from ..domain import Book, BookWithDetails
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
                return BookRepository(conn).add(
                    title, author, isbn or None, year,
                    category_id, language_id, total_copies,
                )
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
