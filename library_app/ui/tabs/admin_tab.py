from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from ...exceptions import LibraryError
from ...services import Services
from ..dialogs import BookDialog
from ..theme import Palette, base_font, heading_font
from ..widgets import FormDialog, ScrollableFrame, TabHeader, build_treeview
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
        sub.pack(fill="both", expand=True, padx=8, pady=8)
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
        # The three sections (Books + Categories + Languages) stacked together
        # are taller than a short / not-maximized window. Sharing the space via
        # grid row-weights made every list shrink — on a small Windows screen
        # the treeviews collapsed to a single visible row. Instead, host the
        # whole panel in a ScrollableFrame and give each list a generous FIXED
        # height: nothing shrinks, and the outer scrollbar appears only when the
        # panel doesn't fit. (Same approach as the Dashboard.)
        scroller = ScrollableFrame(parent)
        scroller.pack(fill="both", expand=True)
        main = tk.Frame(scroller.body, bg=Palette.BG, padx=8, pady=6)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)

        # Books section
        bf = tk.LabelFrame(main, text="📚 Books", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=6)
        bf.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

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

        # "extended" selection so several books can be selected (Ctrl/Shift-
        # click) and deleted in one go.
        container, self.books_tree = build_treeview(bf, [
            ("id",       "ID",        60, "center"),
            ("title",    "Title",    175, "w"),
            ("author",   "Author",   120, "w"),
            ("category", "Category",  95, "w"),
            ("language", "Language",  95, "w"),
            ("copies",   "Copies",    80, "center"),
        ], height=12, selectmode="extended")

        # Action row pinned to the BOTTOM — packed before the tree so it is
        # always reserved and never clipped when the window is short. The
        # tree then absorbs the shrink and scrolls within its own scrollbar.
        btn_row = tk.Frame(bf, bg=Palette.BG)
        btn_row.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(btn_row, text="➕ Add Book", style="Success.TButton",
                   command=self._add_book).pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="📥 Import", style="Primary.TButton",
                   command=self._import_books).pack(side="left", padx=4)
        ttk.Button(btn_row, text="✏ Edit", style="Primary.TButton",
                   command=self._edit_book).pack(side="left", padx=4)
        ttk.Button(btn_row, text="📦 Copies…", style="Neutral.TButton",
                   command=self._manage_copies).pack(side="left", padx=4)
        ttk.Button(btn_row, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_book).pack(side="left", padx=4)

        container.pack(fill="both", expand=True)
        self.books_tree.bind("<Double-1>", lambda e: self._edit_book())

        # Authors, Categories & Languages side by side — grid so columns share
        # width and the single row stretches with the parent (rowconfigure
        # weight 1 ensures the LabelFrames take all available vertical space).
        meta = tk.Frame(main, bg=Palette.BG)
        meta.grid(row=1, column=0, sticky="nsew")
        meta.columnconfigure(0, weight=1)
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(2, weight=1)
        meta.rowconfigure(0, weight=1)

        # Categories
        cf = tk.LabelFrame(meta, text="🏷️ Categories", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=6)
        cf.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

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
        ], height=8)

        # Input row reserved at the bottom (packed before the tree).
        ci = tk.Frame(cf, bg=Palette.BG)
        ci.pack(side="bottom", fill="x", pady=(8, 0))
        self.cat_entry = ttk.Entry(ci, font=base_font())
        self.cat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(ci, text="➕ Add", style="Success.TButton",
                   command=self._add_category).pack(side="left", padx=(0, 4))
        ttk.Button(ci, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_category).pack(side="left")

        container.pack(fill="both", expand=True)

        # Languages
        lf = tk.LabelFrame(meta, text="🌐 Languages", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=6)
        lf.grid(row=0, column=1, sticky="nsew", padx=(5, 5))

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
        ], height=8)

        # Input row reserved at the bottom (packed before the tree).
        li = tk.Frame(lf, bg=Palette.BG)
        li.pack(side="bottom", fill="x", pady=(8, 0))
        self.lang_entry = ttk.Entry(li, font=base_font())
        self.lang_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(li, text="➕ Add", style="Success.TButton",
                   command=self._add_language).pack(side="left", padx=(0, 4))
        ttk.Button(li, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_language).pack(side="left")

        container.pack(fill="both", expand=True)

        # Authors
        af = tk.LabelFrame(meta, text="👤 Authors", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=6)
        af.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        author_search = tk.Frame(af, bg=Palette.BG)
        author_search.pack(fill="x", pady=(0, 6))
        tk.Label(author_search, text="🔎", bg=Palette.BG, fg=Palette.TEXT,
                 font=base_font()).pack(side="left", padx=(0, 4))
        self.author_search_var = tk.StringVar()
        self.author_search_var.trace_add(
            "write", lambda *_: self._refresh_authors_table()
        )
        ttk.Entry(author_search, textvariable=self.author_search_var,
                  font=base_font()).pack(side="left", fill="x", expand=True)

        container, self.author_tree = build_treeview(af, [
            ("id", "ID", 40, "center"),
            ("name", "Name", 150, "w"),
        ], height=8)

        # Input row reserved at the bottom (packed before the tree).
        ai = tk.Frame(af, bg=Palette.BG)
        ai.pack(side="bottom", fill="x", pady=(8, 0))
        self.author_entry = ttk.Entry(ai, font=base_font())
        self.author_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(ai, text="➕ Add", style="Success.TButton",
                   command=self._add_author).pack(side="left", padx=(0, 4))
        ttk.Button(ai, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_author).pack(side="left")

        container.pack(fill="both", expand=True)

    def _build_members_management(self, parent: tk.Widget) -> None:
        main = tk.Frame(parent, bg=Palette.BG, padx=8, pady=6)
        main.pack(fill="both", expand=True)

        mf = tk.LabelFrame(main, text="👥 Members", bg=Palette.BG,
                           fg=Palette.TEXT, font=heading_font(),
                           padx=8, pady=6)
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

        # "extended" selection so several members can be selected (Ctrl/Shift-
        # click) and deleted in one go.
        container, self.members_tree = build_treeview(mf, [
            ("id", "ID", 60, "center"),
            ("name", "Name", 200, "w"),
            ("email", "Email", 220, "w"),
            ("phone", "Phone", 130, "center"),
            ("joined", "Joined", 110, "center"),
        ], height=8, selectmode="extended")

        # Action row reserved at the bottom (packed before the tree).
        br = tk.Frame(mf, bg=Palette.BG)
        br.pack(side="bottom", fill="x", pady=(8, 0))
        ttk.Button(br, text="➕ Add Member", style="Success.TButton",
                   command=self._add_member).pack(side="left", padx=(0, 4))
        ttk.Button(br, text="📥 Import", style="Primary.TButton",
                   command=self._import_members).pack(side="left", padx=4)
        ttk.Button(br, text="✏ Edit", style="Primary.TButton",
                   command=self._edit_member).pack(side="left", padx=4)
        ttk.Button(br, text="🗑 Delete", style="Danger.TButton",
                   command=self._delete_member).pack(side="left", padx=4)

        container.pack(fill="both", expand=True)
        self.members_tree.bind("<Double-1>", lambda e: self._edit_member())

    # -------------------------------------------------------------- actions #

    def _add_book(self) -> None:
        dlg = BookDialog(self.winfo_toplevel(), self._services, "Add Book")
        if not dlg.result:
            return
        d = dlg.result
        try:
            year = int(d["year"]) if d["year"] else None
            total = int(d["total_copies"]) if d["total_copies"] else 1
            book_id, merged = self._services.books.add_or_merge(
                d["title"], d["author_id"], d["isbn"] or None, year,
                d["category_id"], d["language_id"], total,
            )
            self.refresh()
            self.on_change()
            if merged:
                book = self._services.books.get(book_id)
                copies_word = "copy" if total == 1 else "copies"
                messagebox.showinfo(
                    "Added as copies",
                    f"A book titled “{book.title}” with the same author and "
                    f"language already exists.\n\nAdded {total} {copies_word} "
                    f"to it — it now has {book.total_copies} total."
                )
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e))

    def _edit_book(self) -> None:
        sel = self.books_tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("Select one book",
                                "Please select a single book to edit.")
            return
        book_id = int(self.books_tree.item(sel[0])["values"][0])
        book = self._services.books.get(book_id)
        if book is None:
            return
        initial = {
            "title": book.title, "author_id": book.author_id,
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
                book_id, d["title"], d["author_id"], d["isbn"] or None, year,
                d["category_id"], d["language_id"], total,
            )
            self.refresh()
            self.on_change()
        except (LibraryError, ValueError) as e:
            messagebox.showerror("Error", str(e))

    def _delete_book(self) -> None:
        sel = self.books_tree.selection()
        if not sel:
            messagebox.showinfo("Select a book",
                                "Please select one or more books first.")
            return

        # (id, title) for each selected row.
        books = [
            (int(self.books_tree.item(s)["values"][0]),
             str(self.books_tree.item(s)["values"][1]))
            for s in sel
        ]

        if len(books) == 1:
            prompt = f"Delete '{books[0][1]}'?"
        else:
            preview = "\n".join(f"  • {title}" for _, title in books[:10])
            if len(books) > 10:
                preview += f"\n  …and {len(books) - 10} more"
            prompt = (f"Delete these {len(books)} books?\n\n{preview}\n\n"
                      "This cannot be undone.")
        if not messagebox.askyesno("Confirm delete", prompt):
            return

        # Delete each independently so one blocked book (active loans) doesn't
        # abort the whole batch; collect failures and report them together.
        deleted = 0
        failures: list[tuple[str, str]] = []
        for book_id, title in books:
            try:
                self._services.books.delete(book_id)
                deleted += 1
            except LibraryError as e:
                failures.append((title, str(e)))

        self.refresh()
        self.on_change()

        if failures:
            lines: list[str] = []
            if deleted:
                lines.append(f"Deleted {deleted} book(s).")
            lines.append(f"{len(failures)} could not be deleted:")
            lines.extend(f"  • {title}: {msg}" for title, msg in failures[:10])
            if len(failures) > 10:
                lines.append(f"  …and {len(failures) - 10} more.")
            messagebox.showwarning("Some books not deleted", "\n".join(lines))

    def _import_books(self) -> None:
        """Open the bulk-import dialog (Excel/CSV → books)."""
        from ..dialogs import ImportBooksDialog
        ImportBooksDialog(
            self.winfo_toplevel(), self._services,
            on_success=lambda: (self.refresh(), self.on_change()),
        )

    def _import_members(self) -> None:
        """Open the bulk-import dialog (Excel/CSV → members)."""
        from ..dialogs import ImportMembersDialog
        ImportMembersDialog(
            self.winfo_toplevel(), self._services,
            on_success=lambda: (self.refresh(), self.on_change()),
        )

    def _manage_copies(self) -> None:
        """Open the per-copy serial editor for the selected book."""
        sel = self.books_tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("Select one book",
                                "Please select a single book to manage copies.")
            return
        book_id = int(self.books_tree.item(sel[0])["values"][0])
        from ..dialogs import ManageCopiesDialog
        ManageCopiesDialog(self.winfo_toplevel(), self._services, book_id)
        # Renames change visible state in Books tab; cascade refresh.
        self.refresh()
        self.on_change()

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

    def _add_author(self) -> None:
        name = self.author_entry.get().strip()
        try:
            self._services.authors.add(name)
            self.author_entry.delete(0, "end")
            self.refresh()
            self.on_change()
        except LibraryError as e:
            messagebox.showerror("Error", str(e))

    def _delete_author(self) -> None:
        sel = self.author_tree.selection()
        if not sel:
            messagebox.showinfo("Select an author",
                                "Please select an author first.")
            return
        author_id = int(self.author_tree.item(sel[0])["values"][0])
        author = self._services.authors.get(author_id)
        if author is None:
            return
        if not messagebox.askyesno(
            "Confirm",
            f"Delete author '{author.name}'?\n\n"
            "Books by this author will have no author set."
        ):
            return
        self._services.authors.delete(author_id)
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
        if len(sel) != 1:
            messagebox.showinfo("Select one member",
                                "Please select a single member to edit.")
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
                                "Please select one or more members first.")
            return

        # (id, name) for each selected row.
        members = [
            (int(self.members_tree.item(s)["values"][0]),
             str(self.members_tree.item(s)["values"][1]))
            for s in sel
        ]

        if len(members) == 1:
            prompt = f"Delete '{members[0][1]}'?"
        else:
            preview = "\n".join(f"  • {name}" for _, name in members[:10])
            if len(members) > 10:
                preview += f"\n  …and {len(members) - 10} more"
            prompt = (f"Delete these {len(members)} members?\n\n{preview}\n\n"
                      "This cannot be undone.")
        if not messagebox.askyesno("Confirm delete", prompt):
            return

        # Delete each independently so one blocked member (active loans)
        # doesn't abort the batch; collect failures and report them together.
        deleted = 0
        failures: list[tuple[str, str]] = []
        for member_id, name in members:
            try:
                self._services.members.delete(member_id)
                deleted += 1
            except LibraryError as e:
                failures.append((name, str(e)))

        self._refresh_members()
        self.on_change()

        if failures:
            lines: list[str] = []
            if deleted:
                lines.append(f"Deleted {deleted} member(s).")
            lines.append(f"{len(failures)} could not be deleted:")
            lines.extend(f"  • {name}: {msg}" for name, msg in failures[:10])
            if len(failures) > 10:
                lines.append(f"  …and {len(failures) - 10} more.")
            messagebox.showwarning("Some members not deleted", "\n".join(lines))

    # --------------------------------------------------------------- refresh #
    # Per-section refreshes: each search bar updates only its own tree so
    # typing doesn't re-render unrelated sections. The master `refresh()` is
    # used on init and on cross-section actions (add/delete).

    def _refresh_books_table(self) -> None:
        for r in self.books_tree.get_children():
            self.books_tree.delete(r)
        search = self.book_search_var.get() if hasattr(self, "book_search_var") else ""
        # Admin management table is always ordered by ID (the service query
        # sorts by title for the browse view; here we want stable ID order).
        books = sorted(self._services.books.list_with_details(search=search),
                       key=lambda b: b.id)
        for i, b in enumerate(books):
            tag = "even" if i % 2 else "odd"
            self.books_tree.insert(
                "", "end",
                values=(b.id, b.title, b.author_name or "—",
                        b.category_name or "—", b.language_name or "—",
                        f"{b.available_copies}/{b.total_copies}"),
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

    def _refresh_authors_table(self) -> None:
        for r in self.author_tree.get_children():
            self.author_tree.delete(r)
        search = self.author_search_var.get() if hasattr(self, "author_search_var") else ""
        for i, a in enumerate(self._services.authors.list_all(search=search)):
            tag = "even" if i % 2 else "odd"
            self.author_tree.insert("", "end", values=(a.id, a.name), tags=(tag,))

    def _refresh_members(self) -> None:
        for r in self.members_tree.get_children():
            self.members_tree.delete(r)
        search = self.member_search_var.get() if hasattr(self, "member_search_var") else ""
        # Always ordered by ID in the admin management table.
        members = sorted(self._services.members.list_all(search),
                         key=lambda m: m.id)
        for i, m in enumerate(members):
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
        self._refresh_authors_table()
        self._refresh_members()
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
