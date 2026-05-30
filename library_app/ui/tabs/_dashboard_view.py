"""Admin → Dashboard view.

A composed widget owned by AdminTab. Kept in its own module so the dashboard's
layout and the Admin tab's transactional UI evolve independently.

Charts are drawn directly on a tk.Canvas — no matplotlib/numpy dependency.
KPI cards use a two-tone design: a colored top bar + number on white surface.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...services import Services
from ...services.stats_service import MonthlyLoans, OverallStats, RankedItem
from ..theme import Palette, base_font, heading_font, small_font, title_font
from ..widgets import ScrollableFrame, build_treeview


_CHART_HEIGHT = 230
_BAR_GAP = 8
_BAR_MIN_WIDTH = 24
_BAR_MAX_WIDTH = 64


# KPI card definitions: (label, attr_or_callable, accent_color, icon)
def _kpi_cards(s: OverallStats) -> list[tuple[str, str, str, str]]:
    return [
        ("Total Books",       str(s.total_books),       Palette.PRIMARY,  "📚"),
        ("Copies Available",  f"{s.available_copies}/{s.total_copies}",
                                                          Palette.SUCCESS,  "📦"),
        ("Members",           str(s.total_members),     Palette.PURPLE,   "👥"),
        ("Active Loans",      str(s.active_loans),       "#0ea5e9",        "●"),
        ("Overdue",           str(s.overdue_loans),
         Palette.DANGER if s.overdue_loans else Palette.MUTED,              "⚠"),
        ("Total Loans",       str(s.total_loans),        Palette.MUTED,   "Σ"),
    ]


class DashboardView(ttk.Frame):
    """All metrics surfaces for the library, recomputed on `.refresh()`."""

    def __init__(self, parent: tk.Widget, services: Services) -> None:
        super().__init__(parent)
        self._services = services
        self._build_ui()

    # ─────────────────────────────────────────── ui construction ──

    def _build_ui(self) -> None:
        # The dashboard stacks heterogeneous blocks (KPI cards, a chart, three
        # ranked lists) whose combined height exceeds a short window. Hosting
        # it in a scrollable page means nothing is ever clipped — a scrollbar
        # appears only when the content doesn't fit, exactly like a normal app.
        scroller = ScrollableFrame(self, bg=Palette.BG)
        scroller.pack(fill="both", expand=True)
        outer = tk.Frame(scroller.body, bg=Palette.BG, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        # ── KPI snapshot row ─────────────────────────────────────────────────
        snap_lf = tk.LabelFrame(outer, text="  📊  Library Snapshot",
                                bg=Palette.BG, fg=Palette.PRIMARY,
                                font=heading_font(), padx=10, pady=10,
                                relief="flat",
                                highlightthickness=1,
                                highlightbackground=Palette.BORDER)
        snap_lf.pack(fill="x", pady=(0, 12))
        self._snap_inner = tk.Frame(snap_lf, bg=Palette.BG)
        self._snap_inner.pack(fill="x")
        self._stat_cards: dict[str, tk.Label] = {}

        # ── Loans-per-month chart ─────────────────────────────────────────────
        chart_lf = tk.LabelFrame(outer, text="  📈  Loans per Month  (last 12)",
                                 bg=Palette.BG, fg=Palette.PRIMARY,
                                 font=heading_font(), padx=10, pady=10,
                                 relief="flat",
                                 highlightthickness=1,
                                 highlightbackground=Palette.BORDER)
        chart_lf.pack(fill="x", pady=(0, 12))
        self._chart = tk.Canvas(
            chart_lf, height=_CHART_HEIGHT,
            bg=Palette.SURFACE, highlightthickness=1,
            highlightbackground=Palette.BORDER,
        )
        self._chart.pack(fill="x")
        self._chart.bind("<Configure>", lambda e: self._draw_chart())

        # ── Top-N panels ──────────────────────────────────────────────────────
        ranks = tk.Frame(outer, bg=Palette.BG)
        ranks.pack(fill="both", expand=True)
        ranks.columnconfigure(0, weight=1)
        ranks.columnconfigure(1, weight=1)
        ranks.columnconfigure(2, weight=1)
        ranks.rowconfigure(0, weight=1)

        self._books_tree = self._build_ranked_panel(
            ranks, "📚  Top Books", row=0, col=0,
            columns=[
                ("name",     "Title",  220, "w"),
                ("subtitle", "Author", 140, "w"),
                ("count",    "Loans",   70, "center"),
            ],
            padx=(0, 6),
        )
        self._cats_tree = self._build_ranked_panel(
            ranks, "🏷️  Top Categories", row=0, col=1,
            columns=[
                ("name",  "Category", 180, "w"),
                ("count", "Loans",     70, "center"),
            ],
            padx=6,
        )
        self._langs_tree = self._build_ranked_panel(
            ranks, "🌐  Top Languages", row=0, col=2,
            columns=[
                ("name",  "Language", 160, "w"),
                ("count", "Loans",     70, "center"),
            ],
            padx=(6, 0),
        )

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
        lf = tk.LabelFrame(parent, text=f"  {title}", bg=Palette.BG,
                           fg=Palette.PRIMARY, font=heading_font(),
                           padx=8, pady=8, relief="flat",
                           highlightthickness=1,
                           highlightbackground=Palette.BORDER)
        lf.grid(row=row, column=col, sticky="nsew", padx=padx, pady=(0, 4))
        # height=10 fits the full top-10 without the panel needing its own
        # scrollbar — so only the dashboard *page* scrolls, never a nested list.
        container, tree = build_treeview(lf, columns, height=10)
        container.pack(fill="both", expand=True)
        return tree

    # ─────────────────────────────────────────── KPI cards ──

    def _build_stat_cards(self, stats: OverallStats) -> None:
        for w in self._snap_inner.winfo_children():
            w.destroy()
        self._stat_cards.clear()

        cards = _kpi_cards(stats)
        for i, (label, value, color, icon) in enumerate(cards):
            self._snap_inner.columnconfigure(i, weight=1)

            # Card outer (border simulation)
            outer = tk.Frame(
                self._snap_inner, bg=Palette.BORDER,
            )
            outer.grid(row=0, column=i, sticky="nsew", padx=4, pady=2)

            # Colored top accent band
            top_bar = tk.Frame(outer, bg=color, height=5)
            top_bar.pack(fill="x")
            top_bar.pack_propagate(False)

            # White card body
            card = tk.Frame(outer, bg=Palette.SURFACE, padx=12, pady=10)
            card.pack(fill="both", expand=True, padx=1, pady=(0, 1))

            # Icon + label row
            row_lbl = tk.Frame(card, bg=Palette.SURFACE)
            row_lbl.pack(fill="x")
            tk.Label(row_lbl, text=icon, bg=Palette.SURFACE,
                     fg=color, font=base_font()).pack(side="left")
            tk.Label(row_lbl, text=f"  {label}", bg=Palette.SURFACE,
                     fg=Palette.MUTED, font=small_font()).pack(side="left")

            # Large value
            big = tk.Label(card, text=value, bg=Palette.SURFACE, fg=color,
                           font=title_font())
            big.pack(anchor="w", pady=(4, 0))
            self._stat_cards[label] = big

    # ─────────────────────────────────────────── chart ──

    def _draw_chart(self) -> None:
        """Render the loans-per-month bar chart. Redraws on canvas resize."""
        c = self._chart
        c.delete("all")
        width = c.winfo_width()
        height = _CHART_HEIGHT
        if width < 50 or not self._monthly:
            c.create_text(width // 2, height // 2,
                          text="No loan history yet — borrow a book to see trends.",
                          fill=Palette.MUTED, font=base_font())
            return

        left_pad, right_pad = 46, 20
        top_pad, bottom_pad = 24, 44
        plot_w = width - left_pad - right_pad
        plot_h = height - top_pad - bottom_pad
        n = len(self._monthly)
        max_count = max((m.count for m in self._monthly), default=1) or 1

        bar_w = max(_BAR_MIN_WIDTH,
                    min(_BAR_MAX_WIDTH,
                        (plot_w - (n - 1) * _BAR_GAP) // n if n else _BAR_MIN_WIDTH))
        total_w = n * bar_w + (n - 1) * _BAR_GAP
        x_start = left_pad + max(0, (plot_w - total_w) // 2)

        baseline = top_pad + plot_h

        # Y-axis gridlines with labels
        for i in range(5):
            y = top_pad + plot_h - (plot_h * i // 4)
            val = max_count * i // 4
            c.create_line(left_pad - 4, y, width - right_pad, y,
                          fill=Palette.BORDER, dash=(3, 3))
            c.create_text(left_pad - 8, y, text=str(val),
                          anchor="e", fill=Palette.MUTED, font=small_font())

        # Bars with gradient-style two-tone rendering (lighter top strip)
        for i, m in enumerate(self._monthly):
            x = x_start + i * (bar_w + _BAR_GAP)
            h = max(4, int(plot_h * (m.count / max_count)))
            y = baseline - h

            # Shadow (1px offset dark bar)
            c.create_rectangle(x + 1, y + 1, x + bar_w + 1, baseline + 1,
                                fill=Palette.SHADOW, outline="")
            # Main bar body
            c.create_rectangle(x, y, x + bar_w, baseline,
                                fill=Palette.PRIMARY, outline="")
            # Lighter top strip (simulates gradient)
            c.create_rectangle(x, y, x + bar_w, min(y + 8, baseline),
                                fill=Palette.ACCENT_BAR, outline="")

            # Count label above bar
            c.create_text(x + bar_w / 2, y - 5, text=str(m.count),
                          anchor="s", fill=Palette.TEXT,
                          font=(small_font()[0], small_font()[1], "bold"))
            # Month label below (compact)
            label = m.month[2:]
            c.create_text(x + bar_w / 2, baseline + 7, text=label,
                          anchor="n", fill=Palette.MUTED, font=small_font())

        # Baseline line
        c.create_line(left_pad - 4, baseline, width - right_pad, baseline,
                      fill=Palette.BORDER)

    # ─────────────────────────────────────────── ranked lists ──

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

    # ─────────────────────────────────────────── refresh ──

    def refresh(self) -> None:
        """Recompute and redraw every section."""
        stats = self._services.stats.overall()
        self._build_stat_cards(stats)

        self._monthly = self._services.stats.loans_per_month(months_back=12)
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
