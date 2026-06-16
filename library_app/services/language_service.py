from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import LanguageRepository
from ..domain import Language
from ..exceptions import NotFoundError, ValidationError


class LanguageService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("Language name is required.")
        try:
            with self._db.transaction() as conn:
                return LanguageRepository(conn).add(name)
        except sqlite3.IntegrityError:
            raise ValidationError(f"Language '{name}' already exists.")

    def rename(self, language_id: int, name: str) -> None:
        """Rename a language. Every book in it shows the new name automatically
        (books reference the language by id, not by stored name)."""
        name = name.strip()
        if not name:
            raise ValidationError("Language name is required.")
        try:
            with self._db.transaction() as conn:
                repo = LanguageRepository(conn)
                if repo.get(language_id) is None:
                    raise NotFoundError(f"Language #{language_id} not found.")
                repo.update(language_id, name)
        except sqlite3.IntegrityError:
            raise ValidationError(
                f"Another language named '{name}' already exists."
            )

    def get(self, language_id: int) -> Language | None:
        return LanguageRepository(self._db.connection).get(language_id)

    def list_all(self, search: str = "") -> list[Language]:
        return LanguageRepository(self._db.connection).list_all(search)

    def delete(self, language_id: int) -> None:
        with self._db.transaction() as conn:
            LanguageRepository(conn).delete(language_id)
