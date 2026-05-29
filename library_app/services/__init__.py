"""Service layer — business logic, validation, and transaction boundaries.

Services accept a `Database` via DI and own the transaction boundary for each
business operation. They translate raw `sqlite3.IntegrityError` and similar
low-level errors into domain-specific exceptions defined in `exceptions.py`.
"""

from .book_service import BookService
from .category_service import CategoryService
from .container import Services
from .export_service import ExportService
from .language_service import LanguageService
from .loan_service import LoanService
from .member_service import MemberService
from .notification_service import NotificationService
from .stats_service import StatsService

__all__ = [
    "BookService",
    "CategoryService",
    "ExportService",
    "LanguageService",
    "LoanService",
    "MemberService",
    "NotificationService",
    "Services",
    "StatsService",
]
