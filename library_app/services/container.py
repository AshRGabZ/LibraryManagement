"""Service container — a typed bundle of all services for DI.

Passing a single `Services` object to UI components beats threading five
service arguments through every constructor. It also gives us one place to add
cross-cutting wiring (logging, caching) without touching call sites.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data import Database
from .book_service import BookService
from .category_service import CategoryService
from .export_service import ExportService
from .language_service import LanguageService
from .loan_service import LoanService
from .member_service import MemberService
from .notification_service import NotificationService
from .stats_service import StatsService


@dataclass(frozen=True)
class Services:
    books: BookService
    members: MemberService
    loans: LoanService
    categories: CategoryService
    languages: LanguageService
    stats: StatsService
    notify: NotificationService
    export: type[ExportService]  # stateless — pass the class itself

    @classmethod
    def build(cls, db: Database) -> "Services":
        """Wire up all services with a single database instance."""
        return cls(
            books=BookService(db),
            members=MemberService(db),
            loans=LoanService(db),
            categories=CategoryService(db),
            languages=LanguageService(db),
            stats=StatsService(db),
            notify=NotificationService(),
            export=ExportService,
        )
