"""Edit a loan that was created by mistake.

Lets a librarian correct the borrower and/or the borrowed / due dates. The book
and physical copy are intentionally NOT editable here — to fix a wrong book,
delete the loan and borrow again (keeps the availability accounting simple).
"""
from __future__ import annotations

from datetime import date
from tkinter import messagebox, ttk
import tkinter as tk
from typing import Callable

from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider
from ..widgets import DateEntry, SearchablePicker


class EditLoanDialog(tk.Toplevel):
    """Correct a loan's member and dates."""

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        loan_id: int,
        on_success: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._services = services
        self.on_success = on_success
        self.title("Edit Loan")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        loan = services.loans.get(loan_id)
        if loan is None:
            messagebox.showerror("Error", "Loan not found.", parent=parent)
            self.destroy()
            return
        self._loan = loan

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text="✏️  Edit Loan",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Correct a loan entered by mistake",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))
        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Footer (reserved at the bottom) ──────────────────────────────────
        make_divider(self).pack(fill="x", side="bottom")
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")
        ttk.Button(btns, text="✓  Save", style="Primary.TButton",
                   command=self._submit).pack(side="right")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=16)
        body.pack(fill="both", expand=True)

        # Read-only book/copy summary (the book can't be changed here).
        info = tk.Frame(body, bg=Palette.CARD_BG, padx=14, pady=10,
                        highlightthickness=1, highlightbackground=Palette.BORDER)
        info.pack(fill="x", pady=(0, 14))
        serial = loan.serial_number or "—"
        tk.Label(info, text=f"📚  {loan.book_title}", bg=Palette.CARD_BG,
                 fg=Palette.TEXT, font=heading_font(), anchor="w").pack(fill="x")
        tk.Label(info, text=f"🔖  Copy {serial}   ·   to change the book, delete "
                            "this loan and borrow again",
                 bg=Palette.CARD_BG, fg=Palette.MUTED, font=small_font(),
                 anchor="w").pack(fill="x", pady=(3, 0))

        # ── Member (reassign) ────────────────────────────────────────────────
        tk.Label(body, text="👤  Member", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).pack(anchor="w", pady=(0, 6))

        # Active members, plus the current borrower (in case they're archived).
        members = list(self._services.members.list_all())
        if not any(m.id == loan.member_id for m in members):
            current = self._services.members.get(loan.member_id)
            if current is not None:
                members.insert(0, current)

        def fmt_member(m):
            extra = [x for x in (m.email, m.phone) if x]
            tail = f"  ({' • '.join(extra)})" if extra else ""
            return f"  👤  {m.name}{tail}", False

        member_card = tk.Frame(body, bg=Palette.BORDER)
        member_card.pack(fill="both", expand=True, pady=(0, 14))
        self.member_picker = SearchablePicker(
            member_card, members, fmt_member,
            search_keys=("name", "email", "phone"),
            placeholder="🔍  Search by name, email or phone…",
            height=6,
        )
        self.member_picker.pack(fill="both", expand=True, padx=1, pady=1)
        # Pre-select the current borrower (highlight + remember the id).
        self.member_picker.selected_id = loan.member_id
        for i, m in enumerate(members):
            if m.id == loan.member_id:
                self.member_picker.listbox.selection_set(i)
                self.member_picker.listbox.see(i)
                self.member_picker.listbox.activate(i)
                break

        # ── Dates ─────────────────────────────────────────────────────────────
        dates = tk.Frame(body, bg=Palette.SURFACE)
        dates.pack(fill="x")
        tk.Label(dates, text="📅  Borrowed on:", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")
        self.borrowed_entry = DateEntry(
            dates, initial=self._parse(loan.borrowed_on))
        self.borrowed_entry.pack(side="left", padx=(8, 20))
        tk.Label(dates, text="📅  Due on:", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")
        self.due_entry = DateEntry(dates, initial=self._parse(loan.due_on))
        self.due_entry.pack(side="left", padx=(8, 0))

        self.bind("<Escape>", lambda e: self.destroy())
        center_window(self, parent, width=580, height=620)

    @staticmethod
    def _parse(iso: str | None) -> date | None:
        if not iso:
            return None
        try:
            return date.fromisoformat(iso)
        except ValueError:
            return None

    def _submit(self) -> None:
        # Untouched picker (or a search that cleared the selection) keeps the
        # original borrower.
        member_id = self.member_picker.selected_id or self._loan.member_id
        borrowed = self.borrowed_entry.get_date()
        due = self.due_entry.get_date()
        if borrowed is None:
            messagebox.showerror("Validation",
                                 "Enter a valid borrowed date (YYYY-MM-DD).",
                                 parent=self)
            return
        if due is None:
            messagebox.showerror("Validation",
                                 "Enter a valid due date (YYYY-MM-DD).",
                                 parent=self)
            return
        try:
            self._services.loans.update(self._loan.id, member_id, borrowed, due)
            self.destroy()
            self.on_success()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e), parent=self)
