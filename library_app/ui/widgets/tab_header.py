from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ..theme import Palette, base_font, small_font


class TabHeader(ttk.Frame):
    """Branded banner used at the top of every main tab.

    A deep indigo band carries the title + subtitle, finished with a thin
    brighter accent strip beneath it. A live clock badge sits on the right
    side of the header, updating every second.
    """

    _ACCENT_HEIGHT = 4

    def __init__(self, parent: tk.Widget, icon: str, title: str, subtitle: str) -> None:
        super().__init__(parent, style="Header.TFrame")

        inner = ttk.Frame(self, style="Header.TFrame", padding=(24, 10, 20, 10))
        inner.pack(fill="x")
        inner.columnconfigure(0, weight=1)

        # ---- Left: icon + title + subtitle
        left = ttk.Frame(inner, style="Header.TFrame")
        left.grid(row=0, column=0, sticky="w")

        ttk.Label(left, text=f"{icon}  {title}",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(left, text=subtitle,
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        # ---- Right: live date + time badge
        right = ttk.Frame(inner, style="Header.TFrame")
        right.grid(row=0, column=1, sticky="e")

        self._date_label = tk.Label(
            right, text="", bg=Palette.HEADER_BADGE_BG,
            fg=Palette.HEADER_ACCENT, font=small_font(),
            padx=12, pady=5,
        )
        self._date_label.pack(anchor="e")

        self._time_label = tk.Label(
            right, text="", bg=Palette.HEADER_BG,
            fg="#818cf8", font=(small_font()[0], small_font()[1] + 1),
            padx=12, pady=2,
        )
        self._time_label.pack(anchor="e")

        self._update_clock()

        # Accent strip — a 4px indigo-500 line that reads as a brand underline.
        accent = ttk.Frame(self, style="Accent.TFrame", height=self._ACCENT_HEIGHT)
        accent.pack(fill="x")
        accent.pack_propagate(False)

    def _update_clock(self) -> None:
        """Update the date and time labels every second."""
        now = datetime.now()
        # IMPORTANT: keep emoji OUT of the strftime format string. On Windows,
        # datetime.strftime routes the format through the C runtime's locale
        # codec (often cp1252), which can't encode emoji and raises
        # UnicodeEncodeError. Concatenating in Python avoids that codec path.
        self._date_label.configure(
            text="  📅  " + now.strftime("%A, %d %B %Y") + "  "
        )
        self._time_label.configure(
            text="  🕐  " + now.strftime("%H:%M:%S") + "  "
        )
        # Schedule next tick; cancel-safe: if the widget is destroyed
        # the after callback will fire but configure will silently fail.
        try:
            self.after(1000, self._update_clock)
        except tk.TclError:
            pass
