from __future__ import annotations

import sqlite3

from ..data import Database
from ..data.repositories import CategoryRepository
from ..domain import Category
from ..exceptions import ValidationError


class CategoryService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("Category name is required.")
        try:
            with self._db.transaction() as conn:
                return CategoryRepository(conn).add(name)
        except sqlite3.IntegrityError:
            raise ValidationError(f"Category '{name}' already exists.")

    def get(self, category_id: int) -> Category | None:
        return CategoryRepository(self._db.connection).get(category_id)

    def list_all(self, search: str = "") -> list[Category]:
        return CategoryRepository(self._db.connection).list_all(search)

    def delete(self, category_id: int) -> None:
        with self._db.transaction() as conn:
            CategoryRepository(conn).delete(category_id)
