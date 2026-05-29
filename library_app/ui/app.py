from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from ..config import WINDOW_GEOMETRY, WINDOW_MIN_SIZE, WINDOW_TITLE
from ..services import Services
from .tabs import AdminTab, BooksTab, LoansTab
from .theme import setup_styles


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

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.books_tab = BooksTab(self.notebook, services)
        self.loans_tab = LoansTab(
            self.notebook, services, on_change=self.books_tab.refresh
        )
        self.admin_tab = AdminTab(
            self.notebook, services, on_change=self._on_admin_change
        )

        self.notebook.add(self.books_tab, text="  Books  ")
        self.notebook.add(self.loans_tab, text="  Loans  ")
        self.notebook.add(self.admin_tab, text="  Admin  ")

        # Refresh the tab the user switches to. Belt-and-braces: even if an
        # explicit `on_change` propagation is missed for any reason, the act
        # of viewing a tab guarantees it shows current state.
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.status = ttk.Label(
            self, text=" Ready  •  Library Management System",
            style="Status.TLabel", anchor="w",
        )
        self.status.pack(fill="x", side="bottom")

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
        _log.debug("Tab switched → %s refreshed",
                   type(current).__name__)
