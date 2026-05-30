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
    copy_id: int | None  # FK to book_copies.id; NULL for legacy loans

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
            copy_id=row["copy_id"] if "copy_id" in row.keys() else None,
        )


@dataclass(frozen=True)
class LoanWithDetails(Loan):
    """A loan joined with its book title, member name, and copy serial.

    `serial_number` is None only for legacy loans created before per-copy
    tracking landed (migration leaves their copy_id NULL if no copy could be
    assigned). The UI shows "—" in that case.
    """

    book_title: str
    member_name: str
    serial_number: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "LoanWithDetails":
        keys = row.keys()
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            member_id=row["member_id"],
            borrowed_on=row["borrowed_on"],
            due_on=row["due_on"],
            returned_on=row["returned_on"],
            renew_count=row["renew_count"],
            copy_id=row["copy_id"] if "copy_id" in keys else None,
            book_title=row["book_title"],
            member_name=row["member_name"],
            serial_number=row["serial_number"] if "serial_number" in keys else None,
        )
