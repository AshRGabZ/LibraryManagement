from __future__ import annotations

from datetime import date, timedelta

from ..config import DEFAULT_LOAN_DAYS, DEFAULT_RENEW_DAYS, MAX_RENEWALS
from ..data import Database
from ..data.repositories import BookCopyRepository, BookRepository, LoanRepository
from ..domain import Loan, LoanWithDetails
from ..domain.book_copy import STATUS_AVAILABLE, STATUS_BORROWED
from ..exceptions import (
    BookNotAvailableError,
    LoanAlreadyReturnedError,
    MaxRenewalsReachedError,
    NotFoundError,
    ValidationError,
)


class LoanService:
    """Borrow / return / renew operations.

    Each method is a transaction boundary: the loan record and the book's
    available_copies counter are always updated together. This guarantees the
    invariant `sum(active loans for book) = total - available`.
    """

    DEFAULT_LOAN_DAYS = DEFAULT_LOAN_DAYS
    MAX_RENEWALS = MAX_RENEWALS
    DEFAULT_RENEW_DAYS = DEFAULT_RENEW_DAYS

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------- borrow #

    def borrow(
        self,
        book_id: int,
        member_id: int,
        loan_days: int = DEFAULT_LOAN_DAYS,
        borrowed_on: date | None = None,
        copy_id: int | None = None,
    ) -> int:
        """Borrow a book. If `copy_id` is None, auto-assign the lowest-numbered
        available copy. Pass a specific `copy_id` to honor a librarian's
        choice (e.g. they scanned a barcode)."""
        if loan_days <= 0:
            raise ValidationError("Loan period must be positive.")

        if borrowed_on is None:
            borrowed_on = date.today()
        if borrowed_on > date.today():
            raise ValidationError("Borrowed date cannot be in the future.")

        due_on = borrowed_on + timedelta(days=loan_days)

        with self._db.transaction() as conn:
            book_repo = BookRepository(conn)
            loan_repo = LoanRepository(conn)
            copy_repo = BookCopyRepository(conn)

            book = book_repo.get(book_id)
            if book is None:
                raise NotFoundError(f"Book #{book_id} not found.")
            if book.available_copies <= 0:
                raise BookNotAvailableError("No copies available for this book.")

            # Resolve the physical copy. Either honor the caller's choice
            # (verifying it's both for this book and currently available) or
            # pick the lowest-id available one.
            if copy_id is not None:
                copy = copy_repo.get(copy_id)
                if copy is None or copy.book_id != book_id:
                    raise ValidationError(
                        f"Copy #{copy_id} is not a copy of this book."
                    )
                if not copy.is_available:
                    raise BookNotAvailableError(
                        f"Copy {copy.serial_number} is already on loan."
                    )
            else:
                copy = copy_repo.find_available(book_id)
                if copy is None:
                    # Inconsistency between counter and copies — fail loud
                    # rather than silently double-issue.
                    raise BookNotAvailableError(
                        "No available copy found despite the book's counter "
                        "saying one should exist. The data may need repair."
                    )

            loan_id = loan_repo.add(
                book_id, member_id,
                borrowed_on.isoformat(), due_on.isoformat(),
                copy_id=copy.id,
            )
            copy_repo.set_status(copy.id, STATUS_BORROWED)
            book_repo.adjust_available(book_id, -1)
            return loan_id

    # ------------------------------------------------------------- return #

    def return_loan(self, loan_id: int) -> None:
        with self._db.transaction() as conn:
            loan_repo = LoanRepository(conn)
            book_repo = BookRepository(conn)
            copy_repo = BookCopyRepository(conn)

            loan = loan_repo.get(loan_id)
            if loan is None:
                raise NotFoundError(f"Loan #{loan_id} not found.")
            if loan.is_returned:
                raise LoanAlreadyReturnedError(
                    "This loan has already been returned."
                )

            loan_repo.mark_returned(loan_id, date.today().isoformat())
            # Free the specific copy. Skip if loan has no copy_id (legacy
            # loan from before per-copy tracking).
            if loan.copy_id is not None:
                copy_repo.set_status(loan.copy_id, STATUS_AVAILABLE)
            book_repo.adjust_available(loan.book_id, +1)

    # ------------------------------------------------------------- renew  #

    def renew(self, loan_id: int, extra_days: int = DEFAULT_LOAN_DAYS) -> date:
        if extra_days <= 0:
            raise ValidationError("Renewal days must be positive.")

        with self._db.transaction() as conn:
            loan_repo = LoanRepository(conn)
            loan = loan_repo.get(loan_id)
            if loan is None:
                raise NotFoundError(f"Loan #{loan_id} not found.")
            if loan.is_returned:
                raise LoanAlreadyReturnedError("Cannot renew a returned loan.")
            if loan.renew_count >= self.MAX_RENEWALS:
                raise MaxRenewalsReachedError(
                    f"Maximum renewals ({self.MAX_RENEWALS}) reached."
                )

            current_due = (
                date.fromisoformat(loan.due_on) if loan.due_on else date.today()
            )
            base = max(current_due, date.today())
            new_due = base + timedelta(days=extra_days)
            loan_repo.extend_due(loan_id, new_due.isoformat())
            return new_due

    # ------------------------------------------------------------- reads  #

    def get(self, loan_id: int) -> LoanWithDetails | None:
        return LoanRepository(self._db.connection).get_with_details(loan_id)

    def list_all(
        self,
        active_only: bool = False,
        search: str = "",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[LoanWithDetails]:
        """List loans with optional filters.

        `from_date` / `to_date` filter by `borrowed_on` (inclusive). Use this
        to answer "how many books were transacted in this window".
        """
        return LoanRepository(self._db.connection).list_all(
            active_only=active_only,
            search=search,
            from_date=from_date.isoformat() if from_date else None,
            to_date=to_date.isoformat() if to_date else None,
        )
