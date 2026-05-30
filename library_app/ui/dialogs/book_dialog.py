from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ...services import Services
from ..theme import Palette, base_font, heading_font, small_font
from ..ui_helpers import center_window, make_divider


class BookDialog(tk.Toplevel):
    """Add/edit a book.

    Fields are grouped into sections with visual dividers. Includes inline
    category and language selectors with create-new shortcuts.
    Result available in `self.result`.
    """

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
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.result: dict | None = None
        initial = initial or {}

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        inner_h = ttk.Frame(header, style="Header.TFrame", padding=(22, 14))
        inner_h.pack(fill="x")
        ttk.Label(inner_h, text=title, style="Header.TLabel").pack(anchor="w")
        ttk.Label(inner_h, text="Fill in the details below and click Save",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

        accent = ttk.Frame(self, style="Accent.TFrame", height=4)
        accent.pack(fill="x", side="top")
        accent.pack_propagate(False)

        # ── Buttons (packed before scrollable body so always visible) ────────
        make_divider(self).pack(fill="x", side="bottom")
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=22, pady=14)
        btns.pack(fill="x", side="bottom")
        ttk.Button(btns, text="✓  Save", style="Primary.TButton",
                   command=self._on_ok).pack(side="right")
        ttk.Button(btns, text="Cancel", style="Neutral.TButton",
                   command=self.destroy).pack(side="right", padx=(0, 8))

        # ── Scrollable body canvas ────────────────────────────────────────────
        canvas = tk.Canvas(self, bg=Palette.SURFACE, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=Palette.SURFACE, padx=28, pady=20)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(_e: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(e: tk.Event) -> None:
            canvas.itemconfigure(body_id, width=e.width)

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _scroll(e: tk.Event) -> None:
            # macOS trackpad: delta is in pixels (already scaled), no /120 needed.
            # Windows/Linux mouse wheel: delta is ±120 multiples.
            import sys
            if sys.platform == "darwin":
                canvas.yview_scroll(int(-1 * e.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        def _bind_scroll(widget: tk.Widget) -> None:
            """Recursively bind scroll events to every child so trackpad works
            regardless of which widget the cursor is hovering over."""
            widget.bind("<MouseWheel>", _scroll, add=True)
            widget.bind("<Button-4>",
                        lambda e: canvas.yview_scroll(-1, "units"), add=True)
            widget.bind("<Button-5>",
                        lambda e: canvas.yview_scroll(1, "units"), add=True)
            for child in widget.winfo_children():
                _bind_scroll(child)

        # Bind now and also after the body is fully populated (children exist
        # only after this constructor returns, so schedule a second pass).
        _bind_scroll(canvas)
        _bind_scroll(body)
        self.after(100, lambda: _bind_scroll(body))

        # ── Fields ────────────────────────────────────────────────────────────
        body.columnconfigure(0, weight=1)
        self._entries: dict[str, tk.Entry] = {}
        row = 0

        # ── Section: Book Identity ────────────────────────────────────────────
        tk.Label(body, text="📖  Book Identity", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        for key, label, icon in [
            ("title",  "Title",           "✏️"),
            ("author", "Author",          "👤"),
            ("isbn",   "ISBN  (optional)", "🔢"),
        ]:
            row = self._add_field(body, row, key, f"{icon}  {label}",
                                  initial.get(key))

        # ── Section: Publication ──────────────────────────────────────────────
        tk.Frame(body, bg=Palette.BORDER, height=1).grid(
            row=row, column=0, sticky="ew", pady=(12, 10))
        row += 1
        tk.Label(body, text="📅  Publication", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        row = self._add_field(body, row, "year",
                              "📅  Year  (optional)", initial.get("year"))

        # Copies
        tk.Label(body, text="📦  Total Copies", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=small_font()
                 ).grid(row=row, column=0, sticky="w", pady=(8, 2))
        row += 1
        wrap = tk.Frame(body, bg=Palette.BORDER)
        wrap.grid(row=row, column=0, sticky="w")
        copies_entry = tk.Entry(
            wrap, width=10, font=base_font(), relief="flat", bd=0,
            bg=Palette.SURFACE, fg=Palette.TEXT,
            insertbackground=Palette.PRIMARY,
        )
        copies_entry.pack(padx=1, pady=1, ipady=8, ipadx=10)
        copies_val = initial.get("total_copies")
        copies_entry.insert(0, str(copies_val) if copies_val is not None else "1")
        self._entries["total_copies"] = copies_entry
        self._attach_focus_ring(copies_entry, wrap)
        row += 1

        # ── Section: Classification ───────────────────────────────────────────
        tk.Frame(body, bg=Palette.BORDER, height=1).grid(
            row=row, column=0, sticky="ew", pady=(12, 10))
        row += 1
        tk.Label(body, text="🏷️  Classification", bg=Palette.SURFACE,
                 fg=Palette.PRIMARY, font=heading_font()
                 ).grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        # Category
        tk.Label(body, text="🏷️  Category", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=small_font()
                 ).grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1
        cat_frame = tk.Frame(body, bg=Palette.SURFACE)
        cat_frame.grid(row=row, column=0, sticky="ew")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            cat_frame, textvariable=self.category_var, width=32,
            state="readonly", font=base_font(),
        )
        self._refresh_categories()
        if initial.get("category_id"):
            cat = self._services.categories.get(initial["category_id"])
            if cat:
                self.category_var.set(cat.name)
        self.category_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(cat_frame, text="＋ New", style="Neutral.TButton",
                   command=self._new_category).pack(side="left", padx=(8, 0))
        row += 1

        # Language
        tk.Label(body, text="🌐  Language", bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=small_font()
                 ).grid(row=row, column=0, sticky="w", pady=(10, 2))
        row += 1
        lang_frame = tk.Frame(body, bg=Palette.SURFACE)
        lang_frame.grid(row=row, column=0, sticky="ew")
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            lang_frame, textvariable=self.language_var, width=32,
            state="readonly", font=base_font(),
        )
        self._refresh_languages()
        if initial.get("language_id"):
            lang = self._services.languages.get(initial["language_id"])
            if lang:
                self.language_var.set(lang.name)
        self.language_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(lang_frame, text="＋ New", style="Neutral.TButton",
                   command=self._new_language).pack(side="left", padx=(8, 0))

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        list(self._entries.values())[0].focus_set()

        center_window(self, parent, width=520, height=680)
        self.minsize(440, 500)
        self.wait_window(self)

    # ── Field builder ──────────────────────────────────────────────────────────

    def _add_field(
        self,
        body: tk.Frame,
        row: int,
        key: str,
        label: str,
        value: object,
    ) -> int:
        tk.Label(body, text=label, bg=Palette.SURFACE, fg=Palette.MUTED,
                 font=small_font()
                 ).grid(row=row, column=0, sticky="w",
                        pady=(6 if row > 1 else 0, 2))
        row += 1
        wrap = tk.Frame(body, bg=Palette.BORDER)
        wrap.grid(row=row, column=0, sticky="ew")
        entry = tk.Entry(
            wrap, width=38, font=base_font(), relief="flat", bd=0,
            bg=Palette.SURFACE, fg=Palette.TEXT,
            insertbackground=Palette.PRIMARY,
        )
        entry.pack(fill="x", padx=1, pady=1, ipady=8, ipadx=10)
        if value is not None:
            entry.insert(0, str(value))
        self._entries[key] = entry
        self._attach_focus_ring(entry, wrap)
        return row + 1

    @staticmethod
    def _attach_focus_ring(entry: tk.Entry, wrap: tk.Frame) -> None:
        entry.bind("<FocusIn>",  lambda e: wrap.configure(bg=Palette.BORDER_FOCUS))
        entry.bind("<FocusOut>", lambda e: wrap.configure(bg=Palette.BORDER))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _refresh_categories(self) -> None:
        names = [c.name for c in self._services.categories.list_all()]
        self.category_combo["values"] = [""] + names

    def _refresh_languages(self) -> None:
        names = [l.name for l in self._services.languages.list_all()]
        self.language_combo["values"] = [""] + names

    def _new_category(self) -> None:
        name = simpledialog.askstring("New Category", "Category name:",
                                      parent=self)
        if not name:
            return
        try:
            self._services.categories.add(name)
            self._refresh_categories()
            self.category_var.set(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _new_language(self) -> None:
        name = simpledialog.askstring("New Language", "Language name:",
                                      parent=self)
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
