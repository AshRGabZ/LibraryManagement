from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Sequence

from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider


class FormDialog(tk.Toplevel):
    """Polished labelled-field dialog.

    Result available in `self.result` (dict or None on cancel).
    Fields is a sequence of (key, label) pairs. `initial` pre-fills values.
    """

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

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text=title,
                  style="Header.TLabel").pack(anchor="w")

        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=28, pady=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        for i, (key, label) in enumerate(fields):
            # Field label
            tk.Label(
                body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                font=small_font(),
            ).grid(row=i * 2, column=0, columnspan=2, sticky="w",
                   pady=(10 if i > 0 else 0, 2))

            # Entry with inner border simulation
            entry_wrap = tk.Frame(body, bg=Palette.BORDER)
            entry_wrap.grid(row=i * 2 + 1, column=0, columnspan=2,
                            sticky="ew", ipady=0)
            entry = tk.Entry(
                entry_wrap, width=38, font=base_font(),
                relief="flat", bd=0,
                bg=Palette.SURFACE, fg=Palette.TEXT,
                insertbackground=Palette.PRIMARY,
            )
            entry.pack(fill="x", padx=1, pady=1, ipady=8, ipadx=10)

            # Focus-ring simulation: border turns indigo on focus
            def _focus_in(e: tk.Event, w=entry_wrap) -> None:
                w.configure(bg=Palette.BORDER_FOCUS)

            def _focus_out(e: tk.Event, w=entry_wrap) -> None:
                w.configure(bg=Palette.BORDER)

            entry.bind("<FocusIn>", _focus_in)
            entry.bind("<FocusOut>", _focus_out)

            if key in initial and initial[key] is not None:
                entry.insert(0, str(initial[key]))
            self._entries[key] = entry

        # ── Divider ──────────────────────────────────────────────────────────
        divider = make_divider(self)
        divider.pack(fill="x", side="bottom")

        # ── Buttons ──────────────────────────────────────────────────────────
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")

        ttk.Button(btns, text="✓  Save", style="Primary.TButton",
                   command=self._on_ok).pack(side="right")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        list(self._entries.values())[0].focus_set()

        center_window(self, parent,
                      width=460, height=80 + len(fields) * 72 + 80)
        self.wait_window(self)

    def _on_ok(self) -> None:
        self.result = {k: e.get().strip() for k, e in self._entries.items()}
        self.destroy()
