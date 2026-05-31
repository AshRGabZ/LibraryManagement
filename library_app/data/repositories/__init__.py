"""Repositories — raw CRUD operations returning domain entities."""

from .author_repository import AuthorRepository
from .book_copy_repository import BookCopyRepository
from .book_repository import BookRepository
from .category_repository import CategoryRepository
from .language_repository import LanguageRepository
from .loan_repository import LoanRepository
from .member_repository import MemberRepository

__all__ = [
    "AuthorRepository",
    "BookCopyRepository",
    "BookRepository",
    "CategoryRepository",
    "LanguageRepository",
    "LoanRepository",
    "MemberRepository",
]
