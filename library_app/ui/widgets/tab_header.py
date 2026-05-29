from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import Palette


class TabHeader(ttk.Frame):
    """Dark-banner header used at the top of every main tab."""

    def __init__(self, parent: tk.Widget, icon: str, title: str, subtitle: str) -> None:
        super().__init__(parent, style="Header.TFrame")
        inner = ttk.Frame(self, style="Header.TFrame", padding=(20, 16))
        inner.pack(fill="x")
        ttk.Label(inner, text=f"{icon}  {title}",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner, text=subtitle,
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))
