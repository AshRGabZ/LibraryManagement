from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ...exceptions import LibraryError
from ...services import Services
from ..theme import Palette, base_font, heading_font


class RenewDialog(tk.Toplevel):
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

        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="🔁  Renew Loan",
                  style="Header.TLabel").pack(anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=24, pady=18)
        body.pack(fill="both", expand=True)

        def info_row(r: int, label: str, value: str,
                     value_color: str = Palette.TEXT) -> None:
            tk.Label(body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                     font=base_font()).grid(row=r, column=0, sticky="w",
                                            pady=4, padx=(0, 14))
            tk.Label(body, text=value, bg=Palette.SURFACE, fg=value_color,
                     font=heading_font()).grid(row=r, column=1, sticky="w",
                                               pady=4)

        info_row(0, "Book:", loan.book_title)
        info_row(1, "Member:", loan.member_name)
        info_row(2, "Current due date:", loan.due_on or "—", Palette.PRIMARY)
        renew_color = Palette.SUCCESS if renew_count < max_r else Palette.DANGER
        info_row(3, "Renewals used:", f"{renew_count} / {max_r}", renew_color)

        tk.Frame(body, bg=Palette.BORDER, height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=12)

        tk.Label(body, text="Extend by:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=5, column=0, sticky="w", pady=4)

        period = tk.Frame(body, bg=Palette.SURFACE)
        period.grid(row=5, column=1, sticky="w", pady=4)
        self.days_var = tk.StringVar(
            value=str(self._services.loans.DEFAULT_LOAN_DAYS)
        )
        ttk.Entry(period, textvariable=self.days_var, width=6,
                  font=base_font()).pack(side="left")
        tk.Label(period, text="days", bg=Palette.SURFACE, fg=Palette.MUTED,
                 font=base_font()).pack(side="left", padx=(6, 0))

        if renew_count >= max_r:
            tk.Label(body, text="⚠  Maximum renewals reached.",
                     bg=Palette.SURFACE, fg=Palette.DANGER, font=heading_font()
                     ).grid(row=6, column=0, columnspan=2, sticky="w",
                            pady=(10, 0))

        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=14)
        btns.pack(fill="x")
        renew_btn = ttk.Button(btns, text="🔁 Renew", style="Purple.TButton",
                               command=self._submit)
        renew_btn.pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")
        if renew_count >= max_r:
            renew_btn.state(["disabled"])

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Escape>", lambda e: self.destroy())

    def _submit(self) -> None:
        try:
            days = int(self.days_var.get() or self._services.loans.DEFAULT_LOAN_DAYS)
            self._services.loans.renew(self.loan_id, extra_days=days)
            self.destroy()
            self.on_success()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e), parent=self)
