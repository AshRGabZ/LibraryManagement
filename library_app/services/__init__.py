"""Service layer — business logic, validation, and transaction boundaries.

Services accept a `Database` via DI and own the transaction boundary for each
business operation. They translate raw `sqlite3.IntegrityError` and similar
low-level errors into domain-specific exceptions defined in `exceptions.py`.
"""

from .author_service import AuthorService
from .book_service import BookService
from .category_service import CategoryService
from .container import Services
from .export_service import ExportService
from .import_service import (
    ImportResult,
    ImportService,
    MemberImportResult,
    ParsedMemberRow,
    ParsedRow,
)
from .label_service import LabelService
from .language_service import LanguageService
from .loan_service import LoanService
from .member_service import MemberService
from .notification_service import NotificationService
from .stats_service import StatsService

__all__ = [
    "AuthorService",
    "BookService",
    "CategoryService",
    "ExportService",
    "ImportResult",
    "ImportService",
    "LabelService",
    "MemberImportResult",
    "LanguageService",
    "LoanService",
    "MemberService",
    "NotificationService",
    "ParsedMemberRow",
    "ParsedRow",
    "Services",
    "StatsService",
]
