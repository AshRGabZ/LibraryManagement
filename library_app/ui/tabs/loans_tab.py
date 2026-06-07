from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from ...domain import LoanWithDetails
from ...exceptions import LibraryError
from ...services import Services
from ..dialogs import BorrowDialog, EditLoanDialog, RenewDialog
from ..theme import Palette, base_font, heading_font, small_font
from ..widgets import DateEntry, TabHeader, TreeviewSorter, build_treeview


_log = logging.getLogger(__name__)


class LoansTab(ttk.Frame):
    """Loans grouped by member — one expandable row per borrower.

    Why group? A library member often borrows several books at once. Showing
    them flat means the librarian has to mentally fan-in to find "all of
    Alice's loans". The hierarchical tree gives a one-row-per-person summary
    with their loans nested underneath, and lets us put a single "💬 Notify"
    button per member in the toolbar.
    """

    COLUMNS = [
        ("phone",    "Phone",    130, "w"),
        ("serial",   "Serial #", 100, "center"),
        ("borrowed", "Borrowed", 100, "center"),
        ("due",      "Due",      100, "center"),
        ("days_left","Days Left",110, "center"),
        ("returned", "Returned", 100, "center"),
        ("renewals", "Renewals",  80, "center"),
        ("status",   "Status",   130, "center"),
    ]

    _MEMBER_PREFIX = "m:"
    _LOAN_PREFIX   = "l:"

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self.on_change = on_change or (lambda: None)
        self._build_ui()
        self.refresh()

    # ─────────────────────────────────────────── UI construction ──

    def _build_ui(self) -> None:
        TabHeader(self, "🔄", "Loans",
                  "Borrow, renew and return books — grouped by member"
                  ).pack(fill="x")

        # ── Row 1: search + active-only + action buttons ─────────────────────
        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        # Search pill
        search_pill = tk.Frame(toolbar, bg=Palette.BORDER)
        search_pill.pack(side="left")
        tk.Label(search_pill, text=" 🔎 ", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        search_entry = tk.Entry(
            search_pill, textvariable=self.search_var, width=26,
            font=base_font(), relief="flat", bd=0,
            bg=Palette.SURFACE, fg=Palette.TEXT,
            insertbackground=Palette.PRIMARY,
        )
        search_entry.pack(side="left", ipady=7, ipadx=8, pady=1)
        search_entry.bind("<FocusIn>",
                          lambda e: search_pill.configure(bg=Palette.BORDER_FOCUS))
        search_entry.bind("<FocusOut>",
                          lambda e: search_pill.configure(bg=Palette.BORDER))

        self.active_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Active only", variable=self.active_var,
                        command=self.refresh).pack(side="left", padx=12)

        # Action buttons (right → left order so last-packed = right-most)
        ttk.Button(toolbar, text="📖  Borrow", style="Success.TButton",
                   command=self.borrow_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🔁  Renew", style="Purple.TButton",
                   command=self.renew_loan).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↩  Return", style="Primary.TButton",
                   command=self.return_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="✏  Edit", style="Neutral.TButton",
                   command=self.edit_loan).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🗑  Delete", style="Danger.TButton",
                   command=self.delete_loan).pack(side="right", padx=4)
        ttk.Button(toolbar, text="💬  WhatsApp", style="Whatsapp.TButton",
                   command=self.notify_whatsapp).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻  Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)

        # ── Row 2: date-range filter + result count ───────────────────────────
        range_bar = tk.Frame(self, bg=Palette.BG, padx=14)
        range_bar.pack(fill="x", pady=(0, 6))

        filter_card = tk.Frame(range_bar, bg=Palette.CARD_BG,
                               highlightthickness=1,
                               highlightbackground=Palette.BORDER)
        filter_card.pack(side="left", fill="y")
        filter_inner = tk.Frame(filter_card, bg=Palette.CARD_BG, padx=12, pady=6)
        filter_inner.pack()

        tk.Label(filter_inner, text="📅  Borrowed between:", bg=Palette.CARD_BG,
                 fg=Palette.MUTED, font=small_font()
                 ).pack(side="left", padx=(0, 6))
        self.from_date = DateEntry(filter_inner, initial=None, width=11,
                                   on_change=self._on_range_change)
        self.from_date.pack(side="left")
        tk.Label(filter_inner, text="  and ", bg=Palette.CARD_BG,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")
        self.to_date = DateEntry(filter_inner, initial=None, width=11,
                                 on_change=self._on_range_change)
        self.to_date.pack(side="left")
        ttk.Button(filter_inner, text="✕  Clear", style="Neutral.TButton",
                   command=self._clear_range).pack(side="left", padx=(8, 0))

        self.count_var = tk.StringVar(value="")
        tk.Label(range_bar, textvariable=self.count_var, bg=Palette.BG,
                 fg=Palette.MUTED, font=small_font()
                 ).pack(side="left", padx=(12, 0))

        # Expand/collapse toggle — far right of this row, directly above the
        # table. Loans default to expanded, so it starts on "Collapse All".
        self._all_expanded = True
        self._expand_btn = ttk.Button(
            range_bar, text="⤡  Collapse All", style="Neutral.TButton",
            command=self._toggle_expand)
        self._expand_btn.pack(side="right")

        # ── Treeview ─────────────────────────────────────────────────────────
        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.tree.configure(show="tree headings")
        self.tree.heading("#0", text="Member / Book")
        self.tree.column("#0", width=300, anchor="w", stretch=True)

        self.tree.tag_configure(
            "member", background=Palette.ROW_ALT, foreground=Palette.TEXT)
        self.tree.tag_configure(
            "member_overdue", background="#fee2e2", foreground=Palette.DANGER)

        self._sorter = TreeviewSorter(self.tree)
        self._sorter.sort_by("due")

    # ─────────────────────────────────────────── expand/collapse ──

    def _toggle_expand(self) -> None:
        """Flip every member group open/closed and update the button label."""
        self._all_expanded = not self._all_expanded
        self._apply_expand_state()

    def _apply_expand_state(self) -> None:
        """Open/close all member groups to match `_all_expanded`, sync label."""
        for iid in self.tree.get_children(""):
            self.tree.item(iid, open=self._all_expanded)
        self._expand_btn.configure(
            text="⤡  Collapse All" if self._all_expanded else "⤢  Expand All"
        )

    # ─────────────────────────────────────────── helpers ──

    @staticmethod
    def _format_days_left(loan: LoanWithDetails) -> str:
        if loan.is_returned or loan.due_on is None:
            return "—"
        delta = (date.fromisoformat(loan.due_on) - date.today()).days
        if delta > 0:
            return f"{delta} day{'s' if delta != 1 else ''}"
        if delta == 0:
            return "Due today"
        n = abs(delta)
        return f"{n} day{'s' if n != 1 else ''} overdue"

    def _on_range_change(self) -> None:
        self.refresh()

    def _clear_range(self) -> None:
        self.from_date.clear()
        self.to_date.clear()

    # ─────────────────────────────────────────── refresh ──

    def refresh(self) -> None:
        for r in self.tree.get_children():
            self.tree.delete(r)

        loans = self._services.loans.list_all(
            active_only=self.active_var.get(),
            search=self.search_var.get(),
            from_date=self.from_date.get_date(),
            to_date=self.to_date.get_date(),
        )

        by_member: dict[int, list[LoanWithDetails]] = {}
        order: list[int] = []
        for ln in loans:
            if ln.member_id not in by_member:
                by_member[ln.member_id] = []
                order.append(ln.member_id)
            by_member[ln.member_id].append(ln)

        max_r = self._services.loans.MAX_RENEWALS
        for member_id in order:
            self._insert_member_group(member_id, by_member[member_id], max_r)

        self._sorter.resort()

        n = len(loans)
        n_members = len(by_member)
        suffix = "  in date range" if (self.from_date.get_date() or
                                        self.to_date.get_date()) else ""
        self.count_var.set(
            f"  ●  {n} loan{'s' if n != 1 else ''}  across  "
            f"{n_members} member{'s' if n_members != 1 else ''}{suffix}"
        )

    def _insert_member_group(
        self,
        member_id: int,
        loans: list[LoanWithDetails],
        max_r: int,
    ) -> None:
        member = self._services.members.get(member_id)
        name = member.name if member else loans[0].member_name
        phone = member.phone if member else "—"

        active = [ln for ln in loans if not ln.is_returned]
        overdue = [ln for ln in active if ln.is_overdue]

        if not active:
            summary = f"✓  {len(loans)} returned"
        elif overdue:
            summary = f"⚠  {len(overdue)} overdue  ·  {len(active)} active"
        else:
            summary = f"●  {len(active)} active"

        parent_tag = "member_overdue" if overdue else "member"
        parent_iid = self._MEMBER_PREFIX + str(member_id)
        self.tree.insert(
            "", "end",
            iid=parent_iid,
            text=f"  👤  {name}  ({len(loans)})",
            values=(
                phone or "—",
                "", "", "", "", "", "",
                summary,
            ),
            tags=(parent_tag,),
            open=self._all_expanded,
        )

        for ln in loans:
            if ln.is_returned:
                status, stag = "✓  Returned", "status_returned"
            elif ln.is_overdue:
                status, stag = "⚠  Overdue",  "status_overdue"
            else:
                status, stag = "●  Active",   "status_active"

            self.tree.insert(
                parent_iid, "end",
                iid=self._LOAN_PREFIX + str(ln.id),
                text=f"      📖  {ln.book_title}",
                values=(
                    "",
                    ln.serial_number or "—",
                    ln.borrowed_on,
                    ln.due_on or "—",
                    self._format_days_left(ln),
                    ln.returned_on or "—",
                    f"{ln.renew_count}/{max_r}",
                    status,
                ),
                tags=(stag,),
            )

    # ─────────────────────────────────────────── selection ──

    def _selected_loan_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a loan",
                                "Please select a loan first.")
            return None
        iid = sel[0]
        if not iid.startswith(self._LOAN_PREFIX):
            messagebox.showinfo("Select a loan",
                                "Please select a specific loan, not the member row.")
            return None
        return int(iid[len(self._LOAN_PREFIX):])

    def _selected_member_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if iid.startswith(self._MEMBER_PREFIX):
            return int(iid[len(self._MEMBER_PREFIX):])
        if iid.startswith(self._LOAN_PREFIX):
            parent = self.tree.parent(iid)
            if parent and parent.startswith(self._MEMBER_PREFIX):
                return int(parent[len(self._MEMBER_PREFIX):])
        return None

    # ─────────────────────────────────────────── actions ──

    def borrow_book(self) -> None:
        # list_with_details (not list_all) so the picker can show + search by
        # author name — Book itself only carries author_id now.
        books = self._services.books.list_with_details()
        members = self._services.members.list_all()
        available_count = sum(1 for b in books if b.is_available)
        _log.info("Borrow clicked — %d total books, %d available, %d members",
                  len(books), available_count, len(members))

        if not books:
            messagebox.showwarning(
                "No books",
                "There are no books in the catalogue yet.\n\n"
                "Add a book in the Admin tab first."
            )
            return
        if available_count == 0:
            messagebox.showwarning(
                "No books available",
                "All copies of every book are currently borrowed.\n\n"
                "Return a loan before borrowing again."
            )
            return
        if not members:
            messagebox.showwarning(
                "No members",
                "There are no members yet.\n\n"
                "Add a member in the Admin → Manage Members tab first."
            )
            return
        BorrowDialog(self.winfo_toplevel(), self._services, books, members,
                     on_success=self._after_change)

    def return_book(self) -> None:
        lid = self._selected_loan_id()
        if lid is None:
            return
        try:
            self._services.loans.return_loan(lid)
            self._after_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def renew_loan(self) -> None:
        lid = self._selected_loan_id()
        if lid is None:
            return
        RenewDialog(self.winfo_toplevel(), self._services, lid,
                    on_success=self._after_change)

    def edit_loan(self) -> None:
        """Correct a loan entered by mistake (member / dates)."""
        lid = self._selected_loan_id()
        if lid is None:
            return
        EditLoanDialog(self.winfo_toplevel(), self._services, lid,
                       on_success=self._after_change)

    def delete_loan(self) -> None:
        """Delete a loan created by mistake (releases the copy if active)."""
        lid = self._selected_loan_id()
        if lid is None:
            return
        loan = self._services.loans.get(lid)
        if loan is None:
            return
        if loan.is_returned:
            msg = (f"Delete this returned loan from the history?\n\n"
                   f"📚  {loan.book_title}\n👤  {loan.member_name}\n\n"
                   "This cannot be undone.")
        else:
            msg = (f"Delete this active loan?\n\n"
                   f"📚  {loan.book_title}  (copy {loan.serial_number or '—'})\n"
                   f"👤  {loan.member_name}\n\n"
                   "The copy will be returned to available. This cannot be undone.")
        if not messagebox.askyesno("Delete loan", msg):
            return
        try:
            self._services.loans.delete(lid)
            self._after_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def notify_whatsapp(self) -> None:
        """Open WhatsApp pre-filled with this member's outstanding loans."""
        member_id = self._selected_member_id()
        if member_id is None:
            messagebox.showinfo(
                "Select a member",
                "Click on a member row (or any of their loans) first."
            )
            return

        member = self._services.members.get(member_id)
        if member is None:
            messagebox.showerror("Not found", "That member no longer exists.")
            return

        all_loans = self._services.loans.list_all()
        their_loans = [ln for ln in all_loans if ln.member_id == member_id]

        try:
            url = self._services.notify.open_whatsapp(member, their_loans)
            _log.info("WhatsApp opened for member_id=%s → %s",
                      member_id, url[:80] + "...")
        except LibraryError as e:
            messagebox.showerror("Cannot notify", str(e))

    def _after_change(self) -> None:
        self.refresh()
        self.on_change()
