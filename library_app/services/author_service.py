from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import AuthorRepository
from ..domain import Author
from ..exceptions import NotFoundError, ValidationError


class AuthorService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("Author name is required.")
        try:
            with self._db.transaction() as conn:
                return AuthorRepository(conn).add(name)
        except sqlite3.IntegrityError:
            raise ValidationError(f"Author '{name}' already exists.")

    def rename(self, author_id: int, name: str) -> None:
        """Rename an author. Because books reference the author by id, every
        book by this author automatically shows the new name — no per-book
        update needed."""
        name = name.strip()
        if not name:
            raise ValidationError("Author name is required.")
        try:
            with self._db.transaction() as conn:
                repo = AuthorRepository(conn)
                if repo.get(author_id) is None:
                    raise NotFoundError(f"Author #{author_id} not found.")
                repo.update(author_id, name)
        except sqlite3.IntegrityError:
            raise ValidationError(
                f"Another author named '{name}' already exists."
            )

    def get(self, author_id: int) -> Author | None:
        return AuthorRepository(self._db.connection).get(author_id)

    def list_all(self, search: str = "") -> list[Author]:
        return AuthorRepository(self._db.connection).list_all(search)

    def delete(self, author_id: int) -> None:
        with self._db.transaction() as conn:
            AuthorRepository(conn).delete(author_id)
