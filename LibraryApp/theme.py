#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:33:11 2026

@author: ashergabrieljose
"""

# /workspace/theme.py
"""Centralised colour palette and ttk style setup. Cross-platform (Mac/Windows/Linux)."""
import platform
import tkinter as tk
from tkinter import ttk

# Modern, friendly palette
PALETTE = {
    "bg":         "#F4F6FB",   # window background
    "surface":    "#FFFFFF",   # cards/tables
    "primary":    "#3B82F6",   # blue
    "primary_dk": "#2563EB",
    "accent":     "#8B5CF6",   # purple
    "success":    "#10B981",
    "warning":    "#F59E0B",
    "danger":     "#EF4444",
    "text":       "#1F2937",
    "muted":      "#6B7280",
    "border":     "#E5E7EB",
    "row_alt":    "#F9FAFB",
    "sel_bg":     "#DBEAFE",
    "sel_fg":     "#1E3A8A",
    "header_bg":  "#1E293B",
    "header_fg":  "#FFFFFF",
}

FONT_FAMILY = "SF Pro Text" if platform.system() == "Darwin" else "Segoe UI"
FONT_BASE   = (FONT_FAMILY, 10)
FONT_BOLD   = (FONT_FAMILY, 10, "bold")
FONT_TITLE  = (FONT_FAMILY, 18, "bold")
FONT_HEAD   = (FONT_FAMILY, 11, "bold")


def apply_theme(root: tk.Tk):
    style = ttk.Style(root)
    # 'clam' is the most theme-able and looks consistent on Mac + Windows.
    if "clam" in style.theme_names():
        style.theme_use("clam")

    P = PALETTE
    root.configure(bg=P["bg"])

    # General
    style.configure(".", background=P["bg"], foreground=P["text"], font=FONT_BASE)
    style.configure("TFrame", background=P["bg"])
    style.configure("Card.TFrame", background=P["surface"], relief="flat")
    style.configure("Header.TFrame", background=P["header_bg"])

    style.configure("TLabel", background=P["bg"], foreground=P["text"], font=FONT_BASE)
    style.configure("Title.TLabel", background=P["header_bg"], foreground=P["header_fg"],
                    font=FONT_TITLE, padding=(16, 12))
    style.configure("Subtitle.TLabel", background=P["header_bg"], foreground="#CBD5E1",
                    font=(FONT_FAMILY, 10))
    style.configure("Card.TLabel", background=P["surface"], foreground=P["text"])
    style.configure("Muted.TLabel", background=P["bg"], foreground=P["muted"])

    # Entries / Combos
    style.configure("TEntry", fieldbackground=P["surface"], foreground=P["text"],
                    bordercolor=P["border"], lightcolor=P["border"],
                    darkcolor=P["border"], padding=6)
    style.map("TEntry", bordercolor=[("focus", P["primary"])])
    style.configure("TCombobox", fieldbackground=P["surface"], background=P["surface"],
                    foreground=P["text"], padding=5, arrowcolor=P["primary"])
    style.map("TCombobox",
              fieldbackground=[("readonly", P["surface"])],
              foreground=[("readonly", P["text"])])

    # Checkbutton
    style.configure("TCheckbutton", background=P["bg"], foreground=P["text"])

    # --- Buttons (colourful, flat, hover-aware) ---
    def _btn(name, bg, hover, fg="#FFFFFF"):
        style.configure(name, background=bg, foreground=fg, font=FONT_BOLD,
                        borderwidth=0, focusthickness=0, padding=(14, 8))
        style.map(name,
                  background=[("active", hover), ("pressed", hover), ("disabled", "#CBD5E1")],
                  foreground=[("disabled", "#6B7280")])

    _btn("Primary.TButton", P["primary"],  P["primary_dk"])
    _btn("Success.TButton", P["success"],  "#059669")
    _btn("Danger.TButton",  P["danger"],   "#DC2626")
    _btn("Warning.TButton", P["warning"],  "#D97706")
    _btn("Accent.TButton",  P["accent"],   "#7C3AED")
    _btn("Ghost.TButton",   "#E5E7EB",     "#D1D5DB", fg=P["text"])

    # Notebook tabs
    style.configure("TNotebook", background=P["bg"], borderwidth=0, tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab",
                    background="#E5E7EB", foreground=P["text"],
                    padding=(20, 10), font=FONT_BOLD, borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", P["primary"]), ("active", "#CBD5E1")],
              foreground=[("selected", "#FFFFFF")],
              expand=[("selected", (1, 1, 1, 0))])

    # Treeview
    style.configure("Treeview",
                    background=P["surface"], fieldbackground=P["surface"],
                    foreground=P["text"], rowheight=28, borderwidth=0, font=FONT_BASE)
    style.configure("Treeview.Heading",
                    background=P["header_bg"], foreground=P["header_fg"],
                    font=FONT_HEAD, padding=8, borderwidth=0, relief="flat")
    style.map("Treeview.Heading", background=[("active", "#334155")])
    style.map("Treeview",
              background=[("selected", P["sel_bg"])],
              foreground=[("selected", P["sel_fg"])])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=P["bg"],
                    troughcolor=P["bg"], bordercolor=P["bg"],
                    arrowcolor=P["muted"], gripcount=0)

    # Statusbar
    style.configure("Status.TLabel", background="#1E293B", foreground="#E2E8F0",
                    padding=(10, 6), font=(FONT_FAMILY, 9))