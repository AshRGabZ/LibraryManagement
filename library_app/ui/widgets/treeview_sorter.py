"""Click-to-sort behaviour for `ttk.Treeview`.

Plug-and-play: build a treeview, hand it to `TreeviewSorter`, done. The sorter
- wires header click → sort by column (data columns AND the tree column "#0")
- shows ▲/▼ indicators in the active header
- is type-aware: numbers sort numerically, ISO dates chronologically,
  "X days [overdue]" by signed day count, "X/Y" by numerator, etc.
- handles **hierarchical** trees: sorts top-level rows AND sorts each parent's
  children by the same column. Stable sort means rows with equal values
  (e.g. blank parent rows being compared against loan-level columns) keep
  their relative order — clicking "Due" on the grouped Loans tab reorders
  each member's loans without reshuffling the members.
- re-applies sort after the caller refreshes rows (call `.resort()`)
- repairs alternating row stripes after sort (auto-detects whether the tree
  uses stripes, so hierarchical trees with custom row tags aren't disturbed)

Why a separate class instead of subclassing Treeview? Because tabs already use
the bare `ttk.Treeview` from `build_treeview()`. Wrapping that with a class
would force every call site to change. Composition keeps the seam small.
"""
from __future__ import annotations

import re
import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Iterable


# Per-column type override: callers can declare a column's value semantics
# instead of relying on heuristics.
SortType = str  # "auto" | "number" | "date" | "string" | "days_left"


_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_FRACTION_RE = re.compile(r"^(\d+)\s*/\s*\d+$")
_DAYS_RE = re.compile(r"^(\d+)\s+days?$", re.IGNORECASE)
_OVERDUE_RE = re.compile(r"^(\d+)\s+days?\s+overdue$", re.IGNORECASE)

# Stripe tags used by build_treeview — we re-apply these after sorting so the
# alternating-row look survives a re-order.
_STRIPE_TAGS = ("odd", "even")


def _auto_key(val: str) -> tuple:
    """Type-aware sort key.

    Returns a (bucket, value) tuple. Lower bucket sorts first so different
    "kinds" of cell content (numbers vs strings) don't accidentally interleave.
    """
    if not val or val == "—":
        return (9, "")  # nulls last

    # ISO date — e.g. "2026-05-28"
    try:
        return (1, date.fromisoformat(val).toordinal())
    except ValueError:
        pass

    # Plain number
    if _NUMERIC_RE.match(val):
        return (2, float(val))

    # Days-left style: "Due today" / "3 days" / "5 days overdue"
    low = val.lower()
    if low == "due today":
        return (3, 0)
    m = _OVERDUE_RE.match(val)
    if m:
        return (3, -int(m.group(1)))
    m = _DAYS_RE.match(val)
    if m:
        return (3, int(m.group(1)))

    # Fraction (e.g. renewal "1/3") — sort by numerator
    m = _FRACTION_RE.match(val)
    if m:
        return (4, int(m.group(1)))

    # Fallback: case-insensitive string
    return (5, val.lower())


class TreeviewSorter:
    """Adds click-to-sort to an existing `ttk.Treeview`.

    Usage:
        container, tree = build_treeview(parent, columns)
        self._sorter = TreeviewSorter(tree)

        # after refresh:
        self._sorter.resort()
    """

    def __init__(
        self,
        tree: ttk.Treeview,
        exclude: Iterable[str] = (),
    ) -> None:
        self._tree = tree
        self._col: str | None = None
        self._reverse = False

        # Data columns AND the tree column (#0). The latter only has a
        # heading when `show="tree headings"`; gracefully skip if absent.
        self._original_headings: dict[str, str] = {
            c: tree.heading(c)["text"] for c in tree["columns"]
        }
        try:
            tree_col_text = tree.heading("#0")["text"]
            if tree_col_text:
                self._original_headings["#0"] = tree_col_text
        except tk.TclError:
            pass

        excluded = set(exclude)
        for col in self._original_headings:
            if col in excluded:
                continue
            tree.heading(col, command=lambda c=col: self.sort_by(c))

    def sort_by(self, col: str) -> None:
        """Sort by `col`. Toggling the same column flips direction."""
        if self._col == col:
            self._reverse = not self._reverse
        else:
            self._col = col
            self._reverse = False
        self._apply()

    def resort(self) -> None:
        """Re-apply the current sort. Call after refreshing rows."""
        if self._col is not None:
            self._apply()

    def clear(self) -> None:
        """Drop the active sort and restore original headings."""
        self._col = None
        self._reverse = False
        for col, orig in self._original_headings.items():
            self._tree.heading(col, text=orig)

    # ----------------------------------------------------------- internals #

    def _value(self, item: str, col: str) -> str:
        """Read a cell value, including the tree column #0 (which is text-only,
        not a data column, so `Treeview.set` doesn't apply)."""
        if col == "#0":
            return self._tree.item(item, "text") or ""
        return self._tree.set(item, col)

    def _has_stripes(self) -> bool:
        """Did the caller already apply odd/even stripes? If not (e.g. the
        hierarchical Loans view uses custom member/status tags only), don't
        force stripes — that would clobber their visual semantics."""
        for c in self._tree.get_children(""):
            tags = self._tree.item(c, "tags")
            if any(t in _STRIPE_TAGS for t in tags):
                return True
        return False

    def _sort_siblings(self, parent: str, col: str) -> None:
        """Reorder direct children of `parent` by `col`. Stable — equal-keyed
        rows keep their input order."""
        items = [(self._value(c, col), c)
                 for c in self._tree.get_children(parent)]
        if not items:
            return
        items.sort(key=lambda p: _auto_key(p[0]), reverse=self._reverse)
        for idx, (_, child) in enumerate(items):
            self._tree.move(child, parent, idx)

    def _apply(self) -> None:
        col = self._col
        if col is None:
            return

        stripes = self._has_stripes()

        # 1) Sort the top-level (member rows in the grouped view; the only
        #    level in a flat view).
        top_items = [(self._value(c, col), c)
                     for c in self._tree.get_children("")]
        top_items.sort(key=lambda p: _auto_key(p[0]), reverse=self._reverse)
        for idx, (_, child) in enumerate(top_items):
            self._tree.move(child, "", idx)
            if stripes:
                # Re-stripe: keep status tags, replace odd/even by new index
                tags = [t for t in self._tree.item(child, "tags")
                        if t not in _STRIPE_TAGS]
                tags.append("even" if idx % 2 else "odd")
                self._tree.item(child, tags=tags)

        # 2) Sort children inside each top-level row (no-op for flat trees;
        #    for grouped Loans this puts each member's loans into the chosen
        #    order).
        for parent in self._tree.get_children(""):
            self._sort_siblings(parent, col)

        # 3) Update header indicators
        arrow_up, arrow_down = "  ▲", "  ▼"
        for c, orig in self._original_headings.items():
            if c == col:
                arrow = arrow_down if self._reverse else arrow_up
                self._tree.heading(c, text=orig + arrow)
            else:
                self._tree.heading(c, text=orig)
