"""Bulk-import members from a spreadsheet (.xlsx or .csv)."""
from __future__ import annotations

from pathlib import Path

from ._import_dialog_base import BaseImportDialog


class ImportMembersDialog(BaseImportDialog):
    """Pick a .xlsx/.csv of members, preview, then bulk-insert."""

    title_text = "Import Members"
    subtitle_text = "Upload an Excel (.xlsx) or CSV file of members"
    required_text = "Required column:  Name"
    optional_text = ("Optional:  Email, Phone   ·   Phone numbers are normalised"
                     " to 10 digits; duplicate (name + phone) members are skipped.")
    template_filename = "members_import_template.xlsx"
    data_columns = [
        ("row",   "Row",    50,  "center"),
        ("name",  "Name",   190, "w"),
        ("email", "Email",  190, "w"),
        ("phone", "Phone",  120, "w"),
    ]

    def _parse(self, path: Path):
        return self._services.importer.parse_members_file(path)

    def _row_cells(self, r) -> tuple:
        return (r.row_num, r.name or "—", r.email or "—", r.phone or "—")

    def _write_template(self, path: Path) -> Path:
        return self._services.importer.write_members_template(path)

    def _run_import(self, rows) -> list[str]:
        result = self._services.importer.import_members(rows)
        lines = [f"✓  Added {result.added} "
                 f"member{'s' if result.added != 1 else ''}."]
        lines += self._error_lines(result.errors)
        return lines
