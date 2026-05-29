from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from ...domain import LoanWithDetails
from ...exceptions import LibraryError
from ...services import Services
from ..dialogs import BorrowDialog, RenewDialog
from ..theme import Palette, base_font
from ..widgets import DateEntry, TabHeader, TreeviewSorter, build_treeview


_log = logging.getLogger(__name__)


class LoansTab(ttk.Frame):
    """Loans grouped by member — one expandable row per borrower.

    Why group? A library member often borrows several books at once. Showing
    them flat means the librarian has to mentally fan-in to find "all of
    Alice's loans". The hierarchical tree gives a one-row-per-person summary
    with their loans nested underneath, and lets us put a single "💬 Notify"
    button per member in the toolbar.

    The composite identity (name, phone) lives in the `Member` row — selecting
    any loan resolves up to its parent member via `tree.parent()`.
    """

    # Columns visible for every row. Tree column (#0) shows "Member / Book".
    # Parent rows fill: phone + summary fields. Child rows fill: loan fields.
    COLUMNS = [
        ("phone", "Phone", 130, "w"),
        ("borrowed", "Borrowed", 100, "center"),
        ("due", "Due", 100, "center"),
        ("days_left", "Days Left", 110, "center"),
        ("returned", "Returned", 100, "center"),
        ("renewals", "Renewals", 80, "center"),
        ("status", "Status", 130, "center"),
    ]

    # iid prefixes — keep types straight when reading back tree.selection().
    _MEMBER_PREFIX = "m:"
    _LOAN_PREFIX = "l:"

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

    # ----------------------------------------------------------------- UI #

    def _build_ui(self) -> None:
        TabHeader(self, "🔄", "Loans",
                  "Borrow, renew and return books — grouped by member"
                  ).pack(fill="x")

        # --- Row 1: search + active-only + action buttons ----------------
        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=(base_font()[0], base_font()[1] + 2)
                 ).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search_var, width=28,
                  font=base_font()).pack(side="left")

        self.active_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Active only", variable=self.active_var,
                        command=self.refresh).pack(side="left", padx=12)

        # Action buttons — order matters (right-most packs first visually).
        ttk.Button(toolbar, text="📖 Borrow", style="Success.TButton",
                   command=self.borrow_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🔁 Renew", style="Purple.TButton",
                   command=self.renew_loan).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↩ Return", style="Primary.TButton",
                   command=self.return_book).pack(side="right", padx=4)
        # Always-active WhatsApp Notify — acts on the selected member (or
        # the member of the selected loan). No condition on overdue status.
        ttk.Button(toolbar, text="💬 WhatsApp", style="Whatsapp.TButton",
                   command=self.notify_whatsapp).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻ Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)

        # --- Row 2: date-range filter + result count ---------------------
        range_bar = tk.Frame(self, bg=Palette.BG, padx=14)
        range_bar.pack(fill="x", pady=(0, 6))

        tk.Label(range_bar, text="📅 Borrowed between:", bg=Palette.BG,
                 fg=Palette.TEXT, font=base_font()
                 ).pack(side="left", padx=(0, 6))

        self.from_date = DateEntry(range_bar, initial=None, width=11,
                                   on_change=self._on_range_change)
        self.from_date.pack(side="left")

        tk.Label(range_bar, text=" and ", bg=Palette.BG, fg=Palette.MUTED,
                 font=base_font()).pack(side="left")

        self.to_date = DateEntry(range_bar, initial=None, width=11,
                                 on_change=self._on_range_change)
        self.to_date.pack(side="left")

        ttk.Button(range_bar, text="Clear", style="Neutral.TButton",
                   command=self._clear_range).pack(side="left", padx=8)

        self.count_var = tk.StringVar(value="")
        tk.Label(range_bar, textvariable=self.count_var, bg=Palette.BG,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(side="left", padx=(12, 0))

        # --- Hierarchical Treeview -------------------------------------- #
        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Switch to tree+headings so the leftmost column shows expand arrows
        # and we can put member/book names there.
        self.tree.configure(show="tree headings")
        self.tree.heading("#0", text="Member / Book")
        self.tree.column("#0", width=300, anchor="w", stretch=True)

        # Member rows get bold-ish look via a tag — distinguishes them
        # visually from child loan rows even when collapsed.
        self.tree.tag_configure(
            "member", background=Palette.ROW_ALT, foreground=Palette.TEXT,
        )
        self.tree.tag_configure(
            "member_overdue", background="#fee2e2", foreground=Palette.DANGER,
        )

        # Click-to-sort. Sorting "Due" keeps members in their current order
        # (their Due column is blank → all tied → stable sort preserves order)
        # but reorders each member's loans by due date — the most useful
        # default when triaging overdue accounts.
        self._sorter = TreeviewSorter(self.tree)
        self._sorter.sort_by("due")

    # ---------------------------------------------------- helpers (read) #

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

    # -------------------------------------------------------- refresh   #

    def refresh(self) -> None:
        for r in self.tree.get_children():
            self.tree.delete(r)

        loans = self._services.loans.list_all(
            active_only=self.active_var.get(),
            search=self.search_var.get(),
            from_date=self.from_date.get_date(),
            to_date=self.to_date.get_date(),
        )

        # Group preserving the SQL-sorted order (most-urgent first).
        # The composite identity is the member_id from the loan's join —
        # name + phone are display projections of that single key.
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

        # Preserve the user's chosen sort across data refreshes.
        self._sorter.resort()

        n = len(loans)
        n_members = len(by_member)
        if self.from_date.get_date() or self.to_date.get_date():
            self.count_var.set(
                f"●  {n} loan{'s' if n != 1 else ''} across "
                f"{n_members} member{'s' if n_members != 1 else ''} in range"
            )
        else:
            self.count_var.set(
                f"●  {n} loan{'s' if n != 1 else ''} across "
                f"{n_members} member{'s' if n_members != 1 else ''}"
            )

    def _insert_member_group(
        self,
        member_id: int,
        loans: list[LoanWithDetails],
        max_r: int,
    ) -> None:
        member = self._services.members.get(member_id)
        # Member name comes from the join; fallback handles a race where the
        # member was deleted between the join and this row read.
        name = member.name if member else loans[0].member_name
        phone = member.phone if member else "—"

        active = [ln for ln in loans if not ln.is_returned]
        overdue = [ln for ln in active if ln.is_overdue]

        # Summary string for the Status column on the parent row.
        if not active:
            summary = f"{len(loans)} returned"
        elif overdue:
            summary = (
                f"⚠ {len(overdue)} overdue · "
                f"{len(active)} active"
            )
        else:
            summary = f"● {len(active)} active"

        parent_tag = "member_overdue" if overdue else "member"
        parent_iid = self._MEMBER_PREFIX + str(member_id)
        self.tree.insert(
            "", "end",
            iid=parent_iid,
            text=f"👤 {name}  ({len(loans)})",
            values=(
                phone or "—",
                "", "", "", "", "",  # no per-loan columns at member level
                summary,
            ),
            tags=(parent_tag,),
            open=True,
        )

        for ln in loans:
            if ln.is_returned:
                status, stag = "✓ Returned", "status_returned"
            elif ln.is_overdue:
                status, stag = "⚠ Overdue", "status_overdue"
            else:
                status, stag = "● Active", "status_active"

            self.tree.insert(
                parent_iid, "end",
                iid=self._LOAN_PREFIX + str(ln.id),
                text=f"    📖 {ln.book_title}",
                values=(
                    "",  # phone column blank on child rows
                    ln.borrowed_on,
                    ln.due_on or "—",
                    self._format_days_left(ln),
                    ln.returned_on or "—",
                    f"{ln.renew_count}/{max_r}",
                    status,
                ),
                tags=(stag,),
            )

    # ---------------------------------------------------- selection      #

    def _selected_loan_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(
                "Select a loan",
                "Please select a loan first."
            )
            return None
        iid = sel[0]
        if not iid.startswith(self._LOAN_PREFIX):
            messagebox.showinfo(
                "Select a loan",
                "Please select a specific loan, not the member row."
            )
            return None
        return int(iid[len(self._LOAN_PREFIX):])

    def _selected_member_id(self) -> int | None:
        """Resolve selection → member_id. Works for both member rows and
        child loan rows (walks up to the parent)."""
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

    # ---------------------------------------------------- actions       #

    def borrow_book(self) -> None:
        books = self._services.books.list_all()
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

    def notify_whatsapp(self) -> None:
        """Open WhatsApp pre-filled with this member's outstanding loans.

        Always active. Acts on whichever member is currently selected —
        either directly or by virtue of having one of their loans selected.
        """
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

        # Pull this member's loans fresh — the list might have been filtered
        # by date range on screen, but the message should reflect everything
        # they actually have out.
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
