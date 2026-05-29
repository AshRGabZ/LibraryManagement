"""Export service — write domain collections to disk in spreadsheet formats.

XLSX is preferred (real Excel file with styled headers, frozen top row,
auto-sized columns). If `openpyxl` isn't installed at runtime, we fall back to
CSV — same data, opens fine in Excel/Numbers/LibreOffice, no extra dependency.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable, Sequence

from ..domain import BookWithDetails


_log = logging.getLogger(__name__)


class ExportService:
    """Stateless helpers — no DB access, just shape data and write to disk."""

    BOOK_HEADERS: tuple[str, ...] = (
        "ID", "Title", "Author", "Category", "Language",
        "ISBN", "Year", "Available", "Total Copies",
    )

    # ------------------------------------------------------------- public  #

    @classmethod
    def export_books(
        cls, path: Path, books: Sequence[BookWithDetails]
    ) -> Path:
        """Write `books` to `path`. Format chosen from suffix.

        Returns the path actually written (may differ from input if we had to
        fall back to CSV).
        """
        rows = [cls._book_to_row(b) for b in books]
        if path.suffix.lower() == ".xlsx":
            return cls._write_xlsx(path, cls.BOOK_HEADERS, rows, sheet="Books")
        return cls._write_csv(path, cls.BOOK_HEADERS, rows)

    # ------------------------------------------------------------ shaping  #

    @staticmethod
    def _book_to_row(b: BookWithDetails) -> tuple:
        return (
            b.id, b.title, b.author,
            b.category_name or "", b.language_name or "",
            b.isbn or "", b.year or "",
            b.available_copies, b.total_copies,
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

        wb = Workbook()
        ws = wb.active
        ws.title = sheet[:31]  # Excel sheet name limit

        # Header row with brand styling
        ws.append(list(headers))
        header_fill = PatternFill("solid", fgColor="2563EB")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Data rows
        for row in rows:
            ws.append(list(row))

        # Auto-size columns based on longest visible cell content
        for col_cells in ws.columns:
            col_letter = col_cells[0].column_letter
            max_len = max(
                (len(str(c.value)) for c in col_cells if c.value is not None),
                default=10,
            )
            ws.column_dimensions[col_letter].width = max(10, min(40, max_len + 2))

        ws.freeze_panes = "A2"  # keep headers visible while scrolling
        wb.save(path)
        _log.info("XLSX export written: %s (%d rows)", path, len(rows))
        return path
