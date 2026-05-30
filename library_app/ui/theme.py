"""Centralized colour palette, fonts, and ttk style setup.

Keeping all visual constants in one module means a redesign touches one file
instead of every tab and dialog. The rest of the app references only the
`Palette.*` attribute names and the named ttk styles defined here — so the
visual identity can be re-skinned wholesale without editing any call site.

Design language — "Indigo Library":
  • Deep indigo header band with a brighter accent strip beneath it.
  • Indigo-600 primary, with emerald / amber / rose / violet accents tuned to
    sit harmoniously beside it.
  • A soft, cool canvas so white surface cards lift off the background.
  • Generous row height and padding for an unhurried, premium feel.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk


class Palette:
    """Application colour palette.

    Attribute names are a stable contract consumed across the UI; only the
    *values* should change when re-skinning.
    """

    # ---- Canvas & surfaces ------------------------------------------------
    BG = "#eef1f8"          # soft cool canvas so white cards lift off it
    SURFACE = "#ffffff"     # cards, dialogs, table backgrounds
    SURFACE_ALT = "#f8fafc"  # subtly tinted surface (section bands)
    CARD_BG = "#f4f6fb"     # slightly tinted card background for KPIs

    # ---- Brand header -----------------------------------------------------
    HEADER_BG = "#1e1b4b"    # indigo-950 — rich, premium
    HEADER_FG = "#ffffff"
    HEADER_ACCENT = "#a5b4fc"  # indigo-300 — subtitle text on the header
    ACCENT_BAR = "#6366f1"     # indigo-500 — thin strip beneath the header
    HEADER_BADGE_BG = "#312e81"  # slightly lighter than header for badges

    # ---- Ink --------------------------------------------------------------
    TEXT = "#0f172a"         # slate-900 — deeper than gray, easier to read
    MUTED = "#64748b"        # slate-500 — captions, secondary text
    BORDER = "#e2e8f0"       # slate-200 — hairline separators
    BORDER_FOCUS = "#818cf8"  # indigo-400 — focused input border

    # ---- Primary & semantic accents --------------------------------------
    PRIMARY = "#4f46e5"      # indigo-600
    PRIMARY_FG = "#ffffff"
    PRIMARY_HOVER = "#4338ca"  # indigo-700
    PRIMARY_SOFT = "#e0e7ff"   # indigo-100 — soft fills / selection
    PRIMARY_GLOW = "#c7d2fe"   # indigo-200 — glow ring

    SUCCESS = "#059669"      # emerald-600
    SUCCESS_FG = "#ffffff"
    SUCCESS_HOVER = "#047857"
    SUCCESS_SOFT = "#d1fae5"  # emerald-100

    WARNING = "#d97706"      # amber-600
    WARNING_FG = "#ffffff"
    WARNING_HOVER = "#b45309"
    WARNING_SOFT = "#fef3c7"  # amber-100

    DANGER = "#e11d48"       # rose-600 — refined, less harsh than pure red
    DANGER_FG = "#ffffff"
    DANGER_HOVER = "#be123c"
    DANGER_SOFT = "#ffe4e6"   # rose-100

    PURPLE = "#7c3aed"       # violet-600
    PURPLE_FG = "#ffffff"
    PURPLE_HOVER = "#6d28d9"
    PURPLE_SOFT = "#ede9fe"   # violet-100

    NEUTRAL = "#e2e8f0"      # slate-200 — quiet buttons
    NEUTRAL_FG = "#334155"   # slate-700
    NEUTRAL_HOVER = "#cbd5e1"  # slate-300

    # WhatsApp brand color — used for the Notify button so it reads as
    # "WhatsApp action" instantly without needing a real logo glyph.
    WHATSAPP = "#25d366"
    WHATSAPP_FG = "#ffffff"
    WHATSAPP_HOVER = "#1ebe5a"

    # ---- Tables -----------------------------------------------------------
    ROW_ALT = "#f8fafc"      # slate-50 — barely-there zebra stripe
    ROW_HOVER = "#eff6ff"    # blue-50 — hover hint
    SELECT_BG = "#e0e7ff"    # indigo-100 — harmonizes with primary
    SELECT_FG = "#3730a3"    # indigo-800
    HEADING_BG = "#1e1b4b"   # match the brand header
    HEADING_HOVER = "#312e81"  # indigo-900

    # ---- Scrollbar --------------------------------------------------------
    SCROLL_THUMB = "#cbd5e1"
    SCROLL_THUMB_HOVER = "#94a3b8"

    # ---- Status semantics (kept aligned with the accents above) ----------
    STATUS_ACTIVE = "#4f46e5"
    STATUS_OVERDUE = "#e11d48"
    STATUS_RETURNED = "#64748b"
    STATUS_AVAIL = "#059669"
    STATUS_UNAVAIL = "#e11d48"

    # ---- Chip / badge backgrounds (pill-style status indicators) ----------
    CHIP_ACTIVE_BG = "#e0e7ff"
    CHIP_ACTIVE_FG = "#3730a3"
    CHIP_SUCCESS_BG = "#d1fae5"
    CHIP_SUCCESS_FG = "#065f46"
    CHIP_WARNING_BG = "#fef3c7"
    CHIP_WARNING_FG = "#92400e"
    CHIP_DANGER_BG = "#ffe4e6"
    CHIP_DANGER_FG = "#9f1239"
    CHIP_NEUTRAL_BG = "#f1f5f9"
    CHIP_NEUTRAL_FG = "#475569"

    # ---- Dividers & shadows (simulated via flat borders) ------------------
    SHADOW = "#d1d5db"       # gray-300 — card shadow simulation


# --------------------------------------------------------------------------- #
#  Fonts
# --------------------------------------------------------------------------- #
def _family() -> str:
    if sys.platform == "darwin":
        # Helvetica Neue is present on every modern macOS and reads cleaner
        # than plain Helvetica while keeping near-identical metrics.
        return "Helvetica Neue"
    if sys.platform.startswith("win"):
        return "Segoe UI"
    return "DejaVu Sans"


def _base_size() -> int:
    if sys.platform == "darwin":
        return 13
    return 10


def base_font() -> tuple[str, int]:
    return (_family(), _base_size())


def small_font() -> tuple[str, int]:
    return (_family(), max(9, _base_size() - 2))


def heading_font() -> tuple[str, int, str]:
    return (_family(), _base_size(), "bold")


def title_font() -> tuple[str, int, str]:
    return (_family(), _base_size() + 7, "bold")


def display_font() -> tuple[str, int, str]:
    """Extra-large number font for KPI cards."""
    return (_family(), _base_size() + 11, "bold")


def label_font() -> tuple[str, int]:
    """Small caps-like label font for field labels."""
    return (_family(), max(9, _base_size() - 1))


# --------------------------------------------------------------------------- #
#  Style setup
# --------------------------------------------------------------------------- #
def setup_styles(root: tk.Tk) -> None:
    """Apply the application-wide ttk style configuration."""
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    f = base_font()
    small = small_font()
    root.configure(bg=Palette.BG)

    # ---- Base / frames ----------------------------------------------------
    style.configure(".", font=f, background=Palette.BG, foreground=Palette.TEXT)
    style.configure("TFrame", background=Palette.BG)
    style.configure("Surface.TFrame", background=Palette.SURFACE)
    style.configure("Card.TFrame",
                    background=Palette.SURFACE,
                    relief="flat")
    style.configure("Header.TFrame", background=Palette.HEADER_BG)
    # Thin accent strip drawn beneath the header band by TabHeader.
    style.configure("Accent.TFrame", background=Palette.ACCENT_BAR)
    style.configure("Divider.TFrame", background=Palette.BORDER)

    # ---- Labels -----------------------------------------------------------
    style.configure("TLabel", background=Palette.BG, foreground=Palette.TEXT)
    style.configure("Surface.TLabel",
                    background=Palette.SURFACE, foreground=Palette.TEXT)
    style.configure("Card.TLabel",
                    background=Palette.SURFACE, foreground=Palette.TEXT)
    style.configure("Header.TLabel",
                    background=Palette.HEADER_BG, foreground=Palette.HEADER_FG,
                    font=title_font())
    style.configure("Subtitle.TLabel",
                    background=Palette.HEADER_BG,
                    foreground=Palette.HEADER_ACCENT, font=f)
    style.configure("Muted.TLabel",
                    background=Palette.BG, foreground=Palette.MUTED)
    style.configure("SurfaceMuted.TLabel",
                    background=Palette.SURFACE, foreground=Palette.MUTED)
    style.configure("SectionTitle.TLabel",
                    background=Palette.SURFACE, foreground=Palette.TEXT,
                    font=heading_font())
    style.configure("FieldLabel.TLabel",
                    background=Palette.SURFACE, foreground=Palette.MUTED,
                    font=label_font())
    style.configure("KPIValue.TLabel",
                    background=Palette.SURFACE, foreground=Palette.PRIMARY,
                    font=display_font())
    style.configure("KPILabel.TLabel",
                    background=Palette.SURFACE, foreground=Palette.MUTED,
                    font=small)

    # ---- Entries ----------------------------------------------------------
    style.configure("TEntry",
                    fieldbackground=Palette.SURFACE,
                    foreground=Palette.TEXT,
                    bordercolor=Palette.BORDER,
                    lightcolor=Palette.BORDER,
                    darkcolor=Palette.BORDER,
                    insertcolor=Palette.PRIMARY,
                    padding=(10, 8))
    style.map("TEntry",
              bordercolor=[("focus", Palette.PRIMARY)],
              lightcolor=[("focus", Palette.BORDER_FOCUS)],
              darkcolor=[("focus", Palette.BORDER_FOCUS)])

    # ---- Combobox (match entries; harmonize the popdown) ------------------
    style.configure("TCombobox",
                    fieldbackground=Palette.SURFACE,
                    background=Palette.SURFACE,
                    foreground=Palette.TEXT,
                    bordercolor=Palette.BORDER,
                    lightcolor=Palette.BORDER,
                    darkcolor=Palette.BORDER,
                    arrowcolor=Palette.MUTED,
                    padding=(8, 6))
    style.map("TCombobox",
              bordercolor=[("focus", Palette.PRIMARY)],
              lightcolor=[("focus", Palette.BORDER_FOCUS)],
              darkcolor=[("focus", Palette.BORDER_FOCUS)],
              fieldbackground=[("readonly", Palette.SURFACE)],
              arrowcolor=[("active", Palette.PRIMARY)])

    # ---- Checkbutton ------------------------------------------------------
    style.configure("TCheckbutton",
                    background=Palette.BG, foreground=Palette.TEXT,
                    indicatorcolor=Palette.SURFACE,
                    indicatorbackground=Palette.SURFACE,
                    indicatorrelief="flat",
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
                  ("active", Palette.PRIMARY_SOFT),
              ])

    # ---- Notebook (pill tabs with hover) ---------------------------------
    style.configure("TNotebook",
                    background=Palette.BG, borderwidth=0,
                    tabmargins=(10, 10, 10, 0))
    style.configure("TNotebook.Tab",
                    padding=(28, 13), background=Palette.NEUTRAL,
                    foreground=Palette.NEUTRAL_FG, font=heading_font(),
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", Palette.PRIMARY),
                          ("active", Palette.PRIMARY_SOFT)],
              foreground=[("selected", Palette.PRIMARY_FG),
                          ("active", Palette.PRIMARY)],
              expand=[("selected", (1, 1, 1, 0))])

    # ---- Treeview ---------------------------------------------------------
    style.configure("Treeview",
                    background=Palette.SURFACE,
                    fieldbackground=Palette.SURFACE,
                    foreground=Palette.TEXT,
                    rowheight=28, borderwidth=0, font=f)
    style.configure("Treeview.Heading",
                    background=Palette.HEADING_BG, foreground="#ffffff",
                    font=heading_font(), padding=(12, 11),
                    borderwidth=0, relief="flat")
    style.map("Treeview.Heading",
              background=[("active", Palette.HEADING_HOVER)],
              foreground=[("active", "#ffffff")])
    style.map("Treeview",
              background=[("selected", Palette.SELECT_BG)],
              foreground=[("selected", Palette.SELECT_FG)])

    # ---- Scrollbars (thin, minimal) --------------------------------------
    for orient in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(orient,
                        troughcolor=Palette.BG,
                        background=Palette.SCROLL_THUMB,
                        bordercolor=Palette.BG,
                        arrowcolor=Palette.BG,
                        relief="flat", borderwidth=0)
        style.map(orient,
                  background=[("active", Palette.SCROLL_THUMB_HOVER),
                              ("pressed", Palette.SCROLL_THUMB_HOVER)])

    # ---- Separator --------------------------------------------------------
    style.configure("TSeparator", background=Palette.BORDER)

    # ---- Buttons ----------------------------------------------------------
    def _btn(name: str, bg: str, fg: str, hover: str) -> None:
        style.configure(name, background=bg, foreground=fg,
                        font=heading_font(), padding=(18, 10),
                        borderwidth=0, focusthickness=0, relief="flat")
        style.map(name,
                  background=[("pressed", hover), ("active", hover),
                              ("disabled", "#cbd5e1")],
                  foreground=[("disabled", "#94a3b8")])

    _btn("Primary.TButton", Palette.PRIMARY, Palette.PRIMARY_FG, Palette.PRIMARY_HOVER)
    _btn("Success.TButton", Palette.SUCCESS, Palette.SUCCESS_FG, Palette.SUCCESS_HOVER)
    _btn("Warning.TButton", Palette.WARNING, Palette.WARNING_FG, Palette.WARNING_HOVER)
    _btn("Danger.TButton", Palette.DANGER, Palette.DANGER_FG, Palette.DANGER_HOVER)
    _btn("Purple.TButton", Palette.PURPLE, Palette.PURPLE_FG, Palette.PURPLE_HOVER)
    _btn("Neutral.TButton", Palette.NEUTRAL, Palette.NEUTRAL_FG, Palette.NEUTRAL_HOVER)
    _btn("Whatsapp.TButton", Palette.WHATSAPP, Palette.WHATSAPP_FG, Palette.WHATSAPP_HOVER)

    # Compact variant for inline icon-buttons (e.g., calendar picker).
    style.configure("Compact.TButton",
                    background=Palette.NEUTRAL, foreground=Palette.NEUTRAL_FG,
                    font=f, padding=(6, 2), borderwidth=0,
                    focusthickness=0, relief="flat")
    style.map("Compact.TButton",
              background=[("active", Palette.NEUTRAL_HOVER),
                          ("pressed", Palette.NEUTRAL_HOVER),
                          ("disabled", "#cbd5e1")],
              foreground=[("disabled", "#94a3b8")])

    # Icon-only pill button — for small badge actions in headers
    style.configure("IconPill.TButton",
                    background=Palette.HEADER_BADGE_BG,
                    foreground=Palette.HEADER_ACCENT,
                    font=small, padding=(8, 4),
                    borderwidth=0, focusthickness=0, relief="flat")
    style.map("IconPill.TButton",
              background=[("active", Palette.ACCENT_BAR),
                          ("pressed", Palette.ACCENT_BAR)],
              foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])

    # ---- Progress bar (used for renewal counter) -------------------------
    style.configure("TProgressbar",
                    troughcolor=Palette.BORDER,
                    background=Palette.PRIMARY,
                    bordercolor=Palette.BORDER,
                    lightcolor=Palette.PRIMARY,
                    darkcolor=Palette.PRIMARY,
                    thickness=8)

    # ---- Status bar -------------------------------------------------------
    style.configure("Status.TLabel",
                    background=Palette.HEADER_BG, foreground=Palette.HEADER_ACCENT,
                    padding=(16, 8), font=small)
    style.configure("StatusClock.TLabel",
                    background=Palette.HEADER_BG, foreground="#6366f1",
                    padding=(16, 8), font=small)
