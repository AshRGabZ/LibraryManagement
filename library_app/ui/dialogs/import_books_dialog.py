"""Bulk-import books from a spreadsheet (.xlsx or .csv)."""
from __future__ import annotations

from pathlib import Path

from ._import_dialog_base import BaseImportDialog


class ImportBooksDialog(BaseImportDialog):
    """Pick a .xlsx/.csv of books, preview, then bulk-insert."""

    title_text = "Import Books"
    subtitle_text = "Upload an Excel (.xlsx) or CSV file of books"
    required_text = "Required column:  Title"
    optional_text = ("Optional:  Author, ISBN, Year, Category, Language, Copies"
                     "   ·   Unknown authors / categories / languages are "
                     "created automatically.")
    template_filename = "books_import_template.xlsx"
    data_columns = [
        ("row",      "Row",       50,  "center"),
        ("title",    "Title",     170, "w"),
        ("author",   "Author",    120, "w"),
        ("category", "Category",  100, "w"),
        ("language", "Language",  90,  "w"),
        ("copies",   "Copies",    60,  "center"),
    ]

    def _parse(self, path: Path):
        return self._services.importer.parse_file(path)

    def _row_cells(self, r) -> tuple:
        return (r.row_num, r.title or "—", r.author or "—",
                r.category or "—", r.language or "—", r.total_copies)

    def _write_template(self, path: Path) -> Path:
        return self._services.importer.write_template(path)

    def _run_import(self, rows) -> list[str]:
        result = self._services.importer.import_rows(rows)
        lines: list[str] = []
        if result.added:
            lines.append(f"✓  Added {result.added} new "
                         f"book{'s' if result.added != 1 else ''}.")
        if result.merged:
            lines.append(f"✓  Added copies to {result.merged} existing "
                         f"book{'s' if result.merged != 1 else ''} "
                         "(same title, author & language).")
        if not result.added and not result.merged:
            lines.append("No new books imported.")
        if result.created_authors:
            lines.append("• New authors: " + ", ".join(result.created_authors))
        if result.created_categories:
            lines.append("• New categories: "
                         + ", ".join(result.created_categories))
        if result.created_languages:
            lines.append("• New languages: "
                         + ", ".join(result.created_languages))
        lines += self._error_lines(result.errors)
        return lines
