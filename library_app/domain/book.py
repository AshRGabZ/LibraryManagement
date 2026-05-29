from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    isbn: str | None
    year: int | None
    category_id: int | None
    language_id: int | None
    total_copies: int
    available_copies: int

    @property
    def is_available(self) -> bool:
        return self.available_copies > 0

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Book":
        return cls(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            isbn=row["isbn"],
            year=row["year"],
            category_id=row["category_id"],
            language_id=row["language_id"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
        )


@dataclass(frozen=True)
class BookWithDetails(Book):
    """A book joined with its category and language names — for display.

    Eliminates N+1 queries in the UI: the JOIN happens server-side instead of
    one `SELECT * FROM categories WHERE id=?` per row.
    """

    category_name: str | None
    language_name: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "BookWithDetails":
        return cls(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            isbn=row["isbn"],
            year=row["year"],
            category_id=row["category_id"],
            language_id=row["language_id"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
            category_name=row["category_name"],
            language_name=row["language_name"],
        )
