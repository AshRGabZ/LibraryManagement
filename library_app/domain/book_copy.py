from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


# Status values — kept here as the single source of truth so service layer
# and UI both import them instead of repeating string literals.
STATUS_AVAILABLE = "available"
STATUS_BORROWED = "borrowed"
STATUS_LOST = "lost"
STATUS_DAMAGED = "damaged"

VALID_STATUSES = (STATUS_AVAILABLE, STATUS_BORROWED, STATUS_LOST, STATUS_DAMAGED)


@dataclass(frozen=True)
class BookCopy:
    """One physical copy of a book.

    Multiple copies of the same book share `book_id` but each has its own
    `serial_number` (printed on the label/spine) and its own `status`. This is the
    granularity at which loans are tracked.
    """

    id: int
    book_id: int
    serial_number: str
    status: str

    @property
    def is_available(self) -> bool:
        return self.status == STATUS_AVAILABLE

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "BookCopy":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            serial_number=row["serial_number"],
            status=row["status"],
        )


@dataclass(frozen=True)
class BookCopyWithBorrower(BookCopy):
    """Copy joined with its current borrower (if any) — for display.

    `borrower_name` / `borrower_due_on` are populated only when the copy is
    on active loan; for available/lost/damaged copies they're None.
    """

    borrower_name: str | None
    borrower_due_on: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "BookCopyWithBorrower":
        return cls(
            id=row["id"],
            book_id=row["book_id"],
            serial_number=row["serial_number"],
            status=row["status"],
            borrower_name=row["borrower_name"],
            borrower_due_on=row["borrower_due_on"],
        )
