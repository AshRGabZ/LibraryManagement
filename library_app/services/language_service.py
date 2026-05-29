from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import LanguageRepository
from ..domain import Language
from ..exceptions import ValidationError


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

    def get(self, language_id: int) -> Language | None:
        return LanguageRepository(self._db.connection).get(language_id)

    def list_all(self, search: str = "") -> list[Language]:
        return LanguageRepository(self._db.connection).list_all(search)

    def delete(self, language_id: int) -> None:
        with self._db.transaction() as conn:
            LanguageRepository(conn).delete(language_id)
