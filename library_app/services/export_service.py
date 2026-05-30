"""Export service — write domain collections to disk in spreadsheet formats.

XLSX is preferred (real Excel file with styled headers, frozen top row,
auto-sized columns). If `openpyxl` isn't installed at runtime, we fall back to
CSV — same data, opens fine in Excel/Numbers/LibreOffice, no extra dependency.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Callable, Iterable, Sequence

from ..domain import BookCopyWithBorrower, BookWithDetails


_log = logging.getLogger(__name__)


# Type alias: a "fetch copies for a book" callable. We accept this via
# parameter rather than importing `Services` here, so the export module stays
# leaf-level and unit-testable with mock data.
CopiesFetcher = Callable[[int], Sequence[BookCopyWithBorrower]]


class ExportService:
    """Stateless helpers — no DB access, just shape data and write to disk."""

    BOOK_HEADERS: tuple[str, ...] = (
        "ID", "Title", "Author", "Category", "Language",
        "ISBN", "Year", "Available", "Total Copies", "Serial Numbers",
    )

    # Second sheet (XLSX only) lists every copy individually — useful for
    # stocktake reports where one row per physical book makes sense.
    COPIES_HEADERS: tuple[str, ...] = (
        "Book ID", "Title", "Serial #", "Status",
        "Current Borrower", "Due Date",
    )

    # ------------------------------------------------------------- public  #

    @classmethod
    def export_books(
        cls,
        path: Path,
        books: Sequence[BookWithDetails],
        copies_fetcher: CopiesFetcher | None = None,
    ) -> Path:
        """Write `books` to `path`. Format chosen from suffix.

        Returns the path actually written (may differ from input if we had to
        fall back to CSV).

        If `copies_fetcher` is provided (typically `services.books.list_copies_with_borrower`),
        each book row also includes a comma-separated list of its serial
        numbers, and the XLSX output gains a second "Copies" sheet with one
        row per physical copy.
        """
        # Pre-fetch copies once per book so we don't requery during writing.
        copies_by_book: dict[int, list[BookCopyWithBorrower]] = {}
        if copies_fetcher is not None:
            for b in books:
                copies_by_book[b.id] = list(copies_fetcher(b.id))

        rows = [cls._book_to_row(b, copies_by_book.get(b.id)) for b in books]

        if path.suffix.lower() == ".xlsx":
            extra_sheets = []
            if copies_fetcher is not None:
                copy_rows = []
                for b in books:
                    for c in copies_by_book.get(b.id, []):
                        copy_rows.append(cls._copy_to_row(b, c))
                if copy_rows:
                    extra_sheets.append(("Copies", cls.COPIES_HEADERS, copy_rows))
            return cls._write_xlsx(
                path, cls.BOOK_HEADERS, rows, sheet="Books",
                extra_sheets=extra_sheets,
            )
        return cls._write_csv(path, cls.BOOK_HEADERS, rows)

    # ------------------------------------------------------------ shaping  #

    @staticmethod
    def _book_to_row(
        b: BookWithDetails,
        copies: Sequence[BookCopyWithBorrower] | None,
    ) -> tuple:
        # Serials column shows the full inventory: e.g. "B1-01, B1-02, B1-03".
        # Empty if no copy info was fetched (caller didn't pass copies_fetcher).
        serials = ", ".join(c.serial_number for c in copies) if copies else ""
        return (
            b.id, b.title, b.author,
            b.category_name or "", b.language_name or "",
            b.isbn or "", b.year or "",
            b.available_copies, b.total_copies,
            serials,
        )

    @staticmethod
    def _copy_to_row(
        b: BookWithDetails, c: BookCopyWithBorrower
    ) -> tuple:
        return (
            b.id, b.title, c.serial_number, c.status,
            c.borrower_name or "", c.borrower_due_on or "",
        )

    # ------------------------------------------------------------ writers  #

    @staticmethod
    def _write_csv(
        path: Path, headers: Sequence[str], rows: Iterable[Sequence]
    ) -> Path:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)
        _log.info("CSV export written: %s", path)
        return path

    @classmethod
    def _write_xlsx(
        cls,
        path: Path,
        headers: Sequence[str],
        rows: Sequence[Sequence],
        sheet: str = "Sheet1",
        extra_sheets: Sequence[tuple[str, Sequence[str], Sequence[Sequence]]] = (),
    ) -> Path:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:
            # Optional dep missing — degrade gracefully.
            _log.warning(
                "openpyxl not installed; exporting %s as CSV instead", path
            )
            csv_path = path.with_suffix(".csv")
            return cls._write_csv(csv_path, headers, rows)

        header_fill = PatternFill("solid", fgColor="2563EB")
        header_font = Font(bold=True, color="FFFFFF")

        def _populate(ws, hdrs, data_rows) -> None:
            ws.append(list(hdrs))
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for r in data_rows:
                ws.append(list(r))
            for col_cells in ws.columns:
                col_letter = col_cells[0].column_letter
                max_len = max(
                    (len(str(c.value)) for c in col_cells if c.value is not None),
                    default=10,
                )
                ws.column_dimensions[col_letter].width = max(10, min(60, max_len + 2))
            ws.freeze_panes = "A2"

        wb = Workbook()
        ws = wb.active
        ws.title = sheet[:31]
        _populate(ws, headers, rows)

        # Additional sheets (e.g. one-row-per-copy view) — each tab is
        # independently styled and frozen.
        for sheet_name, sheet_headers, sheet_rows in extra_sheets:
            extra = wb.create_sheet(sheet_name[:31])
            _populate(extra, sheet_headers, sheet_rows)

        wb.save(path)
        _log.info(
            "XLSX export written: %s (%d books, %d extra sheets)",
            path, len(rows), len(extra_sheets),
        )
        return path
