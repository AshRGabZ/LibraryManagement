from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from ...domain import Book, Member
from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font
from ..widgets import DateEntry, SearchablePicker


class BorrowDialog(tk.Toplevel):
    """Borrow a book — with category/language pre-filters, backdated borrowed_on,
    and a configurable loan period."""

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        books: list[Book],
        members: list[Member],
        on_success: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._all_books = books
        self.on_success = on_success
        self.title("Borrow Book")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent)
        self.grab_set()

        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="📖  Borrow a Book",
                  style="Header.TLabel").pack(anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        body.rowconfigure(4, weight=1)

        # Filters
        filter_row = tk.Frame(body, bg=Palette.SURFACE)
        filter_row.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        tk.Label(filter_row, text="🏷️ Category:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=base_font()).pack(side="left")
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(
            filter_row, textvariable=self.category_var, width=16,
            state="readonly", font=base_font())
        cat_names = ["All"] + [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = cat_names
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self._update_book_list())
        self.category_combo.pack(side="left", padx=(6, 24))

        tk.Label(filter_row, text="🌐 Language:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=base_font()).pack(side="left")
        self.language_var = tk.StringVar(value="All")
        self.language_combo = ttk.Combobox(
            filter_row, textvariable=self.language_var, width=16,
            state="readonly", font=base_font())
        lang_names = ["All"] + [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = lang_names
        self.language_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self._update_book_list())
        self.language_combo.pack(side="left", padx=(6, 0))

        # Book picker
        tk.Label(body, text="📚  Select Book", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        def fmt_book(b: Book) -> tuple[str, bool]:
            mark = "🟢" if b.is_available else "🔴"
            label = (f"  {mark}  {b.title}  —  {b.author}   "
                     f"({b.available_copies}/{b.total_copies} available)")
            return label, not b.is_available

        self.book_picker = SearchablePicker(
            body, [b for b in books if b.is_available], fmt_book,
            search_keys=("title", "author", "isbn"),
            placeholder="🔍  Search by title, author or ISBN…", height=8,
        )
        self.book_picker.grid(row=2, column=0, sticky="nsew", pady=(0, 14))

        # Member picker
        tk.Label(body, text="👤  Select Member", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=3, column=0, sticky="w", pady=(0, 6))

        def fmt_member(m: Member) -> tuple[str, bool]:
            extra = [x for x in (m.email, m.phone) if x]
            tail = f"  ({' • '.join(extra)})" if extra else ""
            return f"  👤  {m.name}{tail}", False

        self.member_picker = SearchablePicker(
            body, members, fmt_member,
            search_keys=("name", "email", "phone"),
            placeholder="🔍  Search by name, email or phone…", height=6,
        )
        self.member_picker.grid(row=4, column=0, sticky="nsew", pady=(0, 14))

        # Borrowed date & loan period
        period = tk.Frame(body, bg=Palette.SURFACE)
        period.grid(row=5, column=0, sticky="w", pady=(0, 4))

        tk.Label(period, text="📅  Borrowed on:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()).pack(side="left")
        self.borrowed_on_entry = DateEntry(period, initial=date.today())
        self.borrowed_on_entry.pack(side="left", padx=(8, 16))

        tk.Label(period, text="for", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()).pack(side="left")
        self.days_var = tk.StringVar(value=str(self._services.loans.DEFAULT_LOAN_DAYS))
        ttk.Entry(period, textvariable=self.days_var, width=5,
                  font=base_font()).pack(side="left", padx=(8, 4))
        tk.Label(period, text="days", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")

        # Buttons
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=14)
        btns.pack(fill="x")
        ttk.Button(btns, text="✓ Borrow", style="Success.TButton",
                   command=self._submit).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")

        # Size & center
        self.geometry("680x700")
        self.minsize(560, 580)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 680) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 700) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Escape>", lambda e: self.destroy())

    def _update_book_list(self) -> None:
        cat_name = self.category_var.get()
        lang_name = self.language_var.get()

        cat_id = None
        if cat_name != "All":
            for c in self._services.categories.list_all():
                if c.name == cat_name:
                    cat_id = c.id
                    break
        lang_id = None
        if lang_name != "All":
            for l in self._services.languages.list_all():
                if l.name == lang_name:
                    lang_id = l.id
                    break

        filtered = [
            b for b in self._all_books
            if b.is_available
            and (cat_id is None or b.category_id == cat_id)
            and (lang_id is None or b.language_id == lang_id)
        ]
        self.book_picker.set_items(filtered)

    def _submit(self) -> None:
        if not self.book_picker.selected_id:
            messagebox.showerror("Validation", "Please select a book.", parent=self)
            return
        if not self.member_picker.selected_id:
            messagebox.showerror("Validation", "Please select a member.", parent=self)
            return
        try:
            days = int(self.days_var.get() or self._services.loans.DEFAULT_LOAN_DAYS)
            borrowed_str = self.borrowed_on_entry.get()
            if borrowed_str:
                borrowed_on = self.borrowed_on_entry.get_date()
                if borrowed_on is None:
                    raise ValueError("Borrowed date must be YYYY-MM-DD.")
            else:
                borrowed_on = date.today()

            self._services.loans.borrow(
                self.book_picker.selected_id,
                self.member_picker.selected_id,
                loan_days=days,
                borrowed_on=borrowed_on,
            )
            self.destroy()
            self.on_success()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e), parent=self)
