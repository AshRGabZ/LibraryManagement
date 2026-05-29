from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...services import Services
from ..theme import Palette, base_font
from ..widgets import TabHeader, TreeviewSorter, build_treeview


_log = logging.getLogger(__name__)


class BooksTab(ttk.Frame):
    """Browse-only view of the catalogue. Management lives in the Admin tab."""

    COLUMNS = [
        ("id", "ID", 60, "center"),
        ("title", "Title", 200, "w"),
        ("author", "Author", 130, "w"),
        ("category", "Category", 110, "w"),
        ("language", "Language", 110, "w"),
        ("isbn", "ISBN", 110, "center"),
        ("year", "Year", 80, "center"),
        ("available", "Available", 80, "center"),
        ("total", "Total", 70, "center"),
        ("status", "Status", 80, "center"),
    ]

    def __init__(self, parent: tk.Widget, services: Services) -> None:
        super().__init__(parent)
        self._services = services
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        TabHeader(self, "📚", "GHCC Library Management",
                  "Browse the catalogue").pack(fill="x")

        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        # Search
        tk.Label(toolbar, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=(base_font()[0], base_font()[1] + 2)
                 ).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search_var, width=28,
                  font=base_font()).pack(side="left")

        # Filters
        tk.Label(toolbar, text="  🏷️ Category:", bg=Palette.BG,
                 fg=Palette.TEXT, font=base_font()
                 ).pack(side="left", padx=(12, 4))
        self.category_filter_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(
            toolbar, textvariable=self.category_filter_var, width=14,
            state="readonly", font=base_font())
        self._refresh_category_filter()
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self.refresh())
        self.category_combo.pack(side="left", padx=(0, 12))

        tk.Label(toolbar, text="🌐 Language:", bg=Palette.BG,
                 fg=Palette.TEXT, font=base_font()
                 ).pack(side="left", padx=(0, 4))
        self.language_filter_var = tk.StringVar(value="All")
        self.language_combo = ttk.Combobox(
            toolbar, textvariable=self.language_filter_var, width=14,
            state="readonly", font=base_font())
        self._refresh_language_filter()
        self.language_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self.refresh())
        self.language_combo.pack(side="left", padx=(0, 12))

        ttk.Button(toolbar, text="↻ Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)
        ttk.Button(toolbar, text="📤 Export", style="Primary.TButton",
                   command=self.export_books).pack(side="right", padx=4)

        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Click-to-sort on every column. Defaults to "Title ▲" on load —
        # gives a deterministic starting order without forcing a click.
        self._sorter = TreeviewSorter(self.tree)
        self._sorter.sort_by("title")

    def _refresh_category_filter(self) -> None:
        names = [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = ["All"] + names

    def _refresh_language_filter(self) -> None:
        names = [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = ["All"] + names

    def refresh_filters(self) -> None:
        """Re-populate the filter dropdowns; preserve selections if still valid."""
        current_cat = self.category_filter_var.get()
        current_lang = self.language_filter_var.get()
        self._refresh_category_filter()
        self._refresh_language_filter()
        if current_cat in self.category_combo["values"]:
            self.category_filter_var.set(current_cat)
        else:
            self.category_filter_var.set("All")
        if current_lang in self.language_combo["values"]:
            self.language_filter_var.set(current_lang)
        else:
            self.language_filter_var.set("All")

    def _resolve_id(self, name: str, items) -> int | None:
        if name == "All":
            return None
        for item in items:
            if item.name == name:
                return item.id
        return None

    def export_books(self) -> None:
        """Export the currently-filtered book list to XLSX (or CSV fallback).

        We re-query the service with the same filters the user sees, so the
        export matches the table on screen exactly — not "all books in DB".
        """
        cat_id = self._resolve_id(
            self.category_filter_var.get(),
            self._services.categories.list_all(),
        )
        lang_id = self._resolve_id(
            self.language_filter_var.get(),
            self._services.languages.list_all(),
        )
        books = self._services.books.list_with_details(
            search=self.search_var.get(),
            category_id=cat_id,
            language_id=lang_id,
        )
        if not books:
            messagebox.showinfo(
                "Nothing to export",
                "No books match the current filters."
            )
            return

        default_name = f"books_{date.today().isoformat()}.xlsx"
        path_str = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export Books",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[
                ("Excel Workbook", "*.xlsx"),
                ("CSV (comma-separated)", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path_str:
            return

        try:
            written = self._services.export.export_books(
                Path(path_str), books,
            )
            _log.info("Exported %d books to %s", len(books), written)
            messagebox.showinfo(
                "Export complete",
                f"Saved {len(books)} book{'s' if len(books) != 1 else ''} to:\n{written}"
            )
        except Exception as e:
            _log.exception("Export failed")
            messagebox.showerror("Export failed", str(e))

    def refresh(self) -> None:
        for r in self.tree.get_children():
            self.tree.delete(r)

        cat_id = self._resolve_id(
            self.category_filter_var.get(),
            self._services.categories.list_all(),
        )
        lang_id = self._resolve_id(
            self.language_filter_var.get(),
            self._services.languages.list_all(),
        )
        # Single JOIN query — book + category_name + language_name in one shot.
        books = self._services.books.list_with_details(
            search=self.search_var.get(),
            category_id=cat_id,
            language_id=lang_id,
        )

        for i, b in enumerate(books):
            status = "● Available" if b.is_available else "● Unavailable"
            status_tag = "status_avail" if b.is_available else "status_unavail"
            row_tag = "even" if i % 2 else "odd"

            self.tree.insert(
                "", "end",
                values=(b.id, b.title, b.author,
                        b.category_name or "—", b.language_name or "—",
                        b.isbn or "—", b.year or "—",
                        b.available_copies, b.total_copies, status),
                tags=(row_tag, status_tag),
            )
        # Preserve user's sort selection across refreshes
        self._sorter.resort()
