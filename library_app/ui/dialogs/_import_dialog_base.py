"""Shared chrome + flow for spreadsheet import dialogs.

Concrete dialogs (books, members) subclass :class:`BaseImportDialog` and supply
the entity-specific bits — instructions, preview columns, and the parse /
import / template calls. The two-step UX lives here once:

    pick a file → preview every parsed row with a per-row OK / error status →
    Import the valid rows.

Both `.xlsx` and `.csv` are accepted (handled by the import service).
"""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider
from ..widgets import build_treeview


_log = logging.getLogger(__name__)


class BaseImportDialog(tk.Toplevel):
    """Pick a .xlsx/.csv, preview rows, then bulk-insert the valid ones."""

    # ── subclass-provided metadata ─────────────────────────────────────────
    icon: str = "📥"
    title_text: str = "Import"
    subtitle_text: str = "Upload an Excel (.xlsx) or CSV file"
    required_text: str = ""
    optional_text: str = ""
    template_filename: str = "import_template.xlsx"
    #: Data columns for the preview (key, heading, width, anchor). A trailing
    #: "Status" column is appended automatically.
    data_columns: list[tuple] = []

    def __init__(self, parent: tk.Widget, services: Services,
                 on_success=lambda: None) -> None:
        super().__init__(parent)
        self._services = services
        self.on_success = on_success
        self._rows: list = []

        self.title(self.title_text)
        self.configure(bg=Palette.SURFACE)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # ── Header ───────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text=f"{self.icon}  {self.title_text}",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text=self.subtitle_text,
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))
        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Footer (reserved at the bottom) ──────────────────────────────────
        make_divider(self).pack(fill="x", side="bottom")
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")
        self._import_btn = ttk.Button(
            btns, text="✓  Import", style="Success.TButton",
            command=self._do_import, state="disabled",
        )
        self._import_btn.pack(side="right")
        ttk.Button(btns, text="Close", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=16)
        body.pack(fill="both", expand=True)

        info = tk.Frame(body, bg=Palette.PRIMARY_SOFT, padx=14, pady=10)
        info.pack(fill="x")
        tk.Label(info, text=self.required_text, bg=Palette.PRIMARY_SOFT,
                 fg=Palette.PRIMARY,
                 font=(base_font()[0], base_font()[1], "bold"),
                 anchor="w").pack(fill="x")
        if self.optional_text:
            tk.Label(info, text=self.optional_text, bg=Palette.PRIMARY_SOFT,
                     fg=Palette.TEXT, font=small_font(), anchor="w",
                     justify="left").pack(fill="x", pady=(3, 0))

        actions = tk.Frame(body, bg=Palette.SURFACE)
        actions.pack(fill="x", pady=(12, 8))
        ttk.Button(actions, text="⬇  Download Template",
                   style="Neutral.TButton",
                   command=self._download_template).pack(side="left")
        ttk.Button(actions, text="📂  Choose File…", style="Primary.TButton",
                   command=self._choose_file).pack(side="left", padx=(8, 0))
        self._file_var = tk.StringVar(value="No file selected")
        tk.Label(actions, textvariable=self._file_var, bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=small_font(), anchor="e"
                 ).pack(side="right", fill="x", expand=True)

        tk.Label(body, text="Preview", bg=Palette.SURFACE, fg=Palette.PRIMARY,
                 font=heading_font()).pack(anchor="w", pady=(4, 4))

        columns = list(self.data_columns) + [("status", "Status", 170, "w")]
        container, self.preview = build_treeview(body, columns, height=10)
        container.pack(fill="both", expand=True)
        self.preview.tag_configure("row_ok", foreground=Palette.SUCCESS)
        self.preview.tag_configure("row_err", foreground=Palette.DANGER)

        center_window(self, parent, width=760, height=620)
        self.bind("<Escape>", lambda e: self.destroy())

    # ── hooks — subclasses override these ────────────────────────────────
    def _parse(self, path: Path) -> list:
        """Parse + validate the file into rows (each with .is_valid/.error)."""
        raise NotImplementedError

    def _row_cells(self, row) -> tuple:
        """Preview values for `data_columns` (status is added by the base)."""
        raise NotImplementedError

    def _write_template(self, path: Path) -> Path:
        raise NotImplementedError

    def _run_import(self, rows) -> list[str]:
        """Perform the import via the service; return summary lines to show."""
        raise NotImplementedError

    # ── shared helper for the trailing error summary ─────────────────────
    @staticmethod
    def _error_lines(errors: list[tuple[int, str]]) -> list[str]:
        if not errors:
            return []
        lines = [f"\n⚠  {len(errors)} row(s) skipped:"]
        for row_num, msg in errors[:12]:
            lines.append(f"   Row {row_num}: {msg}")
        if len(errors) > 12:
            lines.append(f"   …and {len(errors) - 12} more.")
        return lines

    # ── flow ──────────────────────────────────────────────────────────────
    def _download_template(self) -> None:
        path_str = filedialog.asksaveasfilename(
            parent=self, title="Save Import Template",
            defaultextension=".xlsx", initialfile=self.template_filename,
            filetypes=[("Excel Workbook", "*.xlsx"),
                       ("CSV (comma-separated)", "*.csv")],
        )
        if not path_str:
            return
        try:
            written = self._write_template(Path(path_str))
            messagebox.showinfo("Template saved",
                                f"Starter file saved to:\n{written}", parent=self)
        except Exception as e:  # pragma: no cover - filesystem/permission
            _log.exception("Template write failed")
            messagebox.showerror("Could not save template", str(e), parent=self)

    def _choose_file(self) -> None:
        path_str = filedialog.askopenfilename(
            parent=self, title="Choose a file",
            filetypes=[("Spreadsheets", "*.xlsx *.csv"),
                       ("Excel Workbook", "*.xlsx"),
                       ("CSV (comma-separated)", "*.csv"),
                       ("All files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self._rows = self._parse(path)
        except ValueError as e:
            messagebox.showerror("Could not read file", str(e), parent=self)
            return
        except Exception as e:  # pragma: no cover - unexpected parse failure
            _log.exception("Parse failed")
            messagebox.showerror("Could not read file", str(e), parent=self)
            return
        self._populate_preview(path)

    def _populate_preview(self, path: Path) -> None:
        for item in self.preview.get_children():
            self.preview.delete(item)
        for r in self._rows:
            status = "✓  OK" if r.is_valid else f"✗  {r.error}"
            self.preview.insert(
                "", "end",
                values=(*self._row_cells(r), status),
                tags=("row_ok" if r.is_valid else "row_err",),
            )
        valid = sum(1 for r in self._rows if r.is_valid)
        invalid = len(self._rows) - valid
        summary = f"{path.name}  —  {valid} ready"
        if invalid:
            summary += f", {invalid} with issues"
        self._file_var.set(summary)
        self._import_btn.configure(
            text=f"✓  Import {valid}" if valid else "✓  Import",
            state="normal" if valid else "disabled",
        )

    def _do_import(self) -> None:
        valid = [r for r in self._rows if r.is_valid]
        if not valid:
            messagebox.showwarning("Nothing to import",
                                   "There are no valid rows to import.",
                                   parent=self)
            return
        lines = self._run_import(self._rows)
        self.on_success()
        messagebox.showinfo("Import complete", "\n".join(lines), parent=self)
        self.destroy()
