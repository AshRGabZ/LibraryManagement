"""A vertically scrollable container.

Standard Tk pattern: a Canvas hosts an inner Frame via `create_window`; a
vertical Scrollbar drives the canvas. Callers pack their content into
`.body` exactly as they would into any frame.

Behaviour that makes it feel like a normal app:
  • The scrollbar auto-hides when everything already fits, and appears only
    when the content is taller than the viewport.
  • The inner frame's width always tracks the canvas width, so content fills
    horizontally and only *vertical* scrolling ever happens.
  • The mouse wheel scrolls the canvas while the pointer is over it, and is
    unbound on leave so it never hijacks scrolling elsewhere.

This is used for genuinely tall, stacked content (e.g. the dashboard). For
plain data-list views, prefer reserving fixed chrome and letting the inner
treeview scroll — don't nest two vertical scroll regions.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

from ..theme import Palette


class ScrollableFrame(ttk.Frame):
    """Container exposing a scrollable `.body` frame.

    Example:
        sf = ScrollableFrame(parent)
        sf.pack(fill="both", expand=True)
        tk.Label(sf.body, text="…").pack()
    """

    def __init__(self, parent: tk.Widget, *, bg: str = Palette.BG) -> None:
        super().__init__(parent)

        self._canvas = tk.Canvas(
            self, bg=bg, highlightthickness=0, borderwidth=0
        )
        self._vsb = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._on_scroll_set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        # Scrollbar is grid-managed but starts hidden; shown on demand.
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._vsb.grid_remove()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # The frame callers pack into.
        self.body = tk.Frame(self._canvas, bg=bg)
        self._window = self._canvas.create_window(
            (0, 0), window=self.body, anchor="nw"
        )

        # Keep scrollregion in sync with body height; keep body width == canvas.
        self.body.bind("<Configure>", self._on_body_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Wheel support only while the pointer is over the region.
        self._canvas.bind("<Enter>", self._bind_wheel)
        self._canvas.bind("<Leave>", self._unbind_wheel)

    # ----------------------------------------------------------- geometry #

    def _on_body_configure(self, _event: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._sync_scrollbar_visibility()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        # Force the inner frame to fill the canvas width (vertical scroll only).
        self._canvas.itemconfigure(self._window, width=event.width)
        self._sync_scrollbar_visibility()

    def _on_scroll_set(self, first: str, last: str) -> None:
        # Drive the scrollbar, and hide it when the whole range is visible.
        self._vsb.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._vsb.grid_remove()
        else:
            self._vsb.grid()

    def _sync_scrollbar_visibility(self) -> None:
        # Recompute after layout settles so first/last reflect real sizes.
        self.after_idle(lambda: self._on_scroll_set(*self._canvas.yview()))

    # -------------------------------------------------------------- wheel #

    def _bind_wheel(self, _event: tk.Event) -> None:
        # macOS/Windows deliver <MouseWheel>; X11 uses Button-4/5.
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)
        self._canvas.bind_all("<Button-4>", self._on_wheel)
        self._canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    #: Inner widget classes that scroll themselves on the wheel. When the
    #: pointer is over one of these, it must keep the wheel — the outer panel
    #: should NOT also scroll (otherwise a treeview/listbox inside the panel
    #: drags the whole panel along).
    _INNER_SCROLLERS = ("Treeview", "Listbox", "Text")

    def _should_handle(self, widget: tk.Misc | None) -> bool:
        """Whether a (global) wheel event belongs to this panel.

        Walk from the event's widget up to this ScrollableFrame and bail if:
          • we never reach it — the event is over another window (e.g. a modal
            dialog on top), so it isn't ours; or
          • we first pass through an inner widget that scrolls itself
            (treeview / listbox / text) — let that widget keep the wheel.
        """
        node = widget
        while node is not None:
            if node is self:
                return True
            try:
                if node.winfo_class() in self._INNER_SCROLLERS:
                    return False
            except tk.TclError:
                return False
            node = getattr(node, "master", None)
        return False

    def _on_wheel(self, event: tk.Event) -> None:
        # The wheel binding is global (bind_all); only act when this event is
        # genuinely ours (see _should_handle for the dialog / inner-scroller
        # exclusions).
        if not self._should_handle(getattr(event, "widget", None)):
            return
        # Don't scroll if everything already fits.
        first, last = self._canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            # Windows delta is ±120 multiples; macOS sends small integers.
            raw = event.delta
            if sys.platform == "darwin":
                delta = -1 if raw > 0 else 1
            else:
                delta = -1 if raw > 0 else 1
        self._canvas.yview_scroll(delta, "units")

    # ------------------------------------------------------------- lifecycle #

    def destroy(self) -> None:  # type: ignore[override]
        # The wheel handlers are bound globally via bind_all while hovered.
        # In a transient dialog the widget may be destroyed (e.g. Escape) while
        # still bound; drop the global bindings first so a later wheel event
        # can't fire on this now-dead canvas.
        try:
            self._unbind_wheel(None)  # type: ignore[arg-type]
        except tk.TclError:
            pass
        super().destroy()
