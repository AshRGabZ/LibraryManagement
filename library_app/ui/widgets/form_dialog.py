from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Sequence

from ..theme import Palette, base_font


class FormDialog(tk.Toplevel):
    """Simple labelled-field dialog. Result available in `self.result` (dict or None)."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        fields: Sequence[tuple[str, str]],
        initial: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        self.configure(bg=Palette.SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: dict | None = None
        self._entries: dict[str, ttk.Entry] = {}
        initial = initial or {}

        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Header.TLabel").pack(
            anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        for i, (key, label) in enumerate(fields):
            tk.Label(body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                     font=base_font()).grid(row=i, column=0, sticky="w",
                                            pady=(6, 2))
            entry = ttk.Entry(body, width=38, font=base_font())
            entry.grid(row=i, column=1, pady=(6, 2), padx=(12, 0), sticky="ew")
            if key in initial and initial[key] is not None:
                entry.insert(0, str(initial[key]))
            self._entries[key] = entry

        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save", style="Primary.TButton",
                   command=self._on_ok).pack(side="right")

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        list(self._entries.values())[0].focus_set()

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.wait_window(self)

    def _on_ok(self) -> None:
        self.result = {k: e.get().strip() for k, e in self._entries.items()}
        self.destroy()
