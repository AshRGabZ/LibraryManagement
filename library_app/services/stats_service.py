"""Analytics / metrics service.

All queries are SQL aggregates — no Python loops over rows. The dashboard
calls these methods directly; if the schema ever changes shape, only this
file moves.

Each method returns plain lists of tuples or dataclasses so the UI layer
doesn't need to know about sqlite3.Row.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..data import Database


@dataclass(frozen=True)
class OverallStats:
    total_books: int
    total_copies: int
    available_copies: int
    total_members: int
    total_loans: int
    active_loans: int
    overdue_loans: int


@dataclass(frozen=True)
class MonthlyLoans:
    month: str       # "YYYY-MM"
    count: int


@dataclass(frozen=True)
class RankedItem:
    name: str
    subtitle: str    # optional descriptor (e.g. author)
    count: int


class StatsService:
    """Read-only metrics from the loans/books/categories tables."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ----------------------------------------------------------- overall #

    def overall(self) -> OverallStats:
        c = self._db.connection
        return OverallStats(
            total_books=c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            total_copies=c.execute(
                "SELECT COALESCE(SUM(total_copies), 0) FROM books"
            ).fetchone()[0],
            available_copies=c.execute(
                "SELECT COALESCE(SUM(available_copies), 0) FROM books"
            ).fetchone()[0],
            total_members=c.execute("SELECT COUNT(*) FROM members").fetchone()[0],
            total_loans=c.execute("SELECT COUNT(*) FROM loans").fetchone()[0],
            active_loans=c.execute(
                "SELECT COUNT(*) FROM loans WHERE returned_on IS NULL"
            ).fetchone()[0],
            overdue_loans=c.execute(
                "SELECT COUNT(*) FROM loans "
                "WHERE returned_on IS NULL AND due_on < DATE('now')"
            ).fetchone()[0],
        )

    # ----------------------------------------------------------- trends  #

    def loans_per_month(self, months_back: int = 12) -> list[MonthlyLoans]:
        """Loan-start counts for the last N months (chronological order)."""
        rows = self._db.connection.execute(
            """
            SELECT strftime('%Y-%m', borrowed_on) AS month,
                   COUNT(*) AS cnt
            FROM loans
            WHERE borrowed_on >= DATE('now', ?)
            GROUP BY month
            ORDER BY month
            """,
            (f"-{months_back} months",),
        ).fetchall()
        return [MonthlyLoans(month=r["month"], count=r["cnt"]) for r in rows]

    # ----------------------------------------------------------- rankings #

    def most_borrowed_books(self, limit: int = 10) -> list[RankedItem]:
        rows = self._db.connection.execute(
            """
            SELECT books.title AS name,
                   COALESCE(authors.name, '') AS author,
                   COUNT(*) AS cnt
            FROM loans
            JOIN books ON books.id = loans.book_id
            LEFT JOIN authors ON authors.id = books.author_id
            GROUP BY loans.book_id
            ORDER BY cnt DESC, books.title
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [RankedItem(name=r["name"], subtitle=r["author"], count=r["cnt"])
                for r in rows]

    def most_borrowed_categories(self, limit: int = 10) -> list[RankedItem]:
        rows = self._db.connection.execute(
            """
            SELECT categories.name AS name, COUNT(*) AS cnt
            FROM loans
            JOIN books ON books.id = loans.book_id
            JOIN categories ON categories.id = books.category_id
            GROUP BY categories.id
            ORDER BY cnt DESC, categories.name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [RankedItem(name=r["name"], subtitle="", count=r["cnt"])
                for r in rows]

    def most_borrowed_languages(self, limit: int = 10) -> list[RankedItem]:
        rows = self._db.connection.execute(
            """
            SELECT languages.name AS name, COUNT(*) AS cnt
            FROM loans
            JOIN books ON books.id = loans.book_id
            JOIN languages ON languages.id = books.language_id
            GROUP BY languages.id
            ORDER BY cnt DESC, languages.name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [RankedItem(name=r["name"], subtitle="", count=r["cnt"])
                for r in rows]

    def top_borrowers(self, limit: int = 10) -> list[RankedItem]:
        rows = self._db.connection.execute(
            """
            SELECT members.name AS name, COUNT(*) AS cnt
            FROM loans
            JOIN members ON members.id = loans.member_id
            GROUP BY members.id
            ORDER BY cnt DESC, members.name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [RankedItem(name=r["name"], subtitle="", count=r["cnt"])
                for r in rows]
