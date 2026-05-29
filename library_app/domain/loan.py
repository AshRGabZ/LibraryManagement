from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


@dataclass(frozen=True)
class Loan:
    id: int
    book_id: int
    member_id: int
    borrowed_on: str  # ISO date string
    due_on: str | None
    returned_on: str | None
    renew_count: int

    @property
    def is_returned(self) -> bool:
        return self.returned_on is not None

    @property
    def is_overdue(self) -> bool:
        if self.is_returned or not self.due_on:
            return False
        return date.fromisoformat(self.due_on) < date.today()

    @property
    def days_left(self) -> int | None:
        """Days until due. Negative if overdue. None if returned/no due date."""
        if self.is_returned or not self.due_on:
            return None
        return (date.fromisoformat(self.due_on) - date.today()).days

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Loan":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            member_id=row["member_id"],
            borrowed_on=row["borrowed_on"],
            due_on=row["due_on"],
            returned_on=row["returned_on"],
            renew_count=row["renew_count"],
        )


@dataclass(frozen=True)
class LoanWithDetails(Loan):
    """A loan joined with its book title and member name — for display."""

    book_title: str
    member_name: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "LoanWithDetails":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            member_id=row["member_id"],
            borrowed_on=row["borrowed_on"],
            due_on=row["due_on"],
            returned_on=row["returned_on"],
            renew_count=row["renew_count"],
            book_title=row["book_title"],
            member_name=row["member_name"],
        )
