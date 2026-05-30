"""Shared UI helper utilities.

Small, pure functions that multiple widgets/dialogs can import without
creating circular dependencies. Nothing here should import from a specific
tab or dialog — only from `theme`.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import Palette, base_font, heading_font, small_font


def make_card(
    parent: tk.Widget,
    *,
    padx: int = 16,
    pady: int = 14,
    border_color: str = Palette.BORDER,
    bg: str = Palette.SURFACE,
) -> tk.Frame:
    """Return a visually elevated card frame with a subtle border."""
    outer = tk.Frame(parent, bg=border_color)
    inner = tk.Frame(outer, bg=bg, padx=padx, pady=pady)
    inner.pack(padx=1, pady=1, fill="both", expand=True)
    return inner


def make_section_label(
    parent: tk.Widget,
    text: str,
    bg: str = Palette.SURFACE,
) -> tk.Label:
    """Return a styled section heading label."""
    return tk.Label(
        parent, text=text, bg=bg, fg=Palette.PRIMARY,
        font=heading_font(),
    )


def make_field_label(
    parent: tk.Widget,
    text: str,
    bg: str = Palette.SURFACE,
    required: bool = False,
) -> tk.Label:
    """Return a styled field label, with optional red asterisk for required."""
    display = f"{text}  *" if required else text
    return tk.Label(
        parent, text=display, bg=bg,
        fg=Palette.MUTED if not required else Palette.DANGER,
        font=small_font(),
    )


def make_divider(parent: tk.Widget, bg: str = Palette.SURFACE) -> tk.Frame:
    """A 1px horizontal divider line."""
    line = tk.Frame(parent, bg=Palette.BORDER, height=1)
    return line


def status_chip(
    parent: tk.Widget,
    text: str,
    kind: str = "neutral",
    *,
    bg_override: str | None = None,
    fg_override: str | None = None,
) -> tk.Label:
    """Pill-shaped status chip. `kind` ∈ active | success | warning | danger | neutral."""
    _CHIPS = {
        "active":  (Palette.CHIP_ACTIVE_BG,  Palette.CHIP_ACTIVE_FG),
        "success": (Palette.CHIP_SUCCESS_BG, Palette.CHIP_SUCCESS_FG),
        "warning": (Palette.CHIP_WARNING_BG, Palette.CHIP_WARNING_FG),
        "danger":  (Palette.CHIP_DANGER_BG,  Palette.CHIP_DANGER_FG),
        "neutral": (Palette.CHIP_NEUTRAL_BG, Palette.CHIP_NEUTRAL_FG),
    }
    bg, fg = _CHIPS.get(kind, _CHIPS["neutral"])
    if bg_override:
        bg = bg_override
    if fg_override:
        fg = fg_override
    return tk.Label(
        parent, text=f"  {text}  ",
        bg=bg, fg=fg,
        font=small_font(),
        padx=2, pady=2,
    )


#: Reserved screen margins (px) so a dialog never butts against the OS
#: taskbar / window chrome. Height margin is larger because that's where the
#: Windows taskbar lives and where footer action bars would otherwise hide.
_SCREEN_MARGIN_W = 40
_SCREEN_MARGIN_H = 96


def center_window(
    window: tk.Toplevel,
    parent: tk.Widget,
    width: int,
    height: int,
) -> None:
    """Center `window` over `parent`, clamped to fit the physical screen.

    Dialogs declare an *ideal* width/height, but on small or display-scaled
    monitors (e.g. a 1366×768 laptop at 125 % scaling) a tall dialog would
    extend below the taskbar and hide its footer buttons — exactly the
    "can't see Borrow / Cancel" symptom. We therefore cap the requested size
    to the available screen area and re-clamp the position so the *entire*
    window, crucially its bottom action bar, stays on-screen. When the ideal
    size already fits, behaviour is unchanged (a plain centred window).
    """
    window.update_idletasks()

    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()

    # Never let a dialog be taller/wider than the usable screen.
    width = min(width, screen_w - _SCREEN_MARGIN_W)
    height = min(height, screen_h - _SCREEN_MARGIN_H)

    # Centre over the parent…
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2

    # …then clamp so neither edge spills off-screen (keeps the footer visible).
    x = max(0, min(x, screen_w - width - _SCREEN_MARGIN_W // 2))
    y = max(0, min(y, screen_h - height - _SCREEN_MARGIN_H // 2))

    window.geometry(f"{width}x{height}+{x}+{y}")


def dialog_chrome(
    window: tk.Toplevel,
    parent: tk.Widget,
    title: str,
    icon: str,
    subtitle: str = "",
) -> ttk.Frame:
    """Apply standard dialog chrome (title, header banner) and return the body frame.

    Handles: configure bg, transient, grab_set, header with icon+title+subtitle,
    accent strip. Returns the body Frame the caller packs its content into.
    """
    window.configure(bg=Palette.SURFACE)
    window.transient(parent.winfo_toplevel())
    window.grab_set()

    # Header
    header = ttk.Frame(window, style="Header.TFrame")
    header.pack(fill="x", side="top")

    inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14, 22, 14))
    inner_h.pack(fill="x")
    ttk.Label(inner_h, text=f"{icon}  {title}",
              style="Header.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(inner_h, text=subtitle,
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

    accent = ttk.Frame(window, style="Accent.TFrame", height=4)
    accent.pack(fill="x", side="top")
    accent.pack_propagate(False)

    return header  # caller may need the reference; body is caller's responsibility
