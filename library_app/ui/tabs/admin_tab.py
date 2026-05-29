from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ...exceptions import LibraryError
from ...services import Services
from ..dialogs import BookDialog
from ..theme import Palette, base_font, heading_font
from ..widgets import FormDialog, TabHeader, build_treeview
from ._dashboard_view import DashboardView


class AdminTab(ttk.Frame):
    """Management interface: books, categories, languages, and members.

    Organized into two sub-tabs to keep the surface area manageable.
    Fires `on_change` after every mutation so other tabs can refresh.
    """

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self.on_change = on_change or (lambda: None)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ ui  #

    def _build_ui(self) -> None:
        TabHeader(self, "⚙️", "Admin Panel",
                  "Manage books, members, categories, and languages"
                  ).pack(fill="x")

        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True, padx=14, pady=14)
        self._sub_notebook = sub

        # Dashboard is first so admins see the headline metrics on entry.
        self.dashboard = DashboardView(sub, self._services)
        sub.add(self.dashboard, text="  📊 Dashboard  ")

        books_mgmt = ttk.Frame(sub)
        sub.add(books_mgmt, text="  📚 Manage Books  ")
        self._build_books_management(books_mgmt)

        members_mgmt = ttk.Frame(sub)
        sub.add(members_mgmt, text="  👥 Manage Members  ")
        self._build_members_management(members_mgmt)

        # Refresh whichever sub-tab the admin switches to — the dashboard's
        # numbers can change every time a loan or book is touched.
        sub.bind("<<NotebookTabChanged>>", self._on_sub_tab_changed)

    def _build_books_management(self, parent: tk.Widget) -> None:
        # Grid layout with explicit row weights — gives the Books section
        # roughly 60% of vertical space and Categories/Languages 40%.
        # Pack with `expand=True` on both was distributing space based on
        # natural requested size, which pushed the bottom input rows below
        # the visible window once the lists grew.
        main = tk.Frame(parent, bg=Palette.BG, padx=10, pady=10)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=3)  # Books gets 3 parts
        main.rowconfigure(1, weight=2)  # Cats + Langs get 2 parts

        # Books section
        bf = tk.LabelFrame(main, text="📚 Books", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=10, pady=10)
        bf.grid(row=0, column=0, sticky="nsew", pady=(0, 14))

        # Search bar (live filter — typing immediately filters the table).
        # Backed by `BookService.list_with_details(search=...)` so the filter
        # runs in SQL, not in Python — scales as the catalogue grows.
        sr = tk.Frame(bf, bg=Palette.BG)
        sr.pack(fill="x", pady=(0, 8))
        tk.Label(sr, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=(base_font()[0], base_font()[1] + 2)
                 ).pack(side="left", padx=(0, 4))
        self.book_search_var = tk.StringVar()
        self.book_search_var.trace_add(
            "write", lambda *_: self._refresh_books_table()
        )
        ttk.Entry(sr, textvariable=self.book_search_var, width=32,
                  font=base_font()).pack(side="left")

        # Cap the visible rows so the Add/Edit/Delete row below the tree
        # always stays on-screen even on smaller window heights.
        container, self.books_tree = build_treeview(bf, [
            ("id", "ID", 60, "center"),
            ("title", "Title", 180, "w"),
            ("author", "Author", 120, "w"),
            ("category", "Category", 100, "w"),
            ("language", "Language", 100, "w"),
        ], height=8)
        container.pack(fill="both", expand=True, pady=(0, 10))

        btn_row = tk.Frame(bf, bg=Palette.BG)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="➕ Add Book", style="Success.TButton",
                   command=self._add_book).pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="✏ Edit", style="Primary.TButton",
                   command=self._edit_book).pack(side="left", padx=4)
        ttk.Button(btn_row, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_book).pack(side="left", padx=4)
        self.books_tree.bind("<Double-1>", lambda e: self._edit_book())

        # Categories & Languages side by side — grid so columns share width
        # and the single row stretches with the parent (rowconfigure weight 1
        # ensures the LabelFrames take all available vertical space).
        meta = tk.Frame(main, bg=Palette.BG)
        meta.grid(row=1, column=0, sticky="nsew")
        meta.columnconfigure(0, weight=1)
        meta.columnconfigure(1, weight=1)
        meta.rowconfigure(0, weight=1)

        # Categories
        cf = tk.LabelFrame(meta, text="🏷️ Categories", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=10, pady=10)
        cf.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        cat_search = tk.Frame(cf, bg=Palette.BG)
        cat_search.pack(fill="x", pady=(0, 6))
        tk.Label(cat_search, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=base_font()).pack(side="left", padx=(0, 4))
        self.cat_search_var = tk.StringVar()
        self.cat_search_var.trace_add(
            "write", lambda *_: self._refresh_categories_table()
        )
        ttk.Entry(cat_search, textvariable=self.cat_search_var,
                  font=base_font()).pack(side="left", fill="x", expand=True)

        container, self.cat_tree = build_treeview(cf, [
            ("id", "ID", 40, "center"),
            ("name", "Name", 150, "w"),
        ], height=5)
        container.pack(fill="both", expand=True, pady=(0, 10))

        ci = tk.Frame(cf, bg=Palette.BG)
        ci.pack(fill="x", pady=(0, 8))
        self.cat_entry = ttk.Entry(ci, font=base_font())
        self.cat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(ci, text="➕ Add", style="Success.TButton",
                   command=self._add_category).pack(side="left", padx=(0, 4))
        ttk.Button(ci, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_category).pack(side="left")

        # Languages
        lf = tk.LabelFrame(meta, text="🌐 Languages", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=10, pady=10)
        lf.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        lang_search = tk.Frame(lf, bg=Palette.BG)
        lang_search.pack(fill="x", pady=(0, 6))
        tk.Label(lang_search, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=base_font()).pack(side="left", padx=(0, 4))
        self.lang_search_var = tk.StringVar()
        self.lang_search_var.trace_add(
            "write", lambda *_: self._refresh_languages_table()
        )
        ttk.Entry(lang_search, textvariable=self.lang_search_var,
                  font=base_font()).pack(side="left", fill="x", expand=True)

        container, self.lang_tree = build_treeview(lf, [
            ("id", "ID", 40, "center"),
            ("name", "Name", 150, "w"),
        ], height=5)
        container.pack(fill="both", expand=True, pady=(0, 10))

        li = tk.Frame(lf, bg=Palette.BG)
        li.pack(fill="x", pady=(0, 8))
        self.lang_entry = ttk.Entry(li, font=base_font())
        self.lang_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(li, text="➕ Add", style="Success.TButton",
                   command=self._add_language).pack(side="left", padx=(0, 4))
        ttk.Button(li, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_language).pack(side="left")

    def _build_members_management(self, parent: tk.Widget) -> None:
        main = tk.Frame(parent, bg=Palette.BG, padx=10, pady=10)
        main.pack(fill="both", expand=True)

        mf = tk.LabelFrame(main, text="👥 Members", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=10, pady=10)
        mf.pack(fill="both", expand=True)

        sr = tk.Frame(mf, bg=Palette.BG)
        sr.pack(fill="x", pady=(0, 10))
        tk.Label(sr, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=(base_font()[0], base_font()[1] + 2)
                 ).pack(side="left", padx=(0, 4))
        self.member_search_var = tk.StringVar()
        self.member_search_var.trace_add(
            "write", lambda *_: self._refresh_members()
        )
        ttk.Entry(sr, textvariable=self.member_search_var, width=30,
                  font=base_font()).pack(side="left")

        container, self.members_tree = build_treeview(mf, [
            ("id", "ID", 60, "center"),
            ("name", "Name", 200, "w"),
            ("email", "Email", 220, "w"),
            ("phone", "Phone", 130, "center"),
            ("joined", "Joined", 110, "center"),
        ])
        container.pack(fill="both", expand=True, pady=(0, 10))
        self.members_tree.bind("<Double-1>", lambda e: self._edit_member())

        br = tk.Frame(mf, bg=Palette.BG)
        br.pack(fill="x")
        ttk.Button(br, text="➕ Add Member", style="Success.TButton",
                   command=self._add_member).pack(side="left", padx=(0, 4))
        ttk.Button(br, text="✏ Edit", style="Primary.TButton",
                   command=self._edit_member).pack(side="left", padx=4)
        ttk.Button(br, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_member).pack(side="left", padx=4)

    # -------------------------------------------------------------- actions #

    def _add_book(self) -> None:
        dlg = BookDialog(self.winfo_toplevel(), self._services, "Add Book")
        if not dlg.result:
            return
        d = dlg.result
        try:
            year = int(d["year"]) if d["year"] else None
            total = int(d["total_copies"]) if d["total_copies"] else 1
            self._services.books.add(
                d["title"], d["author"], d["isbn"] or None, year,
                d["category_id"], d["language_id"], total,
            )
            self.refresh()
            self.on_change()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e))

    def _edit_book(self) -> None:
        sel = self.books_tree.selection()
        if not sel:
            messagebox.showinfo("Select a book", "Please select a book first.")
            return
        book_id = int(self.books_tree.item(sel[0])["values"][0])
        book = self._services.books.get(book_id)
        if book is None:
            return
        initial = {
            "title": book.title, "author": book.author,
            "isbn": book.isbn, "year": book.year,
            "total_copies": book.total_copies,
            "category_id": book.category_id,
            "language_id": book.language_id,
        }
        dlg = BookDialog(self.winfo_toplevel(), self._services, "Edit Book",
                         initial=initial)
        if not dlg.result:
            return
        d = dlg.result
        try:
            year = int(d["year"]) if d["year"] else None
            total = int(d["total_copies"]) if d["total_copies"] else 1
            self._services.books.update(
                book_id, d["title"], d["author"], d["isbn"] or None, year,
                d["category_id"], d["language_id"], total,
            )
            self.refresh()
            self.on_change()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e))

    def _delete_book(self) -> None:
        sel = self.books_tree.selection()
        if not sel:
            messagebox.showinfo("Select a book", "Please select a book first.")
            return
        book_id = int(self.books_tree.item(sel[0])["values"][0])
        book = self._services.books.get(book_id)
        if book is None:
            return
        if not messagebox.askyesno("Confirm", f"Delete '{book.title}'?"):
            return
        try:
            self._services.books.delete(book_id)
            self.refresh()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Cannot delete", str(e))

    def _add_category(self) -> None:
        name = self.cat_entry.get().strip()
        try:
            self._services.categories.add(name)
            self.cat_entry.delete(0, "end")
            self.refresh()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def _delete_category(self) -> None:
        sel = self.cat_tree.selection()
        if not sel:
            messagebox.showinfo("Select a category",
                                "Please select a category first.")
            return
        cat_id = int(self.cat_tree.item(sel[0])["values"][0])
        cat = self._services.categories.get(cat_id)
        if cat is None:
            return
        if not messagebox.askyesno(
            "Confirm",
            f"Delete category '{cat.name}'?\n\n"
            "Books in this category will become uncategorized."
        ):
            return
        self._services.categories.delete(cat_id)
        self.refresh()
        self.on_change()

    def _add_language(self) -> None:
        name = self.lang_entry.get().strip()
        try:
            self._services.languages.add(name)
            self.lang_entry.delete(0, "end")
            self.refresh()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def _delete_language(self) -> None:
        sel = self.lang_tree.selection()
        if not sel:
            messagebox.showinfo("Select a language",
                                "Please select a language first.")
            return
        lang_id = int(self.lang_tree.item(sel[0])["values"][0])
        lang = self._services.languages.get(lang_id)
        if lang is None:
            return
        if not messagebox.askyesno(
            "Confirm",
            f"Delete language '{lang.name}'?\n\n"
            "Books in this language will become unassigned."
        ):
            return
        self._services.languages.delete(lang_id)
        self.refresh()
        self.on_change()

    def _add_member(self) -> None:
        dlg = FormDialog(self.winfo_toplevel(), "Add Member", [
            ("name", "Name"),
            ("email", "Email (optional)"),
            ("phone", "Phone (optional)"),
        ])
        if not dlg.result:
            return
        d = dlg.result
        try:
            self._services.members.add(d["name"], d["email"], d["phone"])
            self._refresh_members()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def _edit_member(self) -> None:
        sel = self.members_tree.selection()
        if not sel:
            messagebox.showinfo("Select a member",
                                "Please select a member first.")
            return
        mid = int(self.members_tree.item(sel[0])["values"][0])
        m = self._services.members.get(mid)
        if m is None:
            return
        dlg = FormDialog(self.winfo_toplevel(), "Edit Member", [
            ("name", "Name"),
            ("email", "Email (optional)"),
            ("phone", "Phone (optional)"),
        ], initial={"name": m.name, "email": m.email, "phone": m.phone})
        if not dlg.result:
            return
        d = dlg.result
        try:
            self._services.members.update(mid, d["name"], d["email"], d["phone"])
            self._refresh_members()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def _delete_member(self) -> None:
        sel = self.members_tree.selection()
        if not sel:
            messagebox.showinfo("Select a member",
                                "Please select a member first.")
            return
        mid = int(self.members_tree.item(sel[0])["values"][0])
        if not messagebox.askyesno("Confirm", "Delete this member?"):
            return
        try:
            self._services.members.delete(mid)
            self._refresh_members()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Cannot delete", str(e))

    # --------------------------------------------------------------- refresh #
    # Per-section refreshes: each search bar updates only its own tree so
    # typing doesn't re-render unrelated sections. The master `refresh()` is
    # used on init and on cross-section actions (add/delete).

    def _refresh_books_table(self) -> None:
        for r in self.books_tree.get_children():
            self.books_tree.delete(r)
        search = self.book_search_var.get() if hasattr(self, "book_search_var") else ""
        for i, b in enumerate(self._services.books.list_with_details(search=search)):
            tag = "even" if i % 2 else "odd"
            self.books_tree.insert(
                "", "end",
                values=(b.id, b.title, b.author,
                        b.category_name or "—", b.language_name or "—"),
                tags=(tag,),
            )

    def _refresh_categories_table(self) -> None:
        for r in self.cat_tree.get_children():
            self.cat_tree.delete(r)
        search = self.cat_search_var.get() if hasattr(self, "cat_search_var") else ""
        for i, c in enumerate(self._services.categories.list_all(search=search)):
            tag = "even" if i % 2 else "odd"
            self.cat_tree.insert("", "end", values=(c.id, c.name), tags=(tag,))

    def _refresh_languages_table(self) -> None:
        for r in self.lang_tree.get_children():
            self.lang_tree.delete(r)
        search = self.lang_search_var.get() if hasattr(self, "lang_search_var") else ""
        for i, l in enumerate(self._services.languages.list_all(search=search)):
            tag = "even" if i % 2 else "odd"
            self.lang_tree.insert("", "end", values=(l.id, l.name), tags=(tag,))

    def _refresh_members(self) -> None:
        for r in self.members_tree.get_children():
            self.members_tree.delete(r)
        search = self.member_search_var.get() if hasattr(self, "member_search_var") else ""
        for i, m in enumerate(self._services.members.list_all(search)):
            tag = "even" if i % 2 else "odd"
            self.members_tree.insert(
                "", "end",
                values=(m.id, m.name, m.email or "—",
                        m.phone or "—", m.joined),
                tags=(tag,),
            )

    def _on_sub_tab_changed(self, _event: tk.Event) -> None:
        """Refresh the now-visible admin sub-tab so its data is current."""
        try:
            current = self._sub_notebook.nametowidget(self._sub_notebook.select())
        except (tk.TclError, KeyError):
            return
        if current is self.dashboard:
            self.dashboard.refresh()

    def refresh(self) -> None:
        """Refresh every section. Called on init and after mutations that
        touch multiple sections (e.g., deleting a category nulls book FKs)."""
        self._refresh_books_table()
        self._refresh_categories_table()
        self._refresh_languages_table()
        self._refresh_members()
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
