from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ...services import Services
from ..theme import Palette, base_font, heading_font


class BookDialog(tk.Toplevel):
    """Add/edit a book. Includes category and language selectors with inline
    create-new shortcuts. Result available in `self.result`."""

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        title: str,
        initial: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self.title(title)
        self.configure(bg=Palette.SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: dict | None = None
        initial = initial or {}

        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Header.TLabel").pack(
            anchor="w", padx=20, pady=14)

        body = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        self._entries: dict[str, ttk.Entry] = {}
        fields = [
            ("title", "Title"),
            ("author", "Author"),
            ("isbn", "ISBN (optional)"),
            ("year", "Year (optional)"),
            ("total_copies", "Total Copies"),
        ]
        for i, (key, label) in enumerate(fields):
            tk.Label(body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                     font=base_font()).grid(row=i, column=0, sticky="w",
                                            pady=(6, 2))
            entry = ttk.Entry(body, width=38, font=base_font())
            entry.grid(row=i, column=1, pady=(6, 2), padx=(12, 0), sticky="ew")
            if key in initial and initial[key] is not None:
                entry.insert(0, str(initial[key]))
            self._entries[key] = entry

        # Category selector
        tk.Label(body, text="Category", bg=Palette.SURFACE, fg=Palette.MUTED,
                 font=base_font()).grid(row=len(fields), column=0, sticky="w",
                                        pady=(6, 2))
        cat_frame = tk.Frame(body, bg=Palette.SURFACE)
        cat_frame.grid(row=len(fields), column=1, pady=(6, 2), padx=(12, 0),
                       sticky="ew")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            cat_frame, textvariable=self.category_var, width=35,
            state="readonly"
        )
        self._refresh_categories()
        if initial.get("category_id"):
            cat = self._services.categories.get(initial["category_id"])
            if cat:
                self.category_var.set(cat.name)
        self.category_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(cat_frame, text="+ New", style="Neutral.TButton",
                   command=self._new_category).pack(side="left", padx=(6, 0))

        # Language selector
        tk.Label(body, text="Language", bg=Palette.SURFACE, fg=Palette.MUTED,
                 font=base_font()).grid(row=len(fields) + 1, column=0,
                                        sticky="w", pady=(6, 2))
        lang_frame = tk.Frame(body, bg=Palette.SURFACE)
        lang_frame.grid(row=len(fields) + 1, column=1, pady=(6, 2),
                        padx=(12, 0), sticky="ew")
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            lang_frame, textvariable=self.language_var, width=35,
            state="readonly"
        )
        self._refresh_languages()
        if initial.get("language_id"):
            lang = self._services.languages.get(initial["language_id"])
            if lang:
                self.language_var.set(lang.name)
        self.language_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(lang_frame, text="+ New", style="Neutral.TButton",
                   command=self._new_language).pack(side="left", padx=(6, 0))

        # Buttons
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
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.wait_window(self)

    def _refresh_categories(self) -> None:
        names = [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = [""] + names

    def _refresh_languages(self) -> None:
        names = [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = [""] + names

    def _new_category(self) -> None:
        name = simpledialog.askstring("New Category", "Category name:", parent=self)
        if not name:
            return
        try:
            self._services.categories.add(name)
            self._refresh_categories()
            self.category_var.set(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _new_language(self) -> None:
        name = simpledialog.askstring("New Language", "Language name:", parent=self)
        if not name:
            return
        try:
            self._services.languages.add(name)
            self._refresh_languages()
            self.language_var.set(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _resolve_id(self, name: str, items) -> int | None:
        if not name:
            return None
        for item in items:
            if item.name == name:
                return item.id
        return None

    def _on_ok(self) -> None:
        data = {k: e.get().strip() for k, e in self._entries.items()}
        data["category_id"] = self._resolve_id(
            self.category_var.get().strip(),
            self._services.categories.list_all(),
        )
        data["language_id"] = self._resolve_id(
            self.language_var.get().strip(),
            self._services.languages.list_all(),
        )
        self.result = data
        self.destroy()
