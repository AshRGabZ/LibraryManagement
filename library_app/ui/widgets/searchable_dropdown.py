"""A combobox-like field whose dropdown filters live as you type.

``ttk.Combobox`` can't do this: when its dropdown is posted it takes a global
keyboard grab, so the next keystroke never reaches the entry and typing stops.
This widget sidesteps that entirely.

Design:
  • The field is a normal ``ttk.Entry`` (+ a ▾ button) — typing always works.
  • The match list is a ``tk.Listbox`` *placed inside the same toplevel* and
    raised with ``lift()`` so it overlays whatever sits below the field.
    Because it lives in the same window (not an ``overrideredirect`` popup),
    mouse clicks land on it on every platform **without** needing a grab — so
    the entry keeps focus and you can keep typing while the list updates.
  • As you type, the list is filtered to entries that *contain* the text
    (case-insensitive) and only the matches are shown.

Keyboard: ``Down`` jumps into the list, ``Return`` accepts the highlighted (or
first) match, ``Esc`` closes. Mouse: click a row to pick it; the ▾ button
toggles the full list.

Drop-in for our forms — pass a ``textvariable`` and call
``set_completion_list``; read the value off the same ``StringVar`` as before.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable

from ..theme import Palette, base_font


#: Sentinel row letting the user clear the field back to "no value".
_NONE_LABEL = "— None —"

#: Keys that must not trigger a re-filter (navigation / modifiers / commit).
_SKIP_KEYS = frozenset({
    "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next",
    "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L",
    "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Caps_Lock",
    "Win_L", "Win_R",
})


class SearchableDropdown(tk.Frame):
    """Entry + filtering dropdown list. Pairs with a ``textvariable``."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        textvariable: tk.StringVar | None = None,
        width: int = 32,
        font=None,
        max_visible: int = 8,
        allow_none: bool = True,
    ) -> None:
        super().__init__(parent, bg=Palette.SURFACE)
        self._var = textvariable if textvariable is not None else tk.StringVar()
        self._all: list[str] = []
        self._max_visible = max_visible
        self._allow_none = allow_none
        self._font = font or base_font()
        self._popup: tk.Frame | None = None
        self._listbox: tk.Listbox | None = None
        self._sb: ttk.Scrollbar | None = None
        # Track open-state explicitly: winfo_ismapped() lags a place() until the
        # event loop spins, so a quick toggle could misread it.
        self._open = False

        self._entry = ttk.Entry(self, textvariable=self._var, width=width,
                                font=self._font)
        self._entry.pack(side="left", fill="x", expand=True)
        self._arrow = ttk.Button(self, text="▼", width=2,
                                 style="Compact.TButton", command=self._toggle)
        self._arrow.pack(side="left", padx=(2, 0))

        self._entry.bind("<KeyRelease>", self._on_keyrelease)
        self._entry.bind("<Down>", self._enter_list)
        self._entry.bind("<Return>", self._on_return)
        self._entry.bind("<Escape>", lambda e: self._close())
        # Defer the outside-click close so a click *into* the list/scrollbar
        # registers first (that click fires the entry's FocusOut).
        self._entry.bind("<FocusOut>",
                         lambda e: self.after(120, self._close_if_outside))

    # ── public API ───────────────────────────────────────────────────────
    def set_completion_list(self, values: Iterable) -> None:
        """Replace the option set (stored sorted, blanks dropped)."""
        self._all = sorted(
            {str(v) for v in values if str(v) != ""}, key=str.lower
        )

    def get(self) -> str:
        return self._var.get()

    def set(self, value: str) -> None:
        self._var.set(value)

    # ── filtering ────────────────────────────────────────────────────────
    def _matches(self, typed: str) -> list[str]:
        if not typed:
            return list(self._all)
        low = typed.lower()
        return [v for v in self._all if low in v.lower()]

    def _on_keyrelease(self, event: tk.Event) -> None:
        if event.keysym in _SKIP_KEYS:
            return
        self._show(self._matches(self._var.get()))

    # ── popup lifecycle ──────────────────────────────────────────────────
    def _ensure_popup(self) -> None:
        if self._popup is not None:
            return
        top = self.winfo_toplevel()
        self._popup = tk.Frame(top, bg=Palette.BORDER,
                               highlightthickness=1,
                               highlightbackground=Palette.PRIMARY)
        self._listbox = tk.Listbox(
            self._popup, activestyle="none", font=self._font,
            bd=0, highlightthickness=0, relief="flat", cursor="hand2",
            bg=Palette.SURFACE, fg=Palette.TEXT,
            selectbackground=Palette.PRIMARY, selectforeground=Palette.PRIMARY_FG,
            exportselection=False,
        )
        self._sb = ttk.Scrollbar(self._popup, orient="vertical",
                                 command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=self._sb.set)
        self._listbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        self._listbox.bind("<ButtonRelease-1>", self._on_click)
        self._listbox.bind("<Double-Button-1>", self._on_click)
        self._listbox.bind("<Return>", self._on_return)
        self._listbox.bind("<Escape>",
                           lambda e: (self._close(), self._entry.focus_set()))

    def _show(self, items: list[str]) -> None:
        self._ensure_popup()
        include_none = self._allow_none and not self._var.get().strip()
        rows = ([_NONE_LABEL] if include_none else []) + items
        if not rows:
            self._close()
            return

        lb = self._listbox
        assert lb is not None and self._sb is not None
        lb.delete(0, tk.END)
        for row in rows:
            lb.insert(tk.END, row)
        lb.configure(height=min(len(rows), self._max_visible))
        if len(rows) > self._max_visible:
            self._sb.pack(side="right", fill="y")
        else:
            self._sb.pack_forget()

        # Position directly under the field, in the toplevel's coordinate space.
        top = self.winfo_toplevel()
        top.update_idletasks()
        x = self.winfo_rootx() - top.winfo_rootx()
        y = self.winfo_rooty() - top.winfo_rooty() + self.winfo_height()
        self._popup.place(x=x, y=y, width=self.winfo_width())
        self._popup.lift()
        self._open = True

    def _close(self) -> None:
        self._open = False
        if self._popup is not None:
            self._popup.place_forget()

    def _close_if_outside(self) -> None:
        """Close unless focus is still within this field or its dropdown."""
        try:
            foc: tk.Misc | None = self.focus_get()
        except KeyError:
            foc = None
        w = foc
        while w is not None:
            if w is self or w is self._popup:
                return
            w = getattr(w, "master", None)
        self._close()

    # ── selection ────────────────────────────────────────────────────────
    def _choose(self, text: str) -> None:
        self._var.set("" if text == _NONE_LABEL else text)
        self._close()
        self._entry.focus_set()
        self._entry.icursor(tk.END)

    def _on_click(self, event: tk.Event) -> str:
        lb = self._listbox
        assert lb is not None
        idx = lb.nearest(event.y)
        if 0 <= idx < lb.size():
            self._choose(lb.get(idx))
        return "break"

    def _on_return(self, event: tk.Event):
        if self._open:
            lb = self._listbox
            assert lb is not None
            if lb.size() > 0:
                sel = lb.curselection()
                self._choose(lb.get(sel[0] if sel else 0))
                return "break"
        return None

    def _enter_list(self, event: tk.Event) -> str:
        if not self._open:
            self._show(self._matches(self._var.get()))
        lb = self._listbox
        if lb is not None and lb.size() > 0:
            lb.focus_set()
            lb.selection_clear(0, tk.END)
            lb.selection_set(0)
            lb.activate(0)
            lb.see(0)
        return "break"

    def _toggle(self) -> None:
        if self._open:
            self._close()
        else:
            self._show(self._matches(self._var.get()))
            self._entry.focus_set()
