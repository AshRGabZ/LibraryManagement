"""Admin → Dashboard view.

A composed widget owned by AdminTab. Kept in its own module so the dashboard's
layout and the Admin tab's transactional UI evolve independently.

Charts are drawn directly on a tk.Canvas — no matplotlib/numpy dependency, no
extra MB in the packaged binary. For the data volumes a small library handles,
this is plenty.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...services import Services
from ...services.stats_service import MonthlyLoans, OverallStats, RankedItem
from ..theme import Palette, base_font, heading_font, title_font
from ..widgets import build_treeview


_CHART_HEIGHT = 220
_BAR_GAP = 8
_BAR_MIN_WIDTH = 24
_BAR_MAX_WIDTH = 60


class DashboardView(ttk.Frame):
    """All metrics surfaces for the library, recomputed on `.refresh()`."""

    def __init__(self, parent: tk.Widget, services: Services) -> None:
        super().__init__(parent)
        self._services = services
        self._build_ui()

    # ------------------------------------------------------------------ ui

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=Palette.BG, padx=10, pady=10)
        outer.pack(fill="both", expand=True)

        # Snapshot row: four KPI cards
        snap = tk.LabelFrame(outer, text="Library Snapshot", bg=Palette.BG,
                             fg=Palette.TEXT, font=heading_font(),
                             padx=10, pady=10)
        snap.pack(fill="x", pady=(0, 10))
        self._snap_inner = tk.Frame(snap, bg=Palette.BG)
        self._snap_inner.pack(fill="x")
        self._stat_cards: dict[str, tk.Label] = {}

        # Loans-per-month chart
        chart_frame = tk.LabelFrame(outer, text="Loans per Month (last 12)",
                                    bg=Palette.BG, fg=Palette.TEXT,
                                    font=heading_font(), padx=10, pady=10)
        chart_frame.pack(fill="x", pady=(0, 10))
        self._chart = tk.Canvas(
            chart_frame, height=_CHART_HEIGHT,
            bg=Palette.SURFACE, highlightthickness=1,
            highlightbackground=Palette.BORDER,
        )
        self._chart.pack(fill="x")
        self._chart.bind("<Configure>", lambda e: self._draw_chart())

        # Top-N panels
        ranks = tk.Frame(outer, bg=Palette.BG)
        ranks.pack(fill="both", expand=True)
        ranks.columnconfigure(0, weight=1)
        ranks.columnconfigure(1, weight=1)
        ranks.columnconfigure(2, weight=1)
        ranks.rowconfigure(0, weight=1)

        self._books_tree = self._build_ranked_panel(
            ranks, "📚 Top Books", row=0, col=0,
            columns=[
                ("name", "Title", 220, "w"),
                ("subtitle", "Author", 140, "w"),
                ("count", "Loans", 70, "center"),
            ],
            padx=(0, 5),
        )
        self._cats_tree = self._build_ranked_panel(
            ranks, "🏷️ Top Categories", row=0, col=1,
            columns=[
                ("name", "Category", 180, "w"),
                ("count", "Loans", 70, "center"),
            ],
            padx=5,
        )
        self._langs_tree = self._build_ranked_panel(
            ranks, "🌐 Top Languages", row=0, col=2,
            columns=[
                ("name", "Language", 160, "w"),
                ("count", "Loans", 70, "center"),
            ],
            padx=(5, 0),
        )

        # State cache for redraw on resize
        self._monthly: list[MonthlyLoans] = []

    def _build_ranked_panel(
        self,
        parent: tk.Widget,
        title: str,
        *,
        row: int,
        col: int,
        columns: list,
        padx: tuple,
    ) -> ttk.Treeview:
        lf = tk.LabelFrame(parent, text=title, bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=8)
        lf.grid(row=row, column=col, sticky="nsew", padx=padx)
        container, tree = build_treeview(lf, columns, height=8)
        container.pack(fill="both", expand=True)
        return tree

    # --------------------------------------------------------- KPI cards #

    def _build_stat_cards(self, stats: OverallStats) -> None:
        # Clear and rebuild — cheap, four widgets max.
        for w in self._snap_inner.winfo_children():
            w.destroy()
        self._stat_cards.clear()

        cards = [
            ("📚 Total Books", str(stats.total_books), Palette.PRIMARY),
            ("📦 Copies Available", f"{stats.available_copies}/{stats.total_copies}",
             Palette.SUCCESS),
            ("👥 Members", str(stats.total_members), Palette.PURPLE),
            ("● Active Loans", str(stats.active_loans), "#0ea5e9"),
            ("⚠ Overdue", str(stats.overdue_loans),
             Palette.DANGER if stats.overdue_loans else Palette.MUTED),
            ("Σ Total Loans", str(stats.total_loans), Palette.MUTED),
        ]
        for i, (label, value, color) in enumerate(cards):
            self._snap_inner.columnconfigure(i, weight=1)
            card = tk.Frame(self._snap_inner, bg=Palette.SURFACE,
                            highlightthickness=1,
                            highlightbackground=Palette.BORDER)
            card.grid(row=0, column=i, sticky="nsew", padx=4)
            # tk.Label's own padx/pady accept single ints only — use pack's
            # tuple-form padding for the asymmetric top/bottom gap.
            tk.Label(card, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                     font=base_font(), padx=10
                     ).pack(anchor="w", pady=(8, 0))
            big = tk.Label(card, text=value, bg=Palette.SURFACE, fg=color,
                           font=title_font(), padx=10)
            big.pack(anchor="w", pady=(0, 8))
            self._stat_cards[label] = big

    # ------------------------------------------------------------- chart #

    def _draw_chart(self) -> None:
        """Render the loans-per-month bar chart on the Canvas.

        Called on initial render AND on canvas <Configure> (resize) — bars
        scale to fit horizontally without us needing to know the actual width
        until Tk reports it.
        """
        c = self._chart
        c.delete("all")
        width = c.winfo_width()
        height = _CHART_HEIGHT
        if width < 50 or not self._monthly:
            c.create_text(width // 2, height // 2,
                          text="No loan history yet — borrow a book to start "
                               "seeing trends.",
                          fill=Palette.MUTED, font=base_font())
            return

        # Layout
        left_pad, right_pad = 40, 20
        top_pad, bottom_pad = 20, 40
        plot_w = width - left_pad - right_pad
        plot_h = height - top_pad - bottom_pad
        n = len(self._monthly)
        max_count = max((m.count for m in self._monthly), default=1) or 1

        # Pick a bar width that fits comfortably
        bar_w = max(_BAR_MIN_WIDTH,
                    min(_BAR_MAX_WIDTH,
                        (plot_w - (n - 1) * _BAR_GAP) // n if n else _BAR_MIN_WIDTH))
        total_w = n * bar_w + (n - 1) * _BAR_GAP
        x_start = left_pad + max(0, (plot_w - total_w) // 2)

        # Baseline + Y-axis gridlines (4 ticks)
        baseline = top_pad + plot_h
        for i in range(5):
            y = top_pad + plot_h - (plot_h * i // 4)
            val = max_count * i // 4
            c.create_line(left_pad - 4, y, width - right_pad, y,
                          fill=Palette.BORDER, dash=(2, 2))
            c.create_text(left_pad - 8, y, text=str(val),
                          anchor="e", fill=Palette.MUTED, font=base_font())

        # Bars
        for i, m in enumerate(self._monthly):
            x = x_start + i * (bar_w + _BAR_GAP)
            h = int(plot_h * (m.count / max_count))
            y = baseline - h
            c.create_rectangle(x, y, x + bar_w, baseline,
                               fill=Palette.PRIMARY, outline="")
            # Value above the bar
            c.create_text(x + bar_w / 2, y - 4, text=str(m.count),
                          anchor="s", fill=Palette.TEXT, font=base_font())
            # Month label below (compact: "YY-MM")
            label = m.month[2:]  # "26-05"
            c.create_text(x + bar_w / 2, baseline + 6, text=label,
                          anchor="n", fill=Palette.MUTED, font=base_font())

    # -------------------------------------------------------- ranked lists

    def _fill_ranked(self, tree: ttk.Treeview, items: list[RankedItem],
                     include_subtitle: bool) -> None:
        for r in tree.get_children():
            tree.delete(r)
        if not items:
            return
        for i, item in enumerate(items):
            tag = "even" if i % 2 else "odd"
            if include_subtitle:
                tree.insert("", "end",
                            values=(item.name, item.subtitle, item.count),
                            tags=(tag,))
            else:
                tree.insert("", "end",
                            values=(item.name, item.count),
                            tags=(tag,))

    # ---------------------------------------------------------- refresh  #

    def refresh(self) -> None:
        """Recompute and redraw every section."""
        stats = self._services.stats.overall()
        self._build_stat_cards(stats)

        self._monthly = self._services.stats.loans_per_month(months_back=12)
        # Defer to next idle so the canvas has its actual width
        self.after_idle(self._draw_chart)

        self._fill_ranked(self._books_tree,
                          self._services.stats.most_borrowed_books(10),
                          include_subtitle=True)
        self._fill_ranked(self._cats_tree,
                          self._services.stats.most_borrowed_categories(10),
                          include_subtitle=False)
        self._fill_ranked(self._langs_tree,
                          self._services.stats.most_borrowed_languages(10),
                          include_subtitle=False)
