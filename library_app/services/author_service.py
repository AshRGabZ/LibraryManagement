from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import AuthorRepository
from ..domain import Author
from ..exceptions import ValidationError


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

    def get(self, author_id: int) -> Author | None:
        return AuthorRepository(self._db.connection).get(author_id)

    def list_all(self, search: str = "") -> list[Author]:
        return AuthorRepository(self._db.connection).list_all(search)

    def delete(self, author_id: int) -> None:
        with self._db.transaction() as conn:
            AuthorRepository(conn).delete(author_id)
