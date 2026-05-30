"""Admin → Manage Copies dialog.

Per-copy view + serial renaming for a single book. Shown from the Admin →
Manage Books tab so librarians can match the system's auto-generated serials
to their physical labels (barcodes, spine labels, etc.).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider
from ..widgets import build_treeview


# Maps copy status → (display text, chip background, chip foreground)
_STATUS_DISPLAY: dict[str, tuple[str, str, str]] = {
    "available": ("● Available",  Palette.CHIP_SUCCESS_BG, Palette.CHIP_SUCCESS_FG),
    "borrowed":  ("📖 Borrowed",  Palette.CHIP_ACTIVE_BG,  Palette.CHIP_ACTIVE_FG),
    "lost":      ("🔍 Lost",      Palette.CHIP_DANGER_BG,  Palette.CHIP_DANGER_FG),
    "damaged":   ("⚠ Damaged",   Palette.CHIP_WARNING_BG, Palette.CHIP_WARNING_FG),
}


class ManageCopiesDialog(tk.Toplevel):
    """Modal dialog listing every copy of a book with edit-serial action."""

    COLUMNS = [
        ("id",       "ID",              50,  "center"),
        ("serial",   "Serial #",       140,  "center"),
        ("status",   "Status",         120,  "center"),
        ("borrower", "Current Borrower", 220, "w"),
        ("due",      "Due Date",        110, "center"),
    ]

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        book_id: int,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._book_id = book_id
        book = services.books.get(book_id)
        self._book_title = book.title if book else f"Book #{book_id}"

        self.title(f"Copies — {self._book_title}")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text=f"📦  {self._book_title}",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Manage physical copies — rename serials, preview labels",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Action row + Close (bottom) ──────────────────────────────────────
        make_divider(self).pack(fill="x", side="bottom")
        actions = tk.Frame(self, bg=Palette.SURFACE, padx=18, pady=12)
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="✏  Rename Serial", style="Primary.TButton",
                   command=self._rename_selected).pack(side="left")
        ttk.Button(actions, text="🏷️  Label", style="Purple.TButton",
                   command=self._view_label).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="↻  Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Close", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=18, pady=14)
        body.pack(fill="both", expand=True)

        # Hint card
        hint_card = tk.Frame(body, bg=Palette.PRIMARY_SOFT,
                             highlightthickness=1,
                             highlightbackground=Palette.PRIMARY_GLOW)
        hint_card.pack(fill="x", pady=(0, 12))
        tk.Label(
            hint_card,
            text=(
                "  💡  Double-click a row (or select + Rename) to relabel a copy.  "
                "Each serial must be unique across the entire library."
            ),
            bg=Palette.PRIMARY_SOFT, fg=Palette.PRIMARY,
            font=small_font(), padx=8, pady=8,
            justify="left", wraplength=680,
        ).pack(anchor="w")

        # Treeview
        container, self._tree = build_treeview(body, self.COLUMNS, height=12)
        container.pack(fill="both", expand=True)

        # Extra row tags for per-status colouring
        self._tree.tag_configure(
            "available", foreground=Palette.STATUS_AVAIL)
        self._tree.tag_configure(
            "borrowed", foreground=Palette.STATUS_ACTIVE)
        self._tree.tag_configure(
            "lost", foreground=Palette.STATUS_OVERDUE)
        self._tree.tag_configure(
            "damaged", foreground=Palette.WARNING)

        self._tree.bind("<Double-1>", self._on_double_click)

        center_window(self, parent, width=760, height=480)
        self.bind("<Escape>", lambda e: self.destroy())

        self.refresh()
        self.wait_window(self)

    # ─────────────────────────────────────────── data ──

    def refresh(self) -> None:
        for r in self._tree.get_children():
            self._tree.delete(r)
        copies = self._services.books.list_copies_with_borrower(self._book_id)
        for i, c in enumerate(copies):
            stripe = "even" if i % 2 else "odd"
            status_text, _bg, _fg = _STATUS_DISPLAY.get(
                c.status,
                (c.status.capitalize(), Palette.CHIP_NEUTRAL_BG, Palette.CHIP_NEUTRAL_FG),
            )
            self._tree.insert(
                "", "end",
                iid=str(c.id),
                values=(
                    c.id,
                    c.serial_number,
                    status_text,
                    c.borrower_name or "—",
                    c.borrower_due_on or "—",
                ),
                tags=(stripe, c.status),
            )

    # ─────────────────────────────────────────── actions ──

    def _selected_copy_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo(
                "Select a copy", "Please select a copy first.", parent=self)
            return None
        return int(sel[0])

    def _on_double_click(self, _event: tk.Event) -> None:
        if self._tree.selection():
            self._rename_selected()

    def _rename_selected(self) -> None:
        copy_id = self._selected_copy_id()
        if copy_id is None:
            return
        current = self._tree.set(str(copy_id), "serial")
        new_serial = simpledialog.askstring(
            "Rename Serial",
            f"New serial for  {current}:",
            initialvalue=current,
            parent=self,
        )
        if new_serial is None:
            return
        new_serial = new_serial.strip()
        if not new_serial or new_serial == current:
            return
        try:
            self._services.books.update_copy_serial(copy_id, new_serial)
            self.refresh()
        except LibraryError as e:
            messagebox.showerror("Cannot rename", str(e), parent=self)

    def _view_label(self) -> None:
        copy_id = self._selected_copy_id()
        if copy_id is None:
            return
        serial = self._tree.set(str(copy_id), "serial")
        book = self._services.books.get(self._book_id)
        category_name = None
        if book and book.category_id:
            cat = self._services.categories.get(book.category_id)
            category_name = cat.name if cat else None
        from .label_preview_dialog import LabelPreviewDialog
        LabelPreviewDialog(
            self, self._services,
            serial_number=serial,
            category_name=category_name,
        )
