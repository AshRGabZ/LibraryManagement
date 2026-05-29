from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Sequence

from ..theme import Palette


ColumnSpec = tuple[str, str, int, str]  # (key, heading, width, anchor)


def build_treeview(
    parent: tk.Widget,
    columns_spec: Sequence[ColumnSpec],
    height: int | None = None,
) -> tuple[ttk.Frame, ttk.Treeview]:
    """Construct a styled Treeview with a scrollbar.

    Returns (container_frame, treeview). Pack/grid the container; never the
    treeview directly.

    `height` is the number of visible rows. Set this when the tree shares
    vertical space with other widgets (e.g., a search bar + input row in a
    LabelFrame) — otherwise the default ~10 rows can push siblings off-screen.
    """
    container = ttk.Frame(parent, style="Surface.TFrame")
    keys = [c[0] for c in columns_spec]

    tree_kwargs = {"columns": keys, "show": "headings", "selectmode": "browse"}
    if height is not None:
        tree_kwargs["height"] = height
    tree = ttk.Treeview(container, **tree_kwargs)
    for key, heading, width, anchor in columns_spec:
        tree.heading(key, text=heading, anchor=anchor)
        tree.column(key, width=width, anchor=anchor, stretch=True)

    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.tag_configure("odd", background=Palette.SURFACE)
    tree.tag_configure("even", background=Palette.ROW_ALT)
    tree.tag_configure("status_active", foreground=Palette.STATUS_ACTIVE)
    tree.tag_configure("status_overdue", foreground=Palette.STATUS_OVERDUE)
    tree.tag_configure("status_returned", foreground=Palette.STATUS_RETURNED)
    tree.tag_configure("status_avail", foreground=Palette.STATUS_AVAIL)
    tree.tag_configure("status_unavail", foreground=Palette.STATUS_UNAVAIL)
    return container, tree
