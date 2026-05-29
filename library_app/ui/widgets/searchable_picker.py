from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Sequence

from ..theme import Palette, base_font


class SearchablePicker(tk.Frame):
    """Search entry + scrollable listbox. Exposes `selected_id` of chosen item.

    Items are arbitrary mappings; `formatter(item)` returns `(label, disabled)`.
    """

    def __init__(
        self,
        parent: tk.Widget,
        items: Sequence[Any],
        formatter: Callable[[Any], tuple[str, bool]],
        search_keys: Sequence[str],
        placeholder: str = "Search…",
        height: int = 8,
    ) -> None:
        super().__init__(parent, bg=Palette.SURFACE)
        self.items: list[Any] = list(items)
        self.formatter = formatter
        self.search_keys = search_keys
        self._filtered: list[Any] = []
        self.selected_id: int | None = None

        self.search_var = tk.StringVar()

        entry_wrap = tk.Frame(self, bg=Palette.BORDER, bd=0)
        entry_wrap.pack(fill="x")
        entry = tk.Entry(entry_wrap, textvariable=self.search_var,
                         font=base_font(), relief="flat", bd=0,
                         bg=Palette.SURFACE, fg=Palette.TEXT,
                         insertbackground=Palette.TEXT)
        entry.pack(fill="x", padx=1, pady=1, ipady=6, ipadx=8)
        self.entry = entry

        self._placeholder = placeholder
        self._placeholder_active = True
        entry.insert(0, placeholder)
        entry.config(fg=Palette.MUTED)

        def on_focus_in(_e: tk.Event) -> None:
            if self._placeholder_active:
                entry.delete(0, "end")
                entry.config(fg=Palette.TEXT)
                self._placeholder_active = False

        def on_focus_out(_e: tk.Event) -> None:
            if not self.search_var.get().strip():
                self._placeholder_active = True
                entry.delete(0, "end")
                entry.insert(0, placeholder)
                entry.config(fg=Palette.MUTED)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

        list_wrap = tk.Frame(self, bg=Palette.BORDER, bd=0)
        list_wrap.pack(fill="both", expand=True, pady=(6, 0))

        self.listbox = tk.Listbox(
            list_wrap, height=height, font=base_font(),
            relief="flat", bd=0, bg=Palette.SURFACE, fg=Palette.TEXT,
            selectbackground=Palette.PRIMARY, selectforeground="white",
            activestyle="none", highlightthickness=0, exportselection=False,
        )
        self.listbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        sb = ttk.Scrollbar(list_wrap, orient="vertical",
                           command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.search_var.trace_add("write", lambda *_: self.refilter())
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.refilter()

    def set_items(self, items: Sequence[Any]) -> None:
        """Replace the item list (used when external filters change)."""
        self.items = list(items)
        self.refilter()

    def _query(self) -> str:
        if self._placeholder_active:
            return ""
        return self.search_var.get().strip().lower()

    def refilter(self) -> None:
        q = self._query()
        self.listbox.delete(0, "end")
        self._filtered = []
        for it in self.items:
            blob = " ".join(str(self._access(it, k) or "")
                            for k in self.search_keys).lower()
            if q and q not in blob:
                continue
            label, disabled = self.formatter(it)
            self.listbox.insert("end", label)
            self._filtered.append(it)
            if disabled:
                self.listbox.itemconfig("end", fg=Palette.MUTED)
        self.selected_id = None

    @staticmethod
    def _access(item: Any, key: str) -> Any:
        """Support both attribute access (dataclasses) and mapping access (rows)."""
        if hasattr(item, key):
            return getattr(item, key)
        try:
            return item[key]
        except (TypeError, KeyError):
            return None

    def _on_select(self, _e: tk.Event) -> None:
        sel = self.listbox.curselection()
        if sel:
            picked = self._filtered[sel[0]]
            self.selected_id = self._access(picked, "id")
