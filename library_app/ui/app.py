from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ..config import WINDOW_GEOMETRY, WINDOW_MIN_SIZE, WINDOW_TITLE
from ..services import Services
from .tabs import AdminTab, BooksTab, LoansTab
from .theme import Palette, small_font, setup_styles


_log = logging.getLogger(__name__)


class LibraryApp(tk.Tk):
    """Top-level Tk window. Owns the Services container and wires up the tabs."""

    def __init__(self, services: Services) -> None:
        super().__init__()
        self._services = services
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_GEOMETRY)
        self.minsize(*WINDOW_MIN_SIZE)
        setup_styles(self)

        # ── Status bar — pack FIRST so it's always visible at the bottom.
        # In Tkinter pack geometry, bottom-anchored widgets must be packed
        # before any fill="both"/expand=True widget, otherwise the expanding
        # widget consumes all space and the status bar gets pushed off-screen.
        status_bar = tk.Frame(self, bg=Palette.HEADER_BG)
        status_bar.pack(fill="x", side="bottom")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.books_tab = BooksTab(self.notebook, services)
        self.loans_tab = LoansTab(
            self.notebook, services, on_change=self.books_tab.refresh
        )
        self.admin_tab = AdminTab(
            self.notebook, services, on_change=self._on_admin_change
        )

        self.notebook.add(self.books_tab, text="  📚  Books  ")
        self.notebook.add(self.loans_tab, text="  🔄  Loans  ")
        self.notebook.add(self.admin_tab, text="  ⚙️  Admin  ")

        # Refresh the tab the user switches to.
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Left: app name + ready indicator
        self._status_left = ttk.Label(
            status_bar,
            text="  ✦  GHCC Library Management System  •  Ready",
            style="Status.TLabel",
            anchor="w",
        )
        self._status_left.pack(side="left", fill="x", expand=True)

        # Right: live clock (updates every second independently of TabHeader)
        self._clock_label = ttk.Label(
            status_bar,
            text="",
            style="StatusClock.TLabel",
            anchor="e",
        )
        self._clock_label.pack(side="right")

        self._tick_clock()

    # ─────────────────────────────────────────── clock ──
    def _tick_clock(self) -> None:
        try:
            now = datetime.now()
            self._clock_label.configure(
                text=now.strftime("  🕐  %H:%M:%S  •  %d %b %Y  ")
            )
            self.after(1000, self._tick_clock)
        except tk.TclError:
            pass  # window was destroyed

    # ─────────────────────────────────────────── helpers ──
    def set_status(self, msg: str) -> None:
        """Update the left status message (call after operations)."""
        try:
            self._status_left.configure(text=f"  ✦  {msg}")
        except tk.TclError:
            pass

    # ─────────────────────────────────────────── callbacks ──
    def _on_admin_change(self) -> None:
        """Admin tab modified data; keep dependent tabs in sync."""
        self.books_tab.refresh_filters()
        self.books_tab.refresh()
        self.loans_tab.refresh()

    def _on_tab_changed(self, _event: tk.Event) -> None:
        """Refresh the now-visible tab so it always shows current DB state."""
        try:
            current = self.notebook.nametowidget(self.notebook.select())
        except (tk.TclError, KeyError):
            return
        if current is self.books_tab:
            self.books_tab.refresh_filters()
            self.books_tab.refresh()
        elif current is self.loans_tab:
            self.loans_tab.refresh()
        elif current is self.admin_tab:
            self.admin_tab.refresh()
        _log.debug("Tab switched → %s refreshed", type(current).__name__)
