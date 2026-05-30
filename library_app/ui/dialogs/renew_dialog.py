from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider


class RenewDialog(tk.Toplevel):
    """Renew a loan — card-based info display with a visual renewal progress bar."""

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        loan_id: int,
        on_success: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._services = services
        self.loan_id = loan_id
        self.on_success = on_success
        self.title("Renew Loan")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        loan = self._services.loans.get(loan_id)
        if loan is None:
            messagebox.showerror("Error", "Loan not found.", parent=parent)
            self.destroy()
            return
        if loan.is_returned:
            messagebox.showerror("Error", "This loan has already been returned.",
                                 parent=parent)
            self.destroy()
            return

        max_r = self._services.loans.MAX_RENEWALS
        renew_count = loan.renew_count
        at_limit = renew_count >= max_r

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text="🔁  Renew Loan",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Extend the due date for this loan",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Buttons (packed before body so always visible) ───────────────────
        make_divider(self).pack(fill="x", side="bottom")
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")
        self._renew_btn = ttk.Button(btns, text="🔁  Renew",
                                     style="Purple.TButton",
                                     command=self._submit)
        self._renew_btn.pack(side="right")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))
        if at_limit:
            self._renew_btn.state(["disabled"])

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=Palette.SURFACE, padx=28, pady=22)
        body.pack(fill="both", expand=True)

        # ── Info card ────────────────────────────────────────────────────────
        card_outer = tk.Frame(body, bg=Palette.BORDER)
        card_outer.pack(fill="x", pady=(0, 18))
        card = tk.Frame(card_outer, bg=Palette.CARD_BG, padx=18, pady=14)
        card.pack(fill="x", padx=1, pady=1)

        def _info_row(r: int, icon: str, label: str, value: str,
                      value_color: str = Palette.TEXT) -> None:
            tk.Label(card, text=f"{icon}  {label}", bg=Palette.CARD_BG,
                     fg=Palette.MUTED, font=small_font(),
                     ).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 20))
            tk.Label(card, text=value, bg=Palette.CARD_BG,
                     fg=value_color, font=heading_font(),
                     ).grid(row=r, column=1, sticky="w", pady=4)

        _info_row(0, "📚", "Book", loan.book_title)
        _info_row(1, "👤", "Member", loan.member_name)
        _info_row(2, "📅", "Current due date",
                  loan.due_on or "—", Palette.PRIMARY)

        # ── Renewal progress bar ─────────────────────────────────────────────
        tk.Frame(card, bg=Palette.BORDER, height=1).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(10, 8))

        prog_label_frame = tk.Frame(card, bg=Palette.CARD_BG)
        prog_label_frame.grid(row=4, column=0, columnspan=2, sticky="ew")

        renew_color = (Palette.DANGER if at_limit
                       else Palette.WARNING if renew_count == max_r - 1
                       else Palette.SUCCESS)

        tk.Label(prog_label_frame,
                 text=f"🔄  Renewals used:",
                 bg=Palette.CARD_BG, fg=Palette.MUTED,
                 font=small_font()).pack(side="left")
        tk.Label(prog_label_frame,
                 text=f"  {renew_count} / {max_r}",
                 bg=Palette.CARD_BG, fg=renew_color,
                 font=heading_font()).pack(side="left")

        # Visual progress bar
        prog_frame = tk.Frame(card, bg=Palette.CARD_BG)
        prog_frame.grid(row=5, column=0, columnspan=2, sticky="ew",
                        pady=(6, 0))
        prog_bar_bg = tk.Frame(prog_frame, bg=Palette.BORDER, height=10)
        prog_bar_bg.pack(fill="x")
        fill_pct = min(renew_count / max(max_r, 1), 1.0)
        if fill_pct > 0:
            prog_fill = tk.Frame(prog_bar_bg, bg=renew_color, height=10)
            prog_fill.place(relx=0, rely=0, relwidth=fill_pct, relheight=1)

        # ── At-limit warning ─────────────────────────────────────────────────
        if at_limit:
            warn_card = tk.Frame(body, bg=Palette.DANGER_SOFT)
            warn_card.pack(fill="x", pady=(0, 14))
            tk.Label(warn_card,
                     text="⛔  Maximum renewals reached — this loan cannot be renewed further.",
                     bg=Palette.DANGER_SOFT, fg=Palette.DANGER,
                     font=heading_font(), padx=14, pady=10, wraplength=440,
                     justify="left",
                     ).pack(anchor="w")
        else:
            # ── Extend-by row ─────────────────────────────────────────────────
            tk.Label(body, text="📆  Extend loan by", bg=Palette.SURFACE,
                     fg=Palette.MUTED, font=small_font(),
                     ).pack(anchor="w", pady=(0, 4))
            period_frame = tk.Frame(body, bg=Palette.SURFACE)
            period_frame.pack(fill="x")

            wrap = tk.Frame(period_frame, bg=Palette.BORDER)
            wrap.pack(side="left")
            self.days_var = tk.StringVar(
                value=str(self._services.loans.DEFAULT_RENEW_DAYS)
            )
            days_entry = tk.Entry(
                wrap, textvariable=self.days_var, width=6,
                font=base_font(), relief="flat", bd=0,
                bg=Palette.SURFACE, fg=Palette.TEXT,
                insertbackground=Palette.PRIMARY,
            )
            days_entry.pack(padx=1, pady=1, ipady=8, ipadx=10)
            days_entry.bind("<FocusIn>",
                            lambda e: wrap.configure(bg=Palette.BORDER_FOCUS))
            days_entry.bind("<FocusOut>",
                            lambda e: wrap.configure(bg=Palette.BORDER))

            tk.Label(period_frame, text="  days", bg=Palette.SURFACE,
                     fg=Palette.MUTED, font=base_font()).pack(side="left")

            days_entry.focus_set()

        self.bind("<Return>", lambda e: (
            None if at_limit else self._submit()
        ))
        self.bind("<Escape>", lambda e: self.destroy())

        center_window(self, parent, width=500, height=520 if not at_limit else 460)

    def _submit(self) -> None:
        try:
            days = int(self.days_var.get() or self._services.loans.DEFAULT_RENEW_DAYS)
            self._services.loans.renew(self.loan_id, extra_days=days)
            self.destroy()
            self.on_success()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e), parent=self)
