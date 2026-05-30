from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...domain.book_copy import (
    STATUS_AVAILABLE,
    STATUS_BORROWED,
    STATUS_DAMAGED,
    STATUS_LOST,
)
from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..widgets import TabHeader, TreeviewSorter, build_treeview


_log = logging.getLogger(__name__)


class BooksTab(ttk.Frame):
    """Browse-only catalogue view — books with their physical copies nested
    underneath. Each child row shows a copy's serial number plus current
    status (available, who borrowed it, lost, damaged). Management lives in
    the Admin tab."""

    COLUMNS = [
        ("author",    "Author",    130, "w"),
        ("category",  "Category",  110, "w"),
        ("language",  "Language",  110, "w"),
        ("isbn",      "ISBN",      110, "center"),
        ("year",      "Year",       80, "center"),
        ("available", "Available",  80, "center"),
        ("total",     "Total",      70, "center"),
        ("status",    "Status",    210, "w"),
    ]

    _BOOK_PREFIX = "b:"
    _COPY_PREFIX = "c:"

    def __init__(self, parent: tk.Widget, services: Services) -> None:
        super().__init__(parent)
        self._services = services
        self._build_ui()
        self.refresh()

    # ─────────────────────────────────────────── UI ──

    def _build_ui(self) -> None:
        TabHeader(self, "📚", "GHCC Library Management",
                  "Browse the catalogue — expand a book to see its physical copies"
                  ).pack(fill="x")

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        # Search input with left magnifier badge
        search_pill = tk.Frame(toolbar, bg=Palette.BORDER)
        search_pill.pack(side="left")
        tk.Label(search_pill, text=" 🔎 ", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(side="left", padx=(0, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        search_entry = tk.Entry(
            search_pill, textvariable=self.search_var, width=26,
            font=base_font(), relief="flat", bd=0,
            bg=Palette.SURFACE, fg=Palette.TEXT,
            insertbackground=Palette.PRIMARY,
        )
        search_entry.pack(side="left", padx=0, ipady=7, ipadx=8, pady=1)
        search_entry.bind("<FocusIn>",
                          lambda e: search_pill.configure(bg=Palette.BORDER_FOCUS))
        search_entry.bind("<FocusOut>",
                          lambda e: search_pill.configure(bg=Palette.BORDER))

        # Filters
        tk.Label(toolbar, text="  🏷️", bg=Palette.BG,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(side="left", padx=(14, 2))
        self.category_filter_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(
            toolbar, textvariable=self.category_filter_var, width=14,
            state="readonly", font=base_font())
        self._refresh_category_filter()
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self.refresh())
        self.category_combo.pack(side="left", padx=(0, 12))

        tk.Label(toolbar, text="🌐", bg=Palette.BG,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(side="left", padx=(0, 2))
        self.language_filter_var = tk.StringVar(value="All")
        self.language_combo = ttk.Combobox(
            toolbar, textvariable=self.language_filter_var, width=14,
            state="readonly", font=base_font())
        self._refresh_language_filter()
        self.language_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self.refresh())
        self.language_combo.pack(side="left", padx=(0, 12))

        # Right-side action buttons.
        # Single expand/collapse toggle — its label reflects the action it
        # will perform next (shows "Expand All" while collapsed, and flips to
        # "Collapse All" once expanded).
        self._all_expanded = False
        self._expand_btn = ttk.Button(
            toolbar, text="⤢  Expand All", style="Neutral.TButton",
            command=self._toggle_expand)
        self._expand_btn.pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻  Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)
        ttk.Button(toolbar, text="📤  Export", style="Primary.TButton",
                   command=self.export_books).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🏷️  Label", style="Purple.TButton",
                   command=self.view_label).pack(side="right", padx=4)

        # ── Treeview ─────────────────────────────────────────────────────────
        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.tree.configure(show="tree headings")
        self.tree.heading("#0", text="Title / Serial")
        self.tree.column("#0", width=320, anchor="w", stretch=True)

        self.tree.tag_configure(
            "book_row",
            background=Palette.ROW_ALT,
            foreground=Palette.TEXT,
        )

        self._sorter = TreeviewSorter(self.tree)
        self._sorter.sort_by("#0")

    # ─────────────────────────────────────────── filter helpers ──

    def _refresh_category_filter(self) -> None:
        names = [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = ["All"] + names

    def _refresh_language_filter(self) -> None:
        names = [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = ["All"] + names

    def refresh_filters(self) -> None:
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

    def _toggle_expand(self) -> None:
        """Flip every book row open/closed and update the button label."""
        self._all_expanded = not self._all_expanded
        self._apply_expand_state()

    def _apply_expand_state(self) -> None:
        """Open/close all book rows to match `_all_expanded` and sync the label."""
        for iid in self.tree.get_children(""):
            self.tree.item(iid, open=self._all_expanded)
        self._expand_btn.configure(
            text="⤡  Collapse All" if self._all_expanded else "⤢  Expand All"
        )

    # ─────────────────────────────────────────── copy row ──

    @staticmethod
    def _copy_status_display(copy) -> tuple[str, str]:
        """(display_text, tag) for the Status column on a copy row."""
        if copy.status == STATUS_AVAILABLE:
            return "● Available", "status_avail"
        if copy.status == STATUS_BORROWED:
            who = copy.borrower_name or "—"
            due = f" (due {copy.borrower_due_on})" if copy.borrower_due_on else ""
            overdue = (copy.borrower_due_on and
                       copy.borrower_due_on < date.today().isoformat())
            return (f"📖 Borrowed by {who}{due}",
                    "status_overdue" if overdue else "status_active")
        if copy.status == STATUS_LOST:
            return "🔍 Lost", "status_unavail"
        if copy.status == STATUS_DAMAGED:
            return "⚠ Damaged", "status_unavail"
        return copy.status, ""

    # ─────────────────────────────────────────── actions ──

    def export_books(self) -> None:
        """Export the currently-filtered book list to XLSX (or CSV fallback)."""
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
            messagebox.showinfo("Nothing to export",
                                "No books match the current filters.")
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
                copies_fetcher=self._services.books.list_copies_with_borrower,
            )
            _log.info("Exported %d books to %s", len(books), written)
            messagebox.showinfo(
                "Export complete",
                f"Saved {len(books)} book{'s' if len(books) != 1 else ''} to:\n{written}"
            )
        except Exception as e:
            _log.exception("Export failed")
            messagebox.showerror("Export failed", str(e))

    def view_label(self) -> None:
        """Open the label preview for the currently-selected copy."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(
                "Select a copy",
                "Expand a book and select a specific copy (the 🏷️ row).",
            )
            return
        iid = sel[0]
        if not iid.startswith(self._COPY_PREFIX):
            messagebox.showinfo(
                "Select a copy",
                "Books have multiple copies — please select a specific one "
                "(the 🏷️ row beneath the book)."
            )
            return

        copy_id = int(iid[len(self._COPY_PREFIX):])
        copy = self._services.books.get_copy(copy_id)
        if copy is None:
            return
        book = self._services.books.get(copy.book_id)
        category_name = None
        if book and book.category_id:
            cat = self._services.categories.get(book.category_id)
            category_name = cat.name if cat else None

        from ..dialogs import LabelPreviewDialog
        LabelPreviewDialog(
            self.winfo_toplevel(), self._services,
            serial_number=copy.serial_number,
            category_name=category_name,
        )

    # ─────────────────────────────────────────── refresh ──

    def refresh(self) -> None:
        # Preserve expanded state across refreshes
        expanded = {
            iid for iid in self.tree.get_children("")
            if self.tree.item(iid, "open")
        }

        for r in self.tree.get_children(""):
            self.tree.delete(r)

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

        for b in books:
            avail_pct = (b.available_copies / b.total_copies
                         if b.total_copies else 0)
            if b.available_copies == 0:
                status = "● Unavailable"
                status_tag = "status_unavail"
            elif avail_pct < 0.5:
                status = f"◑ {b.available_copies}/{b.total_copies} left"
                status_tag = "status_overdue"
            else:
                status = f"● {b.available_copies}/{b.total_copies} available"
                status_tag = "status_avail"

            book_iid = self._BOOK_PREFIX + str(b.id)
            self.tree.insert(
                "", "end",
                iid=book_iid,
                text=f"📘  {b.title}",
                values=(
                    b.author,
                    b.category_name or "—",
                    b.language_name or "—",
                    b.isbn or "—",
                    b.year or "—",
                    b.available_copies,
                    b.total_copies,
                    status,
                ),
                tags=("book_row", status_tag),
                # When "Expand All" is active, keep every row (incl. newly
                # filtered-in ones) open; otherwise remember per-row state.
                open=(self._all_expanded or book_iid in expanded),
            )

            for c in self._services.books.list_copies_with_borrower(b.id):
                status_text, c_tag = self._copy_status_display(c)
                self.tree.insert(
                    book_iid, "end",
                    iid=self._COPY_PREFIX + str(c.id),
                    text=f"      🏷️  {c.serial_number}",
                    values=(
                        "", "", "", "", "",
                        "1" if c.is_available else "0",
                        "1",
                        status_text,
                    ),
                    tags=(c_tag,),
                )

        self._sorter.resort()
