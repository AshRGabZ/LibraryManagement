"""Bulk-import books from a spreadsheet.

Two-step UX so nothing is written blind: pick a file → preview every parsed
row with a per-row OK / error status → click Import to commit the valid ones.
A "Download Template" shortcut writes a correctly-headed starter file.
"""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...services import ParsedRow, Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider
from ..widgets import build_treeview


_log = logging.getLogger(__name__)


class ImportBooksDialog(tk.Toplevel):
    """Pick a .xlsx/.csv of books, preview, then bulk-insert."""

    def __init__(self, parent: tk.Widget, services: Services,
                 on_success=lambda: None) -> None:
        super().__init__(parent)
        self._services = services
        self.on_success = on_success
        self._rows: list[ParsedRow] = []

        self.title("Import Books")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # ── Header ───────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text="📥  Import Books",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Upload an Excel (.xlsx) or CSV file of books",
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

        # Instructions card
        info = tk.Frame(body, bg=Palette.PRIMARY_SOFT, padx=14, pady=10)
        info.pack(fill="x")
        tk.Label(info, text="Required columns:  Title, Author",
                 bg=Palette.PRIMARY_SOFT, fg=Palette.PRIMARY,
                 font=(base_font()[0], base_font()[1], "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(info,
                 text="Optional:  ISBN, Year, Category, Language, Copies   "
                      "·   Unknown categories/languages are created "
                      "automatically.",
                 bg=Palette.PRIMARY_SOFT, fg=Palette.TEXT,
                 font=small_font(), anchor="w",
                 justify="left").pack(fill="x", pady=(3, 0))

        # Action row: template + choose file + chosen-file status
        actions = tk.Frame(body, bg=Palette.SURFACE)
        actions.pack(fill="x", pady=(12, 8))
        ttk.Button(actions, text="⬇  Download Template",
                   style="Neutral.TButton",
                   command=self._download_template).pack(side="left")
        ttk.Button(actions, text="📂  Choose File…",
                   style="Primary.TButton",
                   command=self._choose_file).pack(side="left", padx=(8, 0))
        self._file_var = tk.StringVar(value="No file selected")
        tk.Label(actions, textvariable=self._file_var, bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=small_font(), anchor="e"
                 ).pack(side="right", fill="x", expand=True)

        tk.Label(body, text="Preview", bg=Palette.SURFACE, fg=Palette.PRIMARY,
                 font=heading_font()).pack(anchor="w", pady=(4, 4))

        container, self.preview = build_treeview(body, [
            ("row",      "Row",       50,  "center"),
            ("title",    "Title",     180, "w"),
            ("author",   "Author",    130, "w"),
            ("category", "Category",  110, "w"),
            ("language", "Language",  100, "w"),
            ("copies",   "Copies",    60,  "center"),
            ("status",   "Status",    170, "w"),
        ], height=10)
        container.pack(fill="both", expand=True)
        self.preview.tag_configure("row_ok", foreground=Palette.SUCCESS)
        self.preview.tag_configure("row_err", foreground=Palette.DANGER)

        center_window(self, parent, width=760, height=620)
        self.bind("<Escape>", lambda e: self.destroy())

    # ── actions ──────────────────────────────────────────────────────────────

    def _download_template(self) -> None:
        path_str = filedialog.asksaveasfilename(
            parent=self,
            title="Save Import Template",
            defaultextension=".xlsx",
            initialfile="books_import_template.xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"),
                       ("CSV (comma-separated)", "*.csv")],
        )
        if not path_str:
            return
        try:
            written = self._services.importer.write_template(Path(path_str))
            messagebox.showinfo("Template saved",
                                f"Starter file saved to:\n{written}", parent=self)
        except Exception as e:  # pragma: no cover - filesystem/permission
            _log.exception("Template write failed")
            messagebox.showerror("Could not save template", str(e), parent=self)

    def _choose_file(self) -> None:
        path_str = filedialog.askopenfilename(
            parent=self,
            title="Choose a books file",
            filetypes=[("Spreadsheets", "*.xlsx *.csv"),
                       ("Excel Workbook", "*.xlsx"),
                       ("CSV (comma-separated)", "*.csv"),
                       ("All files", "*.*")],
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self._rows = self._services.importer.parse_file(path)
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
                values=(r.row_num, r.title or "—", r.author or "—",
                        r.category or "—", r.language or "—",
                        r.total_copies, status),
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
        result = self._services.importer.import_rows(self._rows)
        self.on_success()

        lines = [f"✓  Added {result.added} "
                 f"book{'s' if result.added != 1 else ''}."]
        if result.created_categories:
            lines.append("• New categories: "
                         + ", ".join(result.created_categories))
        if result.created_languages:
            lines.append("• New languages: "
                         + ", ".join(result.created_languages))
        if result.errors:
            lines.append(f"\n⚠  {result.failed} row(s) skipped:")
            for row_num, msg in result.errors[:12]:
                lines.append(f"   Row {row_num}: {msg}")
            if result.failed > 12:
                lines.append(f"   …and {result.failed - 12} more.")
        messagebox.showinfo("Import complete", "\n".join(lines), parent=self)
        self.destroy()
