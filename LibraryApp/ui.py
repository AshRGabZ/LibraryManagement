#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:18:15 2026

@author: ashergabrieljose
"""
# /workspace/ui.py
"""
Tkinter UI for the Library Management application.
Modern, colourful, cross-platform (Windows / macOS / Linux).
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from models import BookModel, MemberModel, LoanModel


# --------------------------------------------------------------------------- #
#  Theme / palette
# --------------------------------------------------------------------------- #
class Palette:
    BG          = "#f4f6fb"
    SURFACE     = "#ffffff"
    HEADER_BG   = "#1f2937"
    HEADER_FG   = "#ffffff"
    BORDER      = "#e5e7eb"
    TEXT        = "#111827"
    MUTED       = "#6b7280"

    PRIMARY     = "#2563eb"
    PRIMARY_FG  = "#ffffff"
    SUCCESS     = "#16a34a"
    SUCCESS_FG  = "#ffffff"
    WARNING     = "#d97706"
    WARNING_FG  = "#ffffff"
    DANGER      = "#dc2626"
    DANGER_FG   = "#ffffff"
    PURPLE      = "#7c3aed"
    PURPLE_FG   = "#ffffff"
    NEUTRAL     = "#e5e7eb"
    NEUTRAL_FG  = "#111827"

    ROW_ALT     = "#f9fafb"
    SELECT_BG   = "#dbeafe"
    SELECT_FG   = "#1e3a8a"

    STATUS_ACTIVE   = "#2563eb"
    STATUS_OVERDUE  = "#dc2626"
    STATUS_RETURNED = "#6b7280"
    STATUS_AVAIL    = "#16a34a"
    STATUS_UNAVAIL  = "#dc2626"


def base_font():
    if sys.platform == "darwin":
        return ("Helvetica", 13)
    if sys.platform.startswith("win"):
        return ("Segoe UI", 10)
    return ("DejaVu Sans", 10)


def heading_font():
    f = base_font()
    return (f[0], f[1], "bold")


def title_font():
    f = base_font()
    return (f[0], f[1] + 6, "bold")


# --------------------------------------------------------------------------- #
#  Style setup
# --------------------------------------------------------------------------- #
def setup_styles(root):
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
    style.configure("Surface.TLabel", background=Palette.SURFACE, foreground=Palette.TEXT)
    style.configure("Header.TLabel", background=Palette.HEADER_BG,
                    foreground=Palette.HEADER_FG, font=title_font())
    style.configure("Subtitle.TLabel", background=Palette.HEADER_BG,
                    foreground="#cbd5e1", font=f)
    style.configure("Muted.TLabel", background=Palette.BG, foreground=Palette.MUTED)
    style.configure("SurfaceMuted.TLabel", background=Palette.SURFACE, foreground=Palette.MUTED)
    style.configure("SectionTitle.TLabel", background=Palette.SURFACE,
                    foreground=Palette.TEXT, font=heading_font())

    style.configure("TEntry",
                    fieldbackground=Palette.SURFACE,
                    bordercolor=Palette.BORDER,
                    lightcolor=Palette.BORDER,
                    darkcolor=Palette.BORDER,
                    padding=6)
    style.map("TEntry", bordercolor=[("focus", Palette.PRIMARY)])

    style.configure("TCheckbutton", background=Palette.BG, foreground=Palette.TEXT)

    # Notebook
    style.configure("TNotebook", background=Palette.BG, borderwidth=0,
                    tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab", padding=(20, 10),
                    background="#e5e7eb", foreground=Palette.TEXT,
                    font=heading_font(), borderwidth=0)
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
    def make_btn(name, bg, fg, active):
        style.configure(name, background=bg, foreground=fg,
                        font=heading_font(), padding=(14, 8),
                        borderwidth=0, focusthickness=0, relief="flat")
        style.map(name,
                  background=[("active", active), ("disabled", "#cbd5e1")],
                  foreground=[("disabled", "#6b7280")])

    make_btn("Primary.TButton", Palette.PRIMARY, Palette.PRIMARY_FG, "#1d4ed8")
    make_btn("Success.TButton", Palette.SUCCESS, Palette.SUCCESS_FG, "#15803d")
    make_btn("Warning.TButton", Palette.WARNING, Palette.WARNING_FG, "#b45309")
    make_btn("Danger.TButton",  Palette.DANGER,  Palette.DANGER_FG,  "#b91c1c")
    make_btn("Purple.TButton",  Palette.PURPLE,  Palette.PURPLE_FG,  "#6d28d9")
    make_btn("Neutral.TButton", Palette.NEUTRAL, Palette.NEUTRAL_FG, "#d1d5db")

    style.configure("Status.TLabel",
                    background="#111827", foreground="#e5e7eb",
                    padding=(10, 6), font=f)


# --------------------------------------------------------------------------- #
#  Reusable widgets
# --------------------------------------------------------------------------- #
class TabHeader(ttk.Frame):
    def __init__(self, parent, icon, title, subtitle):
        super().__init__(parent, style="Header.TFrame")
        inner = ttk.Frame(self, style="Header.TFrame", padding=(20, 16))
        inner.pack(fill="x")
        ttk.Label(inner, text=f"{icon}  {title}", style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))


class FormDialog(tk.Toplevel):
    def __init__(self, parent, title, fields, initial=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=Palette.SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._entries = {}
        initial = initial or {}

        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Header.TLabel").pack(
            anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        for i, (key, label) in enumerate(fields):
            tk.Label(body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                     font=base_font()).grid(row=i, column=0, sticky="w", pady=(6, 2))
            entry = ttk.Entry(body, width=38, font=base_font())
            entry.grid(row=i, column=1, pady=(6, 2), padx=(12, 0), sticky="ew")
            if key in initial and initial[key] is not None:
                entry.insert(0, str(initial[key]))
            self._entries[key] = entry

        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save", style="Primary.TButton",
                   command=self._on_ok).pack(side="right")

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        list(self._entries.values())[0].focus_set()

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x,0)}+{max(y,0)}")
        self.wait_window(self)

    def _on_ok(self):
        self.result = {k: e.get().strip() for k, e in self._entries.items()}
        self.destroy()


def build_treeview(parent, columns_spec):
    container = ttk.Frame(parent, style="Surface.TFrame")
    keys = [c[0] for c in columns_spec]

    tree = ttk.Treeview(container, columns=keys, show="headings", selectmode="browse")
    for key, heading, width, anchor in columns_spec:
        tree.heading(key, text=heading, anchor=anchor)
        tree.column(key, width=width, anchor=anchor, stretch=True)

    vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.tag_configure("odd",  background=Palette.SURFACE)
    tree.tag_configure("even", background=Palette.ROW_ALT)
    tree.tag_configure("status_active",   foreground=Palette.STATUS_ACTIVE)
    tree.tag_configure("status_overdue",  foreground=Palette.STATUS_OVERDUE)
    tree.tag_configure("status_returned", foreground=Palette.STATUS_RETURNED)
    tree.tag_configure("status_avail",    foreground=Palette.STATUS_AVAIL)
    tree.tag_configure("status_unavail",  foreground=Palette.STATUS_UNAVAIL)
    return container, tree


# --------------------------------------------------------------------------- #
#  Books tab
# --------------------------------------------------------------------------- #
class BooksTab(ttk.Frame):
    COLUMNS = [
        ("id",        "ID",        60,  "center"),
        ("title",     "Title",     260, "w"),
        ("author",    "Author",    180, "w"),
        ("isbn",      "ISBN",      130, "center"),
        ("year",      "Year",      80,  "center"),
        ("available", "Available", 90,  "center"),
        ("total",     "Total",     80,  "center"),
        ("status",    "Status",    120, "center"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        TabHeader(self, "📚", "GHCC Library Management", "Manage your catalogue").pack(fill="x")

        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="🔎", bg=Palette.BG,
                 font=(base_font()[0], base_font()[1] + 2)).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search_var, width=32,
                  font=base_font()).pack(side="left")

        ttk.Button(toolbar, text="➕ Add Book", style="Success.TButton",
                   command=self.add_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="✏ Edit", style="Primary.TButton",
                   command=self.edit_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🗑 Delete", style="Danger.TButton",
                   command=self.delete_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻ Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)

        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tree.bind("<Double-1>", lambda e: self.edit_book())

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for i, b in enumerate(BookModel.list_all(self.search_var.get())):
            available = b["available_copies"] > 0
            status = "● Available" if available else "● Unavailable"
            row_tag = "even" if i % 2 else "odd"
            status_tag = "status_avail" if available else "status_unavail"
            self.tree.insert(
                "", "end",
                values=(b["id"], b["title"], b["author"], b["isbn"] or "—",
                        b["year"] or "—", b["available_copies"],
                        b["total_copies"], status),
                tags=(row_tag, status_tag),
            )

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a book", "Please select a book first.")
            return None
        return int(self.tree.item(sel[0])["values"][0])

    def add_book(self):
        dlg = FormDialog(self.winfo_toplevel(), "Add Book",
            [("title", "Title"), ("author", "Author"), ("isbn", "ISBN"),
             ("year", "Year"), ("total_copies", "Total Copies")])
        if not dlg.result:
            return
        data = dlg.result
        if not data["title"] or not data["author"]:
            messagebox.showerror("Validation", "Title and Author are required.")
            return
        try:
            year = int(data["year"]) if data["year"] else None
            total = int(data["total_copies"]) if data["total_copies"] else 1
            if total < 1:
                raise ValueError("Total copies must be at least 1.")
            BookModel.add(data["title"], data["author"], data["isbn"], year, total)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_book(self):
        bid = self._selected_id()
        if bid is None:
            return
        book = BookModel.get(bid)
        initial = {"title": book["title"], "author": book["author"],
                   "isbn": book["isbn"], "year": book["year"],
                   "total_copies": book["total_copies"]}
        dlg = FormDialog(self.winfo_toplevel(), "Edit Book",
            [("title", "Title"), ("author", "Author"), ("isbn", "ISBN"),
             ("year", "Year"), ("total_copies", "Total Copies")],
            initial=initial)
        if not dlg.result:
            return
        data = dlg.result
        try:
            year = int(data["year"]) if data["year"] else None
            total = int(data["total_copies"]) if data["total_copies"] else 1
            if total < 1:
                raise ValueError("Total copies must be at least 1.")
            BookModel.update(bid, data["title"], data["author"], data["isbn"], year, total)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_book(self):
        bid = self._selected_id()
        if bid is None:
            return
        book = BookModel.get(bid)
        active = [ln for ln in LoanModel.list_all(active_only=True)
                  if ln["book_id"] == bid]
        if active:
            messagebox.showerror("Cannot delete",
                f"'{book['title']}' is currently borrowed "
                f"({len(active)} active loan(s)).\n\n"
                "Please ensure all copies are returned before deleting.")
            return
        if messagebox.askyesno("Confirm", f"Delete '{book['title']}'?"):
            try:
                BookModel.delete(bid)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))


# --------------------------------------------------------------------------- #
#  Members tab
# --------------------------------------------------------------------------- #
class MembersTab(ttk.Frame):
    COLUMNS = [
        ("id",     "ID",     60,  "center"),
        ("name",   "Name",   220, "w"),
        ("email",  "Email",  240, "w"),
        ("phone",  "Phone",  150, "center"),
        ("joined", "Joined", 120, "center"),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        TabHeader(self, "👥", "Members", "Manage library members").pack(fill="x")

        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="🔎", bg=Palette.BG,
                 font=(base_font()[0], base_font()[1] + 2)).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search_var, width=32,
                  font=base_font()).pack(side="left")

        ttk.Button(toolbar, text="➕ Add Member", style="Success.TButton",
                   command=self.add_member).pack(side="right", padx=4)
        ttk.Button(toolbar, text="✏ Edit", style="Primary.TButton",
                   command=self.edit_member).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🗑 Delete", style="Danger.TButton",
                   command=self.delete_member).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻ Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)

        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tree.bind("<Double-1>", lambda e: self.edit_member())

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for i, m in enumerate(MemberModel.list_all(self.search_var.get())):
            row_tag = "even" if i % 2 else "odd"
            self.tree.insert("", "end",
                values=(m["id"], m["name"], m["email"] or "—",
                        m["phone"] or "—", m["joined"]),
                tags=(row_tag,))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a member", "Please select a member first.")
            return None
        return int(self.tree.item(sel[0])["values"][0])

    def add_member(self):
        dlg = FormDialog(self.winfo_toplevel(), "Add Member",
            [("name", "Name"), ("email", "Email"), ("phone", "Phone")])
        if not dlg.result:
            return
        data = dlg.result
        if not data["name"]:
            messagebox.showerror("Validation", "Name is required.")
            return
        try:
            MemberModel.add(data["name"], data["email"], data["phone"])
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_member(self):
        mid = self._selected_id()
        if mid is None:
            return
        member = MemberModel.get(mid)
        initial = {"name": member["name"], "email": member["email"],
                   "phone": member["phone"]}
        dlg = FormDialog(self.winfo_toplevel(), "Edit Member",
            [("name", "Name"), ("email", "Email"), ("phone", "Phone")],
            initial=initial)
        if not dlg.result:
            return
        data = dlg.result
        if not data["name"]:
            messagebox.showerror("Validation", "Name is required.")
            return
        try:
            MemberModel.update(mid, data["name"], data["email"], data["phone"])
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_member(self):
        mid = self._selected_id()
        if mid is None:
            return
        active = [ln for ln in LoanModel.list_all(active_only=True)
                  if ln["member_id"] == mid]
        if active:
            messagebox.showerror("Cannot delete",
                f"This member has {len(active)} active loan(s).\n"
                "Please ensure all books are returned before deleting.")
            return
        if messagebox.askyesno("Confirm", "Delete this member?"):
            try:
                MemberModel.delete(mid)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))


# --------------------------------------------------------------------------- #
#  Loans tab
# --------------------------------------------------------------------------- #
class LoansTab(ttk.Frame):
    COLUMNS = [
        ("id",        "ID",        60,  "center"),
        ("book",      "Book",      240, "w"),
        ("member",    "Member",    180, "w"),
        ("borrowed",  "Borrowed",  110, "center"),
        ("due",       "Due",       110, "center"),
        ("returned",  "Returned",  110, "center"),
        ("renewals",  "Renewals",  90,  "center"),
        ("status",    "Status",    120, "center"),
    ]

    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self.on_change = on_change or (lambda: None)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        TabHeader(self, "🔄", "Loans", "Borrow, renew and return books").pack(fill="x")

        toolbar = tk.Frame(self, bg=Palette.BG, pady=10, padx=14)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="🔎", bg=Palette.BG,
                 font=(base_font()[0], base_font()[1] + 2)).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(toolbar, textvariable=self.search_var, width=28,
                  font=base_font()).pack(side="left")

        self.active_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Active only", variable=self.active_var,
                        command=self.refresh).pack(side="left", padx=12)

        ttk.Button(toolbar, text="📖 Borrow", style="Success.TButton",
                   command=self.borrow_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="🔁 Renew", style="Purple.TButton",
                   command=self.renew_loan).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↩ Return", style="Primary.TButton",
                   command=self.return_book).pack(side="right", padx=4)
        ttk.Button(toolbar, text="↻ Refresh", style="Neutral.TButton",
                   command=self.refresh).pack(side="right", padx=4)

        container, self.tree = build_treeview(self, self.COLUMNS)
        container.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        today = date.today().isoformat()
        loans = LoanModel.list_all(active_only=self.active_var.get(),
                                   search=self.search_var.get())
        for i, ln in enumerate(loans):
            if ln["returned_on"]:
                status, stag = "✓ Returned", "status_returned"
            elif ln["due_on"] and ln["due_on"] < today:
                status, stag = "⚠ Overdue", "status_overdue"
            else:
                status, stag = "● Active", "status_active"

            keys = ln.keys()
            renew_count = ln["renew_count"] if "renew_count" in keys else (
                ln["renewals"] if "renewals" in keys else 0)
            max_r = getattr(LoanModel, "MAX_RENEWALS", 3)
            renewals = f"{renew_count}/{max_r}"
            row_tag = "even" if i % 2 else "odd"

            self.tree.insert("", "end",
                values=(ln["id"], ln["book_title"], ln["member_name"],
                        ln["borrowed_on"], ln["due_on"] or "—",
                        ln["returned_on"] or "—", renewals, status),
                tags=(row_tag, stag))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a loan", "Please select a loan first.")
            return None
        return int(self.tree.item(sel[0])["values"][0])

    def borrow_book(self):
        books   = [b for b in BookModel.list_all() if b["available_copies"] > 0]
        members = MemberModel.list_all()
        if not books:
            messagebox.showwarning("No books", "No books available to borrow.")
            return
        if not members:
            messagebox.showwarning("No members", "Add a member first.")
            return
        BorrowDialog(self.winfo_toplevel(), books, members,
                     on_success=self._after_change)

    def return_book(self):
        lid = self._selected_id()
        if lid is None:
            return
        try:
            LoanModel.return_loan(lid)
            self._after_change()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def renew_loan(self):
        lid = self._selected_id()
        if lid is None:
            return
        RenewDialog(self.winfo_toplevel(), lid, on_success=self._after_change)

    def _after_change(self):
        self.refresh()
        self.on_change()


# --------------------------------------------------------------------------- #
#  Searchable picker (reused by BorrowDialog)
# --------------------------------------------------------------------------- #
class SearchablePicker(tk.Frame):
    """Search entry + scrollable listbox. Returns id of selected item."""

    def __init__(self, parent, items, formatter, search_keys,
                 placeholder="Search…", height=8):
        super().__init__(parent, bg=Palette.SURFACE)
        self.items = items
        self.formatter = formatter
        self.search_keys = search_keys
        self._filtered = []
        self.selected_id = None

        self.search_var = tk.StringVar()

        entry_wrap = tk.Frame(self, bg=Palette.BORDER, bd=0)
        entry_wrap.pack(fill="x")
        entry = tk.Entry(entry_wrap, textvariable=self.search_var,
                         font=base_font(), relief="flat", bd=0,
                         bg=Palette.SURFACE, fg=Palette.TEXT,
                         insertbackground=Palette.TEXT)
        entry.pack(fill="x", padx=1, pady=1, ipady=6, ipadx=8)
        self.entry = entry

        # Placeholder
        self._placeholder = placeholder
        self._placeholder_active = True
        entry.insert(0, placeholder)
        entry.config(fg=Palette.MUTED)

        def on_focus_in(_e):
            if self._placeholder_active:
                entry.delete(0, "end")
                entry.config(fg=Palette.TEXT)
                self._placeholder_active = False

        def on_focus_out(_e):
            if not self.search_var.get().strip():
                self._placeholder_active = True
                entry.delete(0, "end")
                entry.insert(0, placeholder)
                entry.config(fg=Palette.MUTED)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

        # Listbox
        list_wrap = tk.Frame(self, bg=Palette.BORDER, bd=0)
        list_wrap.pack(fill="both", expand=True, pady=(6, 0))

        self.listbox = tk.Listbox(
            list_wrap, height=height, font=base_font(),
            relief="flat", bd=0, bg=Palette.SURFACE, fg=Palette.TEXT,
            selectbackground=Palette.PRIMARY, selectforeground="white",
            activestyle="none", highlightthickness=0, exportselection=False,
        )
        self.listbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        sb = ttk.Scrollbar(list_wrap, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.search_var.trace_add("write", lambda *_: self._refilter())
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self._refilter()

    def _query(self):
        if self._placeholder_active:
            return ""
        return self.search_var.get().strip().lower()

    def _refilter(self):
        q = self._query()
        self.listbox.delete(0, "end")
        self._filtered = []
        for it in self.items:
            blob = " ".join(str(it[k] or "") for k in self.search_keys).lower()
            if q and q not in blob:
                continue
            label, disabled = self.formatter(it)
            self.listbox.insert("end", label)
            self._filtered.append(it)
            if disabled:
                self.listbox.itemconfig("end", fg=Palette.MUTED)
        self.selected_id = None

    def _on_select(self, _e):
        sel = self.listbox.curselection()
        if sel:
            self.selected_id = self._filtered[sel[0]]["id"]


# --------------------------------------------------------------------------- #
#  Borrow dialog
# --------------------------------------------------------------------------- #
class BorrowDialog(tk.Toplevel):
    def __init__(self, parent, books, members, on_success):
        super().__init__(parent)
        self.title("Borrow Book")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent)
        self.grab_set()
        self.on_success = on_success

        # Header
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="📖  Borrow a Book", style="Header.TLabel").pack(
            anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(3, weight=1)

        # ---- Book ----
        tk.Label(body, text="📚  Select Book", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        def fmt_book(b):
            avail = b["available_copies"]
            mark = "🟢" if avail > 0 else "🔴"
            label = f"  {mark}  {b['title']}  —  {b['author']}   ({avail}/{b['total_copies']} available)"
            return label, avail <= 0

        self.book_picker = SearchablePicker(
            body, books, fmt_book,
            search_keys=("title", "author", "isbn"),
            placeholder="🔍  Search by title, author or ISBN…",
            height=8,
        )
        self.book_picker.grid(row=1, column=0, sticky="nsew", pady=(0, 14))

        # ---- Member ----
        tk.Label(body, text="👤  Select Member", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        def fmt_member(m):
            extra = []
            if m["email"]:
                extra.append(m["email"])
            if m["phone"]:
                extra.append(m["phone"])
            tail = f"  ({' • '.join(extra)})" if extra else ""
            return f"  👤  {m['name']}{tail}", False

        self.member_picker = SearchablePicker(
            body, members, fmt_member,
            search_keys=("name", "email", "phone"),
            placeholder="🔍  Search by name, email or phone…",
            height=6,
        )
        self.member_picker.grid(row=3, column=0, sticky="nsew", pady=(0, 14))

        # ---- Loan period ----
        period = tk.Frame(body, bg=Palette.SURFACE)
        period.grid(row=4, column=0, sticky="w", pady=(0, 4))
        tk.Label(period, text="📅  Loan period:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()).pack(side="left")
        self.days_var = tk.StringVar(value="14")
        ttk.Entry(period, textvariable=self.days_var, width=6,
                  font=base_font()).pack(side="left", padx=(8, 4))
        tk.Label(period, text="days", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left")

        # ---- Buttons ----
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=14)
        btns.pack(fill="x")
        ttk.Button(btns, text="✓ Borrow", style="Success.TButton",
                   command=self._submit).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")

        # Size & center
        self.geometry("620x680")
        self.minsize(520, 560)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 620) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 680) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.bind("<Escape>", lambda e: self.destroy())

    def _submit(self):
        if not self.book_picker.selected_id:
            messagebox.showerror("Validation", "Please select a book.", parent=self)
            return
        if not self.member_picker.selected_id:
            messagebox.showerror("Validation", "Please select a member.", parent=self)
            return
        try:
            days = int(self.days_var.get()) if self.days_var.get().strip() else 14
            if days <= 0:
                raise ValueError("Loan days must be positive.")
            LoanModel.borrow(self.book_picker.selected_id,
                             self.member_picker.selected_id,
                             loan_days=days)
            self.destroy()
            self.on_success()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


# --------------------------------------------------------------------------- #
#  Renew dialog
# --------------------------------------------------------------------------- #
class RenewDialog(tk.Toplevel):
    def __init__(self, parent, loan_id, on_success):
        super().__init__(parent)
        self.title("Renew Loan")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.on_success = on_success
        self.loan_id = loan_id

        loan = LoanModel.get(loan_id)
        if not loan:
            messagebox.showerror("Error", "Loan not found.", parent=parent)
            self.destroy()
            return
        if loan["returned_on"]:
            messagebox.showerror("Error", "This loan has already been returned.",
                                 parent=parent)
            self.destroy()
            return

        keys = loan.keys()
        renew_count = loan["renew_count"] if "renew_count" in keys else (
            loan["renewals"] if "renewals" in keys else 0)
        max_r = getattr(LoanModel, "MAX_RENEWALS", 3)

        # Header
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="🔁  Renew Loan", style="Header.TLabel").pack(
            anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=24, pady=18)
        body.pack(fill="both", expand=True)

        def info_row(r, label, value, value_color=Palette.TEXT):
            tk.Label(body, text=label, bg=Palette.SURFACE,
                     fg=Palette.MUTED, font=base_font()
                     ).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 14))
            tk.Label(body, text=value, bg=Palette.SURFACE,
                     fg=value_color, font=heading_font()
                     ).grid(row=r, column=1, sticky="w", pady=4)

        info_row(0, "Book:",     loan["book_title"])
        info_row(1, "Member:",   loan["member_name"])
        info_row(2, "Current due date:", loan["due_on"] or "—", Palette.PRIMARY)
        renew_color = Palette.SUCCESS if renew_count < max_r else Palette.DANGER
        info_row(3, "Renewals used:", f"{renew_count} / {max_r}", renew_color)

        tk.Frame(body, bg=Palette.BORDER, height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=12)

        tk.Label(body, text="Extend by:", bg=Palette.SURFACE,
                 fg=Palette.TEXT, font=heading_font()
                 ).grid(row=5, column=0, sticky="w", pady=4)

        period = tk.Frame(body, bg=Palette.SURFACE)
        period.grid(row=5, column=1, sticky="w", pady=4)
        self.days_var = tk.StringVar(value="14")
        ttk.Entry(period, textvariable=self.days_var, width=6,
                  font=base_font()).pack(side="left")
        tk.Label(period, text="days", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()).pack(side="left", padx=(6, 0))

        if renew_count >= max_r:
            tk.Label(body, text="⚠  Maximum renewals reached.",
                     bg=Palette.SURFACE, fg=Palette.DANGER, font=heading_font()
                     ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

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

    def _submit(self):
        try:
            days = int(self.days_var.get()) if self.days_var.get().strip() else 14
            if days <= 0:
                raise ValueError("Days must be positive.")
            LoanModel.renew(self.loan_id, extra_days=days)
            self.destroy()
            self.on_success()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)


# --------------------------------------------------------------------------- #
#  Main application window
# --------------------------------------------------------------------------- #
class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📚 GHCC Library Management")
        self.geometry("1180x680")
        self.minsize(960, 560)
        setup_styles(self)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.books_tab   = BooksTab(notebook)
        self.members_tab = MembersTab(notebook)
        self.loans_tab   = LoansTab(notebook, on_change=self.books_tab.refresh)

        notebook.add(self.books_tab,   text="  Books  ")
        notebook.add(self.members_tab, text="  Members  ")
        notebook.add(self.loans_tab,   text="  Loans  ")

        self.status = ttk.Label(self,
                                text=" Ready  •  Library Management System",
                                style="Status.TLabel", anchor="w")
        self.status.pack(fill="x", side="bottom")