from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from ...domain import Book, Member
from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider
from ..widgets import DateEntry, SearchablePicker


class BorrowDialog(tk.Toplevel):
    """Borrow a book — polished two-column filter bar, card-framed pickers,
    summary footer showing what will be borrowed before confirming."""

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

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text="📖  Borrow a Book",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Select a book and a member, then confirm",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Summary footer + Buttons (packed before scrollable body) ─────────
        make_divider(self).pack(fill="x", side="bottom")
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")
        ttk.Button(btns, text="✓  Borrow", style="Success.TButton",
                   command=self._submit).pack(side="right")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        # Live summary strip just above the buttons
        self._summary_var = tk.StringVar(value="")
        summary_strip = tk.Frame(self, bg=Palette.PRIMARY_SOFT, padx=18, pady=8)
        summary_strip.pack(fill="x", side="bottom")
        self._summary_label = tk.Label(
            summary_strip, textvariable=self._summary_var,
            bg=Palette.PRIMARY_SOFT, fg=Palette.PRIMARY,
            font=small_font(), anchor="w",
        )
        self._summary_label.pack(fill="x")
        self._update_summary()

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        # ── Filter bar ───────────────────────────────────────────────────────
        filter_card = tk.Frame(body, bg=Palette.CARD_BG,
                               highlightthickness=1,
                               highlightbackground=Palette.BORDER)
        filter_card.pack(fill="x", pady=(0, 14))
        filter_inner = tk.Frame(filter_card, bg=Palette.CARD_BG, padx=14, pady=10)
        filter_inner.pack(fill="x")
        filter_inner.columnconfigure(1, weight=1)
        filter_inner.columnconfigure(3, weight=1)

        tk.Label(filter_inner, text="🏷️  Category:", bg=Palette.CARD_BG,
                 fg=Palette.TEXT, font=base_font()
                 ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(
            filter_inner, textvariable=self.category_var, width=16,
            state="readonly", font=base_font())
        cat_names = ["All"] + [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = cat_names
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self._update_book_list())
        self.category_combo.grid(row=0, column=1, sticky="ew", padx=(0, 20))

        tk.Label(filter_inner, text="🌐  Language:", bg=Palette.CARD_BG,
                 fg=Palette.TEXT, font=base_font()
                 ).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.language_var = tk.StringVar(value="All")
        self.language_combo = ttk.Combobox(
            filter_inner, textvariable=self.language_var, width=16,
            state="readonly", font=base_font())
        lang_names = ["All"] + [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = lang_names
        self.language_combo.bind("<<ComboboxSelected>>",
                                 lambda *_: self._update_book_list())
        self.language_combo.grid(row=0, column=3, sticky="ew")

        # ── Book picker ───────────────────────────────────────────────────────
        tk.Label(body, text="📚  Select Book", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).pack(anchor="w", pady=(0, 6))

        book_card = tk.Frame(body, bg=Palette.BORDER)
        book_card.pack(fill="both", expand=True, pady=(0, 14))

        def fmt_book(b: Book) -> tuple[str, bool]:
            mark = "🟢" if b.is_available else "🔴"
            label = (f"  {mark}  {b.title}  —  {b.author}   "
                     f"({b.available_copies}/{b.total_copies} available)")
            return label, not b.is_available

        self.book_picker = SearchablePicker(
            book_card,
            [b for b in books if b.is_available],
            fmt_book,
            search_keys=("title", "author", "isbn"),
            placeholder="🔍  Search by title, author or ISBN…",
            height=7,
        )
        self.book_picker.pack(fill="both", expand=True, padx=1, pady=1)
        # add=True preserves SearchablePicker's _on_select (which sets selected_id)
        # while also triggering our live summary update.
        self.book_picker.listbox.bind("<<ListboxSelect>>",
                                      lambda e: self._update_summary(), add=True)

        # ── Member picker ─────────────────────────────────────────────────────
        tk.Label(body, text="👤  Select Member", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).pack(anchor="w", pady=(0, 6))

        member_card = tk.Frame(body, bg=Palette.BORDER)
        member_card.pack(fill="both", expand=True, pady=(0, 14))

        def fmt_member(m: Member) -> tuple[str, bool]:
            extra = [x for x in (m.email, m.phone) if x]
            tail = f"  ({' • '.join(extra)})" if extra else ""
            return f"  👤  {m.name}{tail}", False

        self.member_picker = SearchablePicker(
            member_card, members, fmt_member,
            search_keys=("name", "email", "phone"),
            placeholder="🔍  Search by name, email or phone…",
            height=5,
        )
        self.member_picker.pack(fill="both", expand=True, padx=1, pady=1)
        self.member_picker.listbox.bind("<<ListboxSelect>>",
                                        lambda e: self._update_summary(), add=True)

        # ── Loan period ───────────────────────────────────────────────────────
        period_row = tk.Frame(body, bg=Palette.SURFACE)
        period_row.pack(fill="x", pady=(0, 4))

        tk.Label(period_row, text="📅  Borrowed on:", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")
        self.borrowed_on_entry = DateEntry(period_row, initial=date.today())
        self.borrowed_on_entry.pack(side="left", padx=(8, 20))

        tk.Label(period_row, text="for", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")
        self.days_var = tk.StringVar(
            value=str(self._services.loans.DEFAULT_LOAN_DAYS))

        wrap = tk.Frame(period_row, bg=Palette.BORDER)
        wrap.pack(side="left", padx=(8, 4))
        days_entry = tk.Entry(
            wrap, textvariable=self.days_var, width=5, font=base_font(),
            relief="flat", bd=0,
            bg=Palette.SURFACE, fg=Palette.TEXT,
            insertbackground=Palette.PRIMARY,
        )
        days_entry.pack(padx=1, pady=1, ipady=6, ipadx=6)
        days_entry.bind("<FocusIn>",
                        lambda e: wrap.configure(bg=Palette.BORDER_FOCUS))
        days_entry.bind("<FocusOut>",
                        lambda e: wrap.configure(bg=Palette.BORDER))
        self.days_var.trace_add("write", lambda *_: self._update_summary())

        tk.Label(period_row, text="days", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")

        center_window(self, parent, width=700, height=740)
        self.bind("<Escape>", lambda e: self.destroy())

    # ── Helpers ────────────────────────────────────────────────────────────

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
        self._update_summary()

    def _update_summary(self) -> None:
        """Refresh the bottom summary strip based on current selections.

        Called both during construction (before pickers exist) and after
        selections change — guard with hasattr so the early call is a no-op.
        """
        if not hasattr(self, "book_picker") or not hasattr(self, "member_picker"):
            return
        book_id = self.book_picker.selected_id
        member_id = self.member_picker.selected_id
        try:
            days = int(self.days_var.get() or self._services.loans.DEFAULT_LOAN_DAYS)
        except ValueError:
            days = self._services.loans.DEFAULT_LOAN_DAYS

        parts: list[str] = []
        if book_id:
            book = next((b for b in self._all_books if b.id == book_id), None)
            if book:
                parts.append(f"📚 {book.title}")
        if member_id:
            m = self._services.members.get(member_id)
            if m:
                parts.append(f"👤 {m.name}")
        if parts:
            parts.append(f"📅 {days} days")
            self._summary_var.set("  ✦  Will borrow:  " + "  ·  ".join(parts))
        else:
            self._summary_var.set("  Select a book and a member above to preview the loan")

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
            borrowed_on = (
                self.borrowed_on_entry.get_date()
                if borrowed_str else date.today()
            )
            if borrowed_on is None:
                raise ValueError("Borrowed date must be YYYY-MM-DD.")
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
