"""Sample-data seeder.

Populates the database with a diverse, realistic dataset so every part of the
UI has something to show: books spanning many genres and languages, members,
and loans in a spread of states (active, due-soon, overdue, returned, renewed).

It goes through the **service layer**, not raw SQL, so the same validation,
per-copy serial generation, and availability accounting that the live app
relies on runs here too — the seeded state is always internally consistent.

Idempotent by design: every entity is "get-or-create", so running it twice
won't duplicate categories/books/members. Loans are only seeded when the
database has very few, to avoid piling up on repeated runs.

Run standalone:
    python -m library_app.seed
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from .config import DB_PATH
from .data import Database
from .exceptions import LibraryError
from .services import Services


_log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Reference data
# --------------------------------------------------------------------------- #
CATEGORIES: list[str] = [
    "Fiction", "Science Fiction", "Fantasy", "Mystery", "Thriller",
    "Romance", "Historical Fiction", "Horror", "Biography", "History",
    "Science", "Philosophy", "Poetry", "Children", "Self-Help",
    "Technology", "Business", "Travel",
]

LANGUAGES: list[str] = [
    "English", "Spanish", "French", "German", "Hindi",
    "Tamil", "Mandarin", "Arabic", "Portuguese", "Japanese",
]

# (title, author, isbn, year, category, language, total_copies)
BOOKS: list[tuple] = [
    ("Foundation", "Isaac Asimov", "9780553293357", 1951, "Science Fiction", "English", 3),
    ("Dune", "Frank Herbert", "9780441172719", 1965, "Science Fiction", "English", 4),
    ("Neuromancer", "William Gibson", "9780441569595", 1984, "Science Fiction", "English", 2),
    ("The Hobbit", "J.R.R. Tolkien", "9780547928227", 1937, "Fantasy", "English", 5),
    ("A Game of Thrones", "George R.R. Martin", "9780553103540", 1996, "Fantasy", "English", 3),
    ("The Name of the Wind", "Patrick Rothfuss", "9780756404079", 2007, "Fantasy", "English", 2),
    ("Murder on the Orient Express", "Agatha Christie", "9780062693662", 1934, "Mystery", "English", 3),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "9780307454546", 2005, "Thriller", "English", 2),
    ("Gone Girl", "Gillian Flynn", "9780307588371", 2012, "Thriller", "English", 2),
    ("Pride and Prejudice", "Jane Austen", "9780141439518", 1813, "Romance", "English", 4),
    ("The Notebook", "Nicholas Sparks", "9780553816716", 1996, "Romance", "English", 2),
    ("The Pillars of the Earth", "Ken Follett", "9780451166890", 1989, "Historical Fiction", "English", 2),
    ("All the Light We Cannot See", "Anthony Doerr", "9781476746586", 2014, "Historical Fiction", "English", 3),
    ("Dracula", "Bram Stoker", "9780486411095", 1897, "Horror", "English", 2),
    ("The Shining", "Stephen King", "9780307743657", 1977, "Horror", "English", 3),
    ("Steve Jobs", "Walter Isaacson", "9781451648539", 2011, "Biography", "English", 2),
    ("Sapiens", "Yuval Noah Harari", "9780062316097", 2011, "History", "English", 4),
    ("A Brief History of Time", "Stephen Hawking", "9780553380163", 1988, "Science", "English", 3),
    ("The Selfish Gene", "Richard Dawkins", "9780198788607", 1976, "Science", "English", 2),
    ("Meditations", "Marcus Aurelius", "9780812968255", 180, "Philosophy", "English", 2),
    ("The Republic", "Plato", "9780140455113", None, "Philosophy", "English", 2),
    ("Leaves of Grass", "Walt Whitman", "9780143039556", 1855, "Poetry", "English", 1),
    ("The Very Hungry Caterpillar", "Eric Carle", "9780399226908", 1969, "Children", "English", 5),
    ("Atomic Habits", "James Clear", "9780735211292", 2018, "Self-Help", "English", 4),
    ("Clean Code", "Robert C. Martin", "9780132350884", 2008, "Technology", "English", 3),
    ("The Pragmatic Programmer", "Andrew Hunt", "9780201616224", 1999, "Technology", "English", 2),
    ("Cien años de soledad", "Gabriel García Márquez", "9780307474728", 1967, "Fiction", "Spanish", 3),
    ("Le Petit Prince", "Antoine de Saint-Exupéry", "9780156012195", 1943, "Children", "French", 4),
    ("Don Quijote", "Miguel de Cervantes", "9788424117306", 1605, "Fiction", "Spanish", 2),
    ("Gitanjali", "Rabindranath Tagore", None, 1910, "Poetry", "Hindi", 2),
]

# (name, email, phone) — phones are distinct 10-digit numbers
MEMBERS: list[tuple] = [
    ("Alice Johnson", "alice.johnson@example.com", "9876543210"),
    ("Bob Smith", "bob.smith@example.com", "9876501234"),
    ("Carol Williams", "carol.w@example.com", "9812345678"),
    ("David Brown", None, "9911223344"),
    ("Emma Davis", "emma.davis@example.com", "9765432108"),
    ("Frank Miller", "frank.m@example.com", "9123456780"),
    ("Grace Lee", None, "9988776655"),
    ("Henry Wilson", "henry.wilson@example.com", "9001234567"),
    ("Isabella Moore", "bella.moore@example.com", "9871234560"),
    ("Jack Taylor", None, "9456781230"),
    ("Karen Anderson", "karen.a@example.com", "9345678120"),
    ("Liam Thomas", "liam.t@example.com", "9234567810"),
]

# (member, book, days_ago_borrowed, loan_days, state)
#   state ∈ active | overdue | returned | renewed
LOAN_SCENARIOS: list[tuple] = [
    ("Alice Johnson", "Foundation", 3, 14, "active"),
    ("Alice Johnson", "Dune", 1, 21, "active"),
    ("Alice Johnson", "Sapiens", 30, 14, "overdue"),
    ("Alice Johnson", "The Hobbit", 15, 14, "renewed"),
    ("Bob Smith", "The Hobbit", 25, 14, "overdue"),
    ("Bob Smith", "Clean Code", 40, 14, "returned"),
    ("Carol Williams", "Atomic Habits", 5, 14, "active"),
    ("Carol Williams", "Gone Girl", 20, 7, "overdue"),
    ("David Brown", "A Game of Thrones", 10, 14, "renewed"),
    ("Emma Davis", "Pride and Prejudice", 2, 14, "active"),
    ("Emma Davis", "The Shining", 50, 14, "returned"),
    ("Frank Miller", "A Brief History of Time", 8, 14, "active"),
    ("Grace Lee", "Le Petit Prince", 18, 14, "overdue"),
    ("Henry Wilson", "Cien años de soledad", 6, 21, "active"),
    ("Isabella Moore", "The Name of the Wind", 12, 14, "renewed"),
    ("Jack Taylor", "Murder on the Orient Express", 35, 14, "returned"),
    ("Karen Anderson", "Steve Jobs", 4, 14, "active"),
    ("Liam Thomas", "Dune", 2, 14, "active"),
]


# --------------------------------------------------------------------------- #
#  Get-or-create helpers (idempotent)
# --------------------------------------------------------------------------- #
def _get_or_create_category(services: Services, name: str) -> int:
    for c in services.categories.list_all():
        if c.name == name:
            return c.id
    try:
        return services.categories.add(name)
    except LibraryError:
        for c in services.categories.list_all():
            if c.name == name:
                return c.id
        raise


def _get_or_create_language(services: Services, name: str) -> int:
    for l in services.languages.list_all():
        if l.name == name:
            return l.id
    try:
        return services.languages.add(name)
    except LibraryError:
        for l in services.languages.list_all():
            if l.name == name:
                return l.id
        raise


def _get_or_create_book(
    services: Services, title: str, author: str, isbn: str | None,
    year: int | None, category_id: int | None, language_id: int | None,
    copies: int,
) -> int | None:
    for b in services.books.list_all(search=title):
        if b.title == title and b.author == author:
            return b.id
    try:
        return services.books.add(
            title, author, isbn, year, category_id, language_id, copies
        )
    except LibraryError:
        # Likely a duplicate ISBN clash from a partial prior run — retry
        # without the ISBN, then fall back to a name lookup.
        try:
            return services.books.add(
                title, author, None, year, category_id, language_id, copies
            )
        except LibraryError:
            for b in services.books.list_all(search=title):
                if b.title == title:
                    return b.id
    return None


def _get_or_create_member(
    services: Services, name: str, email: str | None, phone: str | None
) -> int | None:
    for m in services.members.list_all(search=name):
        if m.name == name:
            return m.id
    try:
        return services.members.add(name, email, phone)
    except LibraryError:
        for m in services.members.list_all(search=name):
            if m.name == name:
                return m.id
    return None


# --------------------------------------------------------------------------- #
#  Seeding
# --------------------------------------------------------------------------- #
def seed_sample_data(services: Services, *, with_loans: bool = True) -> dict[str, int]:
    """Populate `services`' database with the sample dataset.

    Returns a count of rows created/ensured per entity. Safe to run repeatedly.
    """
    counts = {
        "categories": 0, "languages": 0, "books": 0, "members": 0,
        "loans": 0, "returned": 0, "renewed": 0, "overdue": 0, "active": 0,
    }

    cat_ids: dict[str, int] = {}
    for name in CATEGORIES:
        cat_ids[name] = _get_or_create_category(services, name)
        counts["categories"] += 1

    lang_ids: dict[str, int] = {}
    for name in LANGUAGES:
        lang_ids[name] = _get_or_create_language(services, name)
        counts["languages"] += 1

    book_ids: dict[str, int] = {}
    for title, author, isbn, year, cat, lang, copies in BOOKS:
        bid = _get_or_create_book(
            services, title, author, isbn, year,
            cat_ids.get(cat), lang_ids.get(lang), copies,
        )
        if bid is not None:
            book_ids[title] = bid
            counts["books"] += 1

    member_ids: dict[str, int] = {}
    for name, email, phone in MEMBERS:
        mid = _get_or_create_member(services, name, email, phone)
        if mid is not None:
            member_ids[name] = mid
            counts["members"] += 1

    if with_loans and len(services.loans.list_all()) < 3:
        _seed_loans(services, book_ids, member_ids, counts)

    return counts


def _seed_loans(
    services: Services,
    book_ids: dict[str, int],
    member_ids: dict[str, int],
    counts: dict[str, int],
) -> None:
    today = date.today()
    for member_name, book_title, days_ago, loan_days, state in LOAN_SCENARIOS:
        bid = book_ids.get(book_title)
        mid = member_ids.get(member_name)
        if bid is None or mid is None:
            continue
        borrowed_on = today - timedelta(days=days_ago)
        try:
            loan_id = services.loans.borrow(
                bid, mid, loan_days=loan_days, borrowed_on=borrowed_on
            )
        except LibraryError:
            # No copy available (a busy title) — skip this scenario.
            continue
        counts["loans"] += 1

        if state == "returned":
            try:
                services.loans.return_loan(loan_id)
                counts["returned"] += 1
            except LibraryError:
                pass
        elif state == "renewed":
            try:
                services.loans.renew(loan_id, extra_days=14)
                counts["renewed"] += 1
            except LibraryError:
                pass
        elif state == "overdue":
            counts["overdue"] += 1
        else:
            counts["active"] += 1


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    from .logging_setup import configure_logging

    configure_logging(DB_PATH.parent)
    db = Database(DB_PATH)
    try:
        services = Services.build(db)
        counts = seed_sample_data(services)
        print("Sample data seeded into:", DB_PATH)
        for key, val in counts.items():
            print(f"  {key:12} {val}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
