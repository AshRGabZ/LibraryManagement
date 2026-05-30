"""Bulk-import books from a spreadsheet (.xlsx or .csv).

Mirrors :class:`ExportService` on the read side. The flow is deliberately two
phase so the UI can show a preview before anything is written:

    rows = service.parse_file(path)   # read + validate, NO DB writes
    result = service.import_rows(rows) # insert the valid rows

`.xlsx` parsing needs the optional ``openpyxl`` package (same dependency as
export); `.csv` works on the standard library alone. Category and language are
matched by name (case-insensitive) and **auto-created** when missing, so a
spreadsheet can introduce new ones in a single pass.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..exceptions import LibraryError
from .book_service import BookService
from .category_service import CategoryService
from .language_service import LanguageService


_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedRow:
    """One spreadsheet data row after mapping + validation.

    `row_num` is the 1-based line number in the source file (header = 1), so
    error messages point the user at the right row. `error` is ``None`` when
    the row is importable.
    """

    row_num: int
    title: str
    author: str
    isbn: str | None
    year: int | None
    category: str | None
    language: str | None
    total_copies: int
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class ImportResult:
    """Outcome summary returned to the UI after an import run."""

    added: int
    errors: list[tuple[int, str]]          # (row_num, message)
    created_categories: list[str]
    created_languages: list[str]

    @property
    def failed(self) -> int:
        return len(self.errors)


class ImportService:
    """Read a spreadsheet of books and insert them via the book service."""

    #: Columns written to a downloadable template (also the canonical order).
    TEMPLATE_HEADERS: tuple[str, ...] = (
        "Title", "Author", "ISBN", "Year", "Category", "Language", "Copies",
    )

    #: Example rows shown in the template so the format is self-explanatory.
    _TEMPLATE_EXAMPLE: tuple[tuple, ...] = (
        ("The Pilgrim's Progress", "John Bunyan", "9780141439297", 1678,
         "Classics", "English", 2),
        ("Mere Christianity", "C. S. Lewis", "", 1952, "Theology", "English", 1),
    )

    #: Accepted header spellings → canonical field. Matched case-insensitively.
    _HEADER_ALIASES: dict[str, set[str]] = {
        "title": {"title", "book title", "name"},
        "author": {"author", "authors", "writer", "by"},
        "isbn": {"isbn", "isbn13", "isbn-13", "isbn 13", "isbn10"},
        "year": {"year", "published", "publication year", "pub year"},
        "category": {"category", "categories", "genre", "subject"},
        "language": {"language", "languages", "lang"},
        "copies": {"copies", "total copies", "quantity", "qty", "count",
                   "no of copies", "number of copies", "stock"},
    }

    def __init__(
        self,
        books: BookService,
        categories: CategoryService,
        languages: LanguageService,
    ) -> None:
        self._books = books
        self._categories = categories
        self._languages = languages

    # ------------------------------------------------------------- parse  #

    def parse_file(self, path: Path) -> list[ParsedRow]:
        """Read + validate `path`. Raises ValueError for unusable files."""
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            raw = self._read_xlsx(path)
        elif suffix in (".csv", ".txt"):
            raw = self._read_csv(path)
        else:
            raise ValueError(
                f"Unsupported file type '{suffix}'. Use .xlsx or .csv."
            )

        if not raw:
            raise ValueError("The file is empty.")

        col = self._map_headers(raw[0])
        if "title" not in col or "author" not in col:
            raise ValueError(
                "The first row must contain at least 'Title' and 'Author' "
                "column headers."
            )

        rows: list[ParsedRow] = []
        for line_no, raw_row in enumerate(raw[1:], start=2):
            if self._is_blank(raw_row):
                continue  # skip trailing/empty rows silently
            rows.append(self._parse_row(line_no, raw_row, col))
        if not rows:
            raise ValueError("No data rows found below the header.")
        return rows

    # ------------------------------------------------------------- import #

    def import_rows(self, rows: Sequence[ParsedRow]) -> ImportResult:
        """Insert the valid rows; auto-create missing categories/languages.

        Invalid rows (and any that fail at insert time, e.g. duplicate ISBN)
        are collected into `errors` — the import is best-effort, not
        all-or-nothing, so one bad row never blocks the rest.
        """
        cat_map = {c.name.lower(): c.id for c in self._categories.list_all()}
        lang_map = {l.name.lower(): l.id for l in self._languages.list_all()}
        created_cats: list[str] = []
        created_langs: list[str] = []
        added = 0
        errors: list[tuple[int, str]] = []

        for r in rows:
            if not r.is_valid:
                errors.append((r.row_num, r.error or "Invalid row"))
                continue
            try:
                cat_id = self._get_or_create(
                    r.category, cat_map, created_cats, self._categories
                )
                lang_id = self._get_or_create(
                    r.language, lang_map, created_langs, self._languages
                )
                self._books.add(
                    r.title, r.author, r.isbn, r.year,
                    cat_id, lang_id, r.total_copies,
                )
                added += 1
            except LibraryError as e:
                errors.append((r.row_num, str(e)))
            except Exception as e:  # pragma: no cover - defensive
                _log.exception("Unexpected error importing row %d", r.row_num)
                errors.append((r.row_num, str(e)))

        _log.info("Import finished: %d added, %d failed", added, len(errors))
        return ImportResult(added, errors, created_cats, created_langs)

    # ------------------------------------------------------------ template #

    @classmethod
    def write_template(cls, path: Path) -> Path:
        """Write a starter file (headers + two example rows). Returns the path
        actually written (falls back to .csv if .xlsx is asked for without
        openpyxl)."""
        if path.suffix.lower() == ".xlsx":
            written = cls._write_template_xlsx(path)
            if written is not None:
                return written
            path = path.with_suffix(".csv")  # degrade gracefully
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cls.TEMPLATE_HEADERS)
            w.writerows(cls._TEMPLATE_EXAMPLE)
        _log.info("Import template written (CSV): %s", path)
        return path

    @classmethod
    def _write_template_xlsx(cls, path: Path) -> Path | None:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:
            return None
        wb = Workbook()
        ws = wb.active
        ws.title = "Books"
        ws.append(list(cls.TEMPLATE_HEADERS))
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="4F46E5")
            cell.alignment = Alignment(horizontal="center")
        for row in cls._TEMPLATE_EXAMPLE:
            ws.append(list(row))
        for col_cells in ws.columns:
            letter = col_cells[0].column_letter
            width = max((len(str(c.value)) for c in col_cells if c.value), default=10)
            ws.column_dimensions[letter].width = max(12, min(40, width + 2))
        ws.freeze_panes = "A2"
        wb.save(path)
        _log.info("Import template written (XLSX): %s", path)
        return path

    # ------------------------------------------------------------ helpers #

    def _get_or_create(
        self,
        name: str | None,
        name_map: dict[str, int],
        created: list[str],
        service: CategoryService | LanguageService,
    ) -> int | None:
        if not name:
            return None
        key = name.lower()
        if key in name_map:
            return name_map[key]
        new_id = service.add(name)
        name_map[key] = new_id
        created.append(name)
        return new_id

    def _map_headers(self, header_row: Sequence) -> dict[str, int]:
        index: dict[str, int] = {}
        for col, raw in enumerate(header_row):
            if raw is None:
                continue
            key = str(raw).strip().lower()
            for canonical, aliases in self._HEADER_ALIASES.items():
                if key in aliases and canonical not in index:
                    index[canonical] = col
        return index

    def _parse_row(
        self, row_num: int, raw: Sequence, col: dict[str, int]
    ) -> ParsedRow:
        def cell(field: str) -> str:
            idx = col.get(field)
            if idx is None or idx >= len(raw):
                return ""
            v = raw[idx]
            if v is None:
                return ""
            # Excel hands back whole numbers as floats (e.g. 1952.0); trim.
            if isinstance(v, float) and v.is_integer():
                v = int(v)
            return str(v).strip()

        title = cell("title")
        author = cell("author")
        copies = self._parse_int(cell("copies"))
        row = ParsedRow(
            row_num=row_num,
            title=title,
            author=author,
            isbn=cell("isbn") or None,
            year=self._parse_int(cell("year")),
            category=cell("category") or None,
            language=cell("language") or None,
            total_copies=copies if (copies and copies >= 1) else 1,
            error=self._validate(title, author),
        )
        return row

    @staticmethod
    def _validate(title: str, author: str) -> str | None:
        if not title and not author:
            return "Missing Title and Author"
        if not title:
            return "Missing Title"
        if not author:
            return "Missing Author"
        return None

    @staticmethod
    def _parse_int(text: str) -> int | None:
        text = text.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            try:
                return int(float(text))
            except ValueError:
                return None

    @staticmethod
    def _is_blank(raw_row: Sequence) -> bool:
        return all(c is None or str(c).strip() == "" for c in raw_row)

    # ------------------------------------------------------------ readers #

    @staticmethod
    def _read_xlsx(path: Path) -> list[list]:
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ValueError(
                "Reading .xlsx files needs the 'openpyxl' package.\n"
                "Install it (pip install openpyxl) or save your file as .csv."
            )
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb.active
            return [list(r) for r in ws.iter_rows(values_only=True)]
        finally:
            wb.close()

    @staticmethod
    def _read_csv(path: Path) -> list[list]:
        # utf-8-sig strips the BOM Excel writes when saving CSV.
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            return [row for row in csv.reader(f)]
