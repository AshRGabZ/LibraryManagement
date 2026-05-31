"""Service container — a typed bundle of all services for DI.

Passing a single `Services` object to UI components beats threading five
service arguments through every constructor. It also gives us one place to add
cross-cutting wiring (logging, caching) without touching call sites.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data import Database
from .author_service import AuthorService
from .book_service import BookService
from .category_service import CategoryService
from .export_service import ExportService
from .import_service import ImportService
from .language_service import LanguageService
from .loan_service import LoanService
from .member_service import MemberService
from .label_service import LabelService
from .notification_service import NotificationService
from .stats_service import StatsService


@dataclass(frozen=True)
class Services:
    books: BookService
    members: MemberService
    loans: LoanService
    categories: CategoryService
    languages: LanguageService
    authors: AuthorService
    stats: StatsService
    notify: NotificationService
    label: LabelService
    export: type[ExportService]  # stateless — pass the class itself
    importer: ImportService

    @classmethod
    def build(cls, db: Database) -> "Services":
        """Wire up all services with a single database instance."""
        books = BookService(db)
        categories = CategoryService(db)
        languages = LanguageService(db)
        authors = AuthorService(db)
        members = MemberService(db)
        return cls(
            books=books,
            members=members,
            loans=LoanService(db),
            categories=categories,
            languages=languages,
            authors=authors,
            stats=StatsService(db),
            notify=NotificationService(),
            label=LabelService(),
            export=ExportService,
            # The importer composes the book/category/language/author/member
            # services so it can resolve-or-create names and insert through the
            # same validation rules as the rest of the app.
            importer=ImportService(books, categories, languages, authors, members),
        )
