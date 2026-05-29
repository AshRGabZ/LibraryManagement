"""Date entry with a popup calendar.

Pure stdlib (no `tkcalendar` dependency) so packaging stays self-contained.
The widget is two things bundled: a free-form `Entry` for typing, plus a 📅
button that opens a `CalendarPopup` for clicking. Both write to the same
StringVar, so callers see a single ISO date string regardless of input mode.

Implementation notes:
- The 6×7 cell grid is created once in __init__ and reused on every month
  navigation — only the text and color of each cell is updated. This avoids
  destroying/recreating 42 Tk widgets per click.
- Dismissal uses a root-level `<Button-1>` bind to detect clicks outside the
  popup (more reliable across platforms than `<FocusOut>` heuristics).
"""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Callable

from ..theme import Palette, base_font, heading_font


_DAY_HEADERS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# Layout constants — kept here so the file is the single source of truth.
_GRID_ROWS = 6   # Months span at most 6 calendar weeks
_GRID_COLS = 7
_CELL_WIDTH = 4
_CELL_PADY = 4


class DateEntry(tk.Frame):
    """ISO-date Entry + 📅 button.

    `.get()` returns the raw text; `.get_date()` returns a parsed `date | None`.
    Pass `initial=None` (the default) to start blank — useful for optional
    filters. Pass a `date` to pre-fill.

    `on_change` (optional) fires whenever the field's value changes — typed
    or picked from the calendar. Use it to wire up live filtering.
    """

    def __init__(
        self,
        parent: tk.Widget,
        initial: date | None = None,
        width: int = 12,
        on_change: "Callable[[], None] | None" = None,
        placeholder: str = "YYYY-MM-DD",
    ) -> None:
        super().__init__(parent, bg=Palette.SURFACE)
        initial_text = initial.isoformat() if initial is not None else ""
        self._var = tk.StringVar(value=initial_text)
        self._placeholder = placeholder

        self._entry = ttk.Entry(self, textvariable=self._var, width=width,
                                font=base_font())
        self._entry.pack(side="left")
        ttk.Button(self, text="📅", style="Compact.TButton", width=2,
                   command=self._open_popup).pack(side="left", padx=(2, 0))

        if on_change is not None:
            self._var.trace_add("write", lambda *_: on_change())

    def get(self) -> str:
        return self._var.get().strip()

    def get_date(self) -> date | None:
        text = self.get()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    def set_date(self, d: date | None) -> None:
        self._var.set(d.isoformat() if d else "")

    def clear(self) -> None:
        self._var.set("")

    def _open_popup(self) -> None:
        # If the entry is empty, anchor the calendar on today.
        CalendarPopup(
            self, initial=self.get_date() or date.today(),
            on_select=self.set_date,
        )


class CalendarPopup(tk.Toplevel):
    """Modal month-grid calendar.

    Day cells are created once and updated in place — month navigation is
    O(42) label updates, not 42 widget creations.
    """

    def __init__(
        self,
        parent: tk.Widget,
        initial: date | None = None,
        on_select: Callable[[date], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_select = on_select or (lambda _d: None)
        self.overrideredirect(True)  # frameless — feels like a dropdown
        self.configure(bg=Palette.SURFACE, highlightthickness=1,
                       highlightbackground=Palette.BORDER)
        self.transient(parent.winfo_toplevel())

        # grab_set is essential on macOS: without it, real OS mouse clicks on
        # an `overrideredirect` toplevel are routed to the underlying window
        # instead of the popup, so date cells never receive Button-1.
        #
        # IMPORTANT — Tk does NOT auto-restore a parent dialog's grab when
        # this popup releases its own. We capture the previous grab here and
        # re-assert it in `destroy()`, otherwise the parent dialog's fields
        # become unresponsive after the user picks a date.
        self._previous_grab = self.grab_current()
        self.grab_set()

        d = initial or date.today()
        self._year = d.year
        self._month = d.month
        self._selected = d

        # ----------------------------------------------------------- header
        header = tk.Frame(self, bg=Palette.HEADER_BG)
        header.pack(fill="x")
        ttk.Button(header, text="◀", style="Neutral.TButton",
                   width=3, command=self._prev_month
                   ).pack(side="left", padx=4, pady=4)
        self._title_var = tk.StringVar()
        tk.Label(header, textvariable=self._title_var,
                 bg=Palette.HEADER_BG, fg=Palette.HEADER_FG,
                 font=heading_font(), padx=8
                 ).pack(side="left", expand=True)
        ttk.Button(header, text="▶", style="Neutral.TButton",
                   width=3, command=self._next_month
                   ).pack(side="right", padx=4, pady=4)

        # --------------------------------------------------- day-of-week row
        dow = tk.Frame(self, bg=Palette.SURFACE)
        dow.pack(fill="x", padx=4, pady=(6, 2))
        for i, name in enumerate(_DAY_HEADERS):
            fg = Palette.DANGER if i >= 5 else Palette.MUTED
            tk.Label(dow, text=name, bg=Palette.SURFACE, fg=fg,
                     font=base_font(), width=_CELL_WIDTH
                     ).grid(row=0, column=i, padx=1)

        # ----------------------------------------------- pre-built day cells
        # Create once; _render() will just update text/colors.
        grid = tk.Frame(self, bg=Palette.SURFACE)
        grid.pack(padx=4, pady=(0, 6))
        self._cells: list[tk.Label] = []
        self._cell_dates: list[date | None] = [None] * (_GRID_ROWS * _GRID_COLS)
        for r in range(_GRID_ROWS):
            for c in range(_GRID_COLS):
                cell = tk.Label(
                    grid, text="", bg=Palette.SURFACE, fg=Palette.TEXT,
                    font=base_font(), width=_CELL_WIDTH,
                    padx=2, pady=_CELL_PADY, cursor="hand2",
                    relief="flat", borderwidth=0,
                )
                cell.grid(row=r, column=c, padx=1, pady=1)
                idx = r * _GRID_COLS + c
                cell.bind("<Button-1>", lambda e, i=idx: self._cell_clicked(i))
                cell.bind("<Enter>", lambda e, i=idx: self._cell_hover(i, True))
                cell.bind("<Leave>", lambda e, i=idx: self._cell_hover(i, False))
                self._cells.append(cell)

        # --------------------------------------------------------- footer
        footer = tk.Frame(self, bg=Palette.SURFACE)
        footer.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(footer, text="Today", style="Neutral.TButton",
                   command=self._pick_today).pack(side="left")
        ttk.Button(footer, text="Close", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")

        # ------------------------------------------- dismissal & nav binds
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Left>",  lambda e: self._prev_month())
        self.bind("<Right>", lambda e: self._next_month())

        # Click-outside detection — bind on the *parent dialog's* toplevel so
        # we catch clicks anywhere in that window (not just on this popup's
        # immediate parent widget). The bind is unregistered in `destroy()`.
        #
        # IMPORTANT: do NOT name this attribute `self._root`. `Misc._root()`
        # is an inherited method tkinter calls during event substitution; if
        # we shadow it with an attribute, every event raises a TypeError that
        # propagates as "object is not callable".
        self._click_target = parent.winfo_toplevel()
        self._click_bind_id = self._click_target.bind(
            "<Button-1>", self._on_global_click, add="+"
        )

        self._render()
        self._position_near(parent)

    # ---------------------------------------------------------------- lifecycle

    def destroy(self) -> None:  # type: ignore[override]
        try:
            self._click_target.unbind("<Button-1>", self._click_bind_id)
        except (tk.TclError, AttributeError):
            pass
        # Release our own grab and restore the parent dialog's grab BEFORE
        # destroying — otherwise Tk leaves the application ungrabbed and any
        # widgets we passed focus through become unresponsive.
        try:
            self.grab_release()
        except tk.TclError:
            pass
        previous = self._previous_grab
        super().destroy()
        if previous is not None:
            try:
                previous.grab_set()
                previous.focus_force()
            except tk.TclError:
                pass

    def _on_global_click(self, event: tk.Event) -> None:
        # If the click happened outside this popup's window, close.
        x, y = event.x_root, event.y_root
        x0 = self.winfo_rootx()
        y0 = self.winfo_rooty()
        x1 = x0 + self.winfo_width()
        y1 = y0 + self.winfo_height()
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            self.destroy()

    def _position_near(self, anchor: tk.Widget) -> None:
        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        x = min(x, sw - w - 8)
        y = min(y, sh - h - 8)
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.focus_set()

    # ---------------------------------------------------------------- render

    def _render(self) -> None:
        """Repaint cells in place — no widget creation."""
        self._title_var.set(
            f"{calendar.month_name[self._month]} {self._year}"
        )
        today = date.today()
        weeks = calendar.monthcalendar(self._year, self._month)
        # Pad to exactly _GRID_ROWS rows
        while len(weeks) < _GRID_ROWS:
            weeks.append([0] * _GRID_COLS)

        for r in range(_GRID_ROWS):
            for c in range(_GRID_COLS):
                idx = r * _GRID_COLS + c
                day = weeks[r][c]
                if day == 0:
                    self._cell_dates[idx] = None
                    self._paint_empty(idx)
                else:
                    d = date(self._year, self._month, day)
                    self._cell_dates[idx] = d
                    self._paint_day(idx, d, today)

    def _paint_empty(self, idx: int) -> None:
        self._cells[idx].config(
            text="", bg=Palette.SURFACE, fg=Palette.SURFACE, cursor=""
        )

    def _paint_day(self, idx: int, d: date, today: date) -> None:
        is_today = (d == today)
        is_selected = (d == self._selected)
        is_weekend = d.weekday() >= 5

        if is_selected:
            bg, fg = Palette.PRIMARY, Palette.PRIMARY_FG
        elif is_today:
            bg, fg = Palette.SELECT_BG, Palette.SELECT_FG
        else:
            bg = Palette.SURFACE
            fg = Palette.DANGER if is_weekend else Palette.TEXT

        self._cells[idx].config(text=str(d.day), bg=bg, fg=fg, cursor="hand2")

    # ---------------------------------------------------------------- events

    def _cell_clicked(self, idx: int) -> None:
        d = self._cell_dates[idx]
        if d is not None:
            self._pick(d)

    def _cell_hover(self, idx: int, entering: bool) -> None:
        d = self._cell_dates[idx]
        if d is None or d == self._selected:
            return  # skip empty cells and the selected one
        if entering:
            self._cells[idx].config(bg=Palette.ROW_ALT)
        else:
            # Repaint to restore the correct baseline color
            self._paint_day(idx, d, date.today())

    def _prev_month(self) -> None:
        self._month -= 1
        if self._month < 1:
            self._month = 12
            self._year -= 1
        self._render()

    def _next_month(self) -> None:
        self._month += 1
        if self._month > 12:
            self._month = 1
            self._year += 1
        self._render()

    def _pick(self, d: date) -> None:
        self.on_select(d)
        self.destroy()

    def _pick_today(self) -> None:
        self._pick(date.today())
