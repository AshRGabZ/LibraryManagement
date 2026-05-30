"""Preview + download dialog for a single book label.

The actual image generation is in `LabelService` — this dialog is a thin
visual wrapper that converts the Pillow Image to a PhotoImage Tk can render
and offers Save-as. Keeps Tk concerns and PIL concerns apart.
"""
from __future__ import annotations

import logging
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ...services import Services
from ..theme import Palette, base_font, heading_font


_log = logging.getLogger(__name__)


class LabelPreviewDialog(tk.Toplevel):
    """Modal label preview with Download. Pillow is required at this seam;
    if it's not installed, we surface a friendly error and bail."""

    # Display preview at half DPI so the dialog fits comfortably on small
    # screens but the underlying image keeps its full print resolution.
    _PREVIEW_DPI = 150

    def __init__(
        self,
        parent: tk.Widget,
        services: Services,
        *,
        serial_number: str,
        category_name: str | None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._serial = serial_number
        self._category = category_name

        self.title(f"Label — {serial_number}")
        self.configure(bg=Palette.SURFACE)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # Render the full-DPI image once — Download uses this directly so
        # there's no resolution loss between preview and saved file.
        try:
            self._image = services.label.render(serial_number, category_name)
        except ImportError as e:
            messagebox.showerror(
                "Pillow not installed",
                f"{e}\n\nRun: pip install pillow",
                parent=parent,
            )
            self.destroy()
            return

        self._build_ui()

        self.geometry("760x540")
        self.minsize(620, 480)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 760) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 540) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window(self)

    # ------------------------------------------------------------------ UI #

    def _build_ui(self) -> None:
        # ---- Header bar
        header = ttk.Frame(self, style="Header.TFrame")
        header.pack(fill="x", side="top")
        ttk.Label(
            header, text="🏷️  Label Preview",
            style="Header.TLabel",
        ).pack(anchor="w", padx=20, pady=14)

        # ---- Buttons — packed BEFORE body so they're always visible
        # regardless of how tall the preview image is.
        btns = tk.Frame(self, bg=Palette.SURFACE, padx=20, pady=14)
        btns.pack(fill="x", side="bottom")
        ttk.Button(btns, text="💾 Download", style="Primary.TButton",
                   command=self._download).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Close", style="Neutral.TButton",
                   command=self.destroy).pack(side="right")

        # Thin separator above the button row
        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # ---- Scrollable body — preview may be taller than the dialog
        canvas = tk.Canvas(self, bg=Palette.SURFACE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=Palette.SURFACE, padx=20, pady=20)
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Keep body frame width in sync with the canvas so text wraps
            # correctly rather than being clipped or wrapping too early.
            canvas.itemconfigure(body_id, width=canvas.winfo_width())

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(body_id, width=event.width)

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel / trackpad scrolling.
        # macOS trackpad sends per-pixel delta (no /120 needed).
        # Windows/Linux mouse wheel sends ±120 multiples.
        # Bind recursively so trackpad works over any child widget.
        import sys as _sys

        def _scroll(event: tk.Event) -> None:
            if _sys.platform == "darwin":
                canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_scroll(widget: tk.Widget) -> None:
            widget.bind("<MouseWheel>", _scroll, add=True)
            widget.bind("<Button-4>",
                        lambda e: canvas.yview_scroll(-1, "units"), add=True)
            widget.bind("<Button-5>",
                        lambda e: canvas.yview_scroll(1, "units"), add=True)
            for child in widget.winfo_children():
                _bind_scroll(child)

        _bind_scroll(canvas)
        _bind_scroll(body)
        self.after(100, lambda: _bind_scroll(body))

        # Preview — scale to half DPI for screen display.
        full = self._image
        target_w = int(self._services.label.style.width_in * self._PREVIEW_DPI)
        target_h = int(self._services.label.style.height_in * self._PREVIEW_DPI)
        from PIL import Image, ImageTk
        preview = full.resize((target_w, target_h), Image.LANCZOS)
        # Hold a reference on `self` so Tk's GC doesn't blank the image.
        self._photo = ImageTk.PhotoImage(preview)

        preview_wrap = tk.Frame(
            body, bg=Palette.SURFACE,
            highlightthickness=1, highlightbackground=Palette.BORDER,
        )
        preview_wrap.pack(pady=(0, 14))
        tk.Label(preview_wrap, image=self._photo, bg=Palette.SURFACE
                 ).pack(padx=4, pady=4)

        # Metadata caption
        s = self._services.label.style
        meta = (
            f"📐  {s.width_in}\" × {s.height_in}\" at {s.dpi} dpi  "
            f"({full.size[0]} × {full.size[1]} px)"
        )
        tk.Label(body, text=meta, bg=Palette.SURFACE,
                 fg=Palette.MUTED, font=base_font()
                 ).pack(pady=(0, 4))
        tip = (
            "Take the downloaded file to your print shop — they can print at "
            "this exact size on label paper, or larger for posters."
        )
        tk.Label(body, text=tip, bg=Palette.SURFACE, fg=Palette.MUTED,
                 font=base_font(), wraplength=640, justify="center"
                 ).pack(pady=(0, 0))

    # --------------------------------------------------------- actions   #

    def _download(self) -> None:
        # Suggested filename — sanitize serial for cross-platform safety.
        safe_serial = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in self._serial
        )
        default = f"label_{safe_serial}_{date.today().isoformat()}.png"
        path_str = filedialog.asksaveasfilename(
            parent=self,
            title="Download Label",
            defaultextension=".png",
            initialfile=default,
            filetypes=[
                ("PNG image", "*.png"),
                ("PDF document", "*.pdf"),
                ("JPEG image", "*.jpg"),
                ("All files", "*.*"),
            ],
        )
        if not path_str:
            return
        try:
            written = self._services.label.save(self._image, Path(path_str))
            messagebox.showinfo(
                "Saved",
                f"Label saved to:\n{written}",
                parent=self,
            )
        except Exception as e:
            _log.exception("Label save failed")
            messagebox.showerror("Save failed", str(e), parent=self)
