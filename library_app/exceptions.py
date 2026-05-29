"""Domain-specific exceptions.

A dedicated hierarchy lets the UI catch only library-specific failures and
present them as friendly messages, while letting unexpected programming errors
bubble up to the crash handler.
"""
from __future__ import annotations


class LibraryError(Exception):
    """Base class for all expected, user-facing library errors."""


class NotFoundError(LibraryError):
    """A requested entity does not exist."""


class ValidationError(LibraryError):
    """User input failed validation rules."""


class BookNotAvailableError(LibraryError):
    """All copies of a book are currently borrowed."""


class LoanAlreadyReturnedError(LibraryError):
    """Cannot operate on a loan that has already been returned."""


class MaxRenewalsReachedError(LibraryError):
    """A loan has reached its renewal limit."""


class ActiveLoansError(LibraryError):
    """Cannot delete a book/member with active loans."""
