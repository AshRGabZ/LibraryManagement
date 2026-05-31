"""Domain entities — pure data classes with no persistence concerns."""

from .author import Author
from .book import Book, BookWithDetails
from .book_copy import BookCopy, BookCopyWithBorrower
from .category import Category
from .language import Language
from .loan import Loan, LoanWithDetails
from .member import Member

__all__ = [
    "Author",
    "Book",
    "BookCopy",
    "BookCopyWithBorrower",
    "BookWithDetails",
    "Category",
    "Language",
    "Loan",
    "LoanWithDetails",
    "Member",
]
