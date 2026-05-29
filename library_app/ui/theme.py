"""Centralized colour palette, fonts, and ttk style setup.

Keeping all visual constants in one module means a redesign touches one file
instead of every tab and dialog.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk


class Palette:
    """Application colour palette."""

    BG = "#f4f6fb"
    SURFACE = "#ffffff"
    HEADER_BG = "#1f2937"
    HEADER_FG = "#ffffff"
    BORDER = "#e5e7eb"
    TEXT = "#111827"
    MUTED = "#6b7280"

    PRIMARY = "#2563eb"
    PRIMARY_FG = "#ffffff"
    SUCCESS = "#16a34a"
    SUCCESS_FG = "#ffffff"
    WARNING = "#d97706"
    WARNING_FG = "#ffffff"
    DANGER = "#dc2626"
    DANGER_FG = "#ffffff"
    PURPLE = "#7c3aed"
    PURPLE_FG = "#ffffff"
    NEUTRAL = "#e5e7eb"
    NEUTRAL_FG = "#111827"

    # WhatsApp brand color — used for the Notify button so it reads as
    # "WhatsApp action" instantly without needing a real logo glyph.
    WHATSAPP = "#25d366"
    WHATSAPP_FG = "#ffffff"

    ROW_ALT = "#f9fafb"
    SELECT_BG = "#dbeafe"
    SELECT_FG = "#1e3a8a"

    STATUS_ACTIVE = "#2563eb"
    STATUS_OVERDUE = "#dc2626"
    STATUS_RETURNED = "#6b7280"
    STATUS_AVAIL = "#16a34a"
    STATUS_UNAVAIL = "#dc2626"


def base_font() -> tuple[str, int]:
    if sys.platform == "darwin":
        return ("Helvetica", 13)
    if sys.platform.startswith("win"):
        return ("Segoe UI", 10)
    return ("DejaVu Sans", 10)


def heading_font() -> tuple[str, int, str]:
    f = base_font()
    return (f[0], f[1], "bold")


def title_font() -> tuple[str, int, str]:
    f = base_font()
    return (f[0], f[1] + 6, "bold")


def setup_styles(root: tk.Tk) -> None:
    """Apply the application-wide ttk style configuration."""
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    f = base_font()
    root.configure(bg=Palette.BG)

    style.configure(".", font=f, background=Palette.BG, foreground=Palette.TEXT)
    style.configure("TFrame", background=Palette.BG)
    style.configure("Surface.TFrame", background=Palette.SURFACE)
    style.configure("Header.TFrame", background=Palette.HEADER_BG)

    style.configure("TLabel", background=Palette.BG, foreground=Palette.TEXT)
    style.configure("Surface.TLabel",
                    background=Palette.SURFACE, foreground=Palette.TEXT)
    style.configure("Header.TLabel",
                    background=Palette.HEADER_BG, foreground=Palette.HEADER_FG,
                    font=title_font())
    style.configure("Subtitle.TLabel",
                    background=Palette.HEADER_BG, foreground="#cbd5e1", font=f)
    style.configure("Muted.TLabel",
                    background=Palette.BG, foreground=Palette.MUTED)
    style.configure("SurfaceMuted.TLabel",
                    background=Palette.SURFACE, foreground=Palette.MUTED)
    style.configure("SectionTitle.TLabel",
                    background=Palette.SURFACE, foreground=Palette.TEXT,
                    font=heading_font())

    style.configure("TEntry",
                    fieldbackground=Palette.SURFACE,
                    bordercolor=Palette.BORDER,
                    lightcolor=Palette.BORDER,
                    darkcolor=Palette.BORDER, padding=6)
    style.map("TEntry", bordercolor=[("focus", Palette.PRIMARY)])

    # Checkbutton — the clam theme's default indicator is nearly invisible
    # against our light surface. Explicit indicator colors fix that on every
    # platform without needing to swap to `tk.Checkbutton`.
    style.configure("TCheckbutton",
                    background=Palette.BG, foreground=Palette.TEXT,
                    indicatorcolor=Palette.SURFACE,
                    indicatorbackground=Palette.SURFACE,
                    indicatorrelief="solid",
                    focuscolor=Palette.PRIMARY,
                    padding=(4, 2))
    style.map("TCheckbutton",
              background=[("active", Palette.BG)],
              indicatorcolor=[
                  ("selected", Palette.PRIMARY),
                  ("pressed", Palette.PRIMARY),
              ],
              indicatorbackground=[
                  ("selected", Palette.PRIMARY),
                  ("active", "#dbeafe"),
              ])

    # Notebook
    style.configure("TNotebook",
                    background=Palette.BG, borderwidth=0,
                    tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab",
                    padding=(20, 10), background="#e5e7eb",
                    foreground=Palette.TEXT, font=heading_font(),
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", Palette.PRIMARY)],
              foreground=[("selected", Palette.PRIMARY_FG)],
              expand=[("selected", (1, 1, 1, 0))])

    # Treeview
    style.configure("Treeview",
                    background=Palette.SURFACE,
                    fieldbackground=Palette.SURFACE,
                    foreground=Palette.TEXT,
                    rowheight=30, borderwidth=0, font=f)
    style.configure("Treeview.Heading",
                    background="#111827", foreground="#ffffff",
                    font=heading_font(), padding=(8, 8),
                    borderwidth=0, relief="flat")
    style.map("Treeview.Heading", background=[("active", "#1f2937")])
    style.map("Treeview",
              background=[("selected", Palette.SELECT_BG)],
              foreground=[("selected", Palette.SELECT_FG)])

    # Buttons
    def _btn(name: str, bg: str, fg: str, active: str) -> None:
        style.configure(name, background=bg, foreground=fg,
                        font=heading_font(), padding=(14, 8),
                        borderwidth=0, focusthickness=0, relief="flat")
        style.map(name,
                  background=[("active", active), ("disabled", "#cbd5e1")],
                  foreground=[("disabled", "#6b7280")])

    _btn("Primary.TButton", Palette.PRIMARY, Palette.PRIMARY_FG, "#1d4ed8")
    _btn("Success.TButton", Palette.SUCCESS, Palette.SUCCESS_FG, "#15803d")
    _btn("Warning.TButton", Palette.WARNING, Palette.WARNING_FG, "#b45309")
    _btn("Danger.TButton", Palette.DANGER, Palette.DANGER_FG, "#b91c1c")
    _btn("Purple.TButton", Palette.PURPLE, Palette.PURPLE_FG, "#6d28d9")
    _btn("Neutral.TButton", Palette.NEUTRAL, Palette.NEUTRAL_FG, "#d1d5db")
    _btn("Whatsapp.TButton", Palette.WHATSAPP, Palette.WHATSAPP_FG, "#1ebe5a")

    # Compact variant for inline icon-buttons (e.g., calendar picker).
    style.configure("Compact.TButton",
                    background=Palette.NEUTRAL, foreground=Palette.NEUTRAL_FG,
                    font=f, padding=(4, 0), borderwidth=0,
                    focusthickness=0, relief="flat")
    style.map("Compact.TButton",
              background=[("active", "#d1d5db"), ("disabled", "#cbd5e1")],
              foreground=[("disabled", "#6b7280")])

    style.configure("Status.TLabel",
                    background="#111827", foreground="#e5e7eb",
                    padding=(10, 6), font=f)
