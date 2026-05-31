from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author_id: int | None
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
            author_id=row["author_id"],
            isbn=row["isbn"],
            year=row["year"],
            category_id=row["category_id"],
            language_id=row["language_id"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
        )


@dataclass(frozen=True)
class BookWithDetails(Book):
    """A book joined with its author, category and language names — for display.

    Eliminates N+1 queries in the UI: the JOINs happen server-side instead of
    one `SELECT … WHERE id=?` per row for each related entity.
    """

    author_name: str | None
    category_name: str | None
    language_name: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "BookWithDetails":
        return cls(
            id=row["id"],
            title=row["title"],
            author_id=row["author_id"],
            isbn=row["isbn"],
            year=row["year"],
            category_id=row["category_id"],
            language_id=row["language_id"],
            total_copies=row["total_copies"],
            available_copies=row["available_copies"],
            author_name=row["author_name"],
            category_name=row["category_name"],
            language_name=row["language_name"],
        )
