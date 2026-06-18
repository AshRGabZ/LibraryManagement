"""Printable book labels.

Renders a high-DPI label per physical copy. Output is a Pillow Image that
can be previewed in the UI or saved as PNG/JPG/PDF for a print shop.

Why Pillow? It's the de-facto standard for image generation in Python, ships
PNG/JPG/PDF/TIFF writers in one library, and gives us crisp text at any size.
The service stays UI-agnostic — `LabelPreviewDialog` consumes the Image
returned here without coupling to Tk.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from ..config import LIBRARY_NAME


if TYPE_CHECKING:  # avoid hard-importing Pillow at module load
    from PIL.Image import Image


_log = logging.getLogger(__name__)


# Common system font paths per platform. We probe these in order so the
# label uses a nicer face than Pillow's bitmap default whenever available,
# but never crashes when the user's box doesn't have any of them installed.
_FONT_CANDIDATES_BOLD: dict[str, list[str]] = {
    "darwin": [
        "/System/Library/Fonts/Helvetica.ttc",  # has bold variant baked in
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ],
    "win32": [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ],
    "linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ],
}
_FONT_CANDIDATES_REG: dict[str, list[str]] = {
    "darwin": [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ],
    "win32": [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ],
    "linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
}


@dataclass(frozen=True)
class LabelStyle:
    """Visual configuration — all in one place so a future redesign is one
    edit rather than rooting through paint code."""

    library_name: str = LIBRARY_NAME

    # Final pixel dimensions = inches × DPI. A roomy **portrait 2"×3"** tag at
    # 300 dpi (600×900 px) — taller than a spine label so the five stacked
    # fields (serial, book, author, category) print at a comfortable size.
    dpi: int = 300
    width_in: float = 2.0
    height_in: float = 3.0

    # Colors
    bg: str = "white"
    header_bg: str = "#1f2937"          # matches the app's HEADER_BG
    header_fg: str = "#ffffff"
    accent: str = "#2563eb"             # matches PRIMARY
    text: str = "#111827"
    muted: str = "#6b7280"
    border: str = "#1f2937"

    # Font sizes (px at the target DPI). Generous because the tag is large.
    # `title_pt` is auto-shrunk to fit the header width; `caption_pt` is the
    # small field headings; `serial_pt` is the big serial; `field_pt` is the
    # book / author / category values.
    title_pt: int = 46
    caption_pt: int = 26
    serial_pt: int = 82
    field_pt: int = 44

    # Background watermark (the library bookplate logo). Opacity is kept low so
    # text stays crisp on top; set to 0 to disable. The image is looked up at
    # library_app/assets/label_logo.png (or the LIBRARY_LABEL_LOGO env path).
    watermark_opacity: float = 0.28


class LabelService:
    """Stateless renderer + saver for book labels."""

    def __init__(self, style: LabelStyle | None = None) -> None:
        self._style = style or LabelStyle()
        self._wm_cache = None   # lazily-prepared watermark, or False if none

    # --------------------------------------------------------- logo / wm #

    def _logo_path(self) -> "Path | None":
        """Locate the bookplate logo: env override → bundled package asset
        (works both in dev and inside a PyInstaller bundle)."""
        import os
        override = os.environ.get("LIBRARY_LABEL_LOGO")
        if override:
            p = Path(override)
            return p if p.exists() else None
        candidates = []
        if getattr(sys, "frozen", False):  # PyInstaller bundle
            candidates.append(
                Path(getattr(sys, "_MEIPASS", "")) / "library_app" / "assets"
                / "label_logo.png"
            )
        candidates.append(
            Path(__file__).resolve().parent.parent / "assets" / "label_logo.png"
        )
        for c in candidates:
            if c.exists():
                return c
        return None

    def _watermark(self):
        """Return the faded, pre-sized watermark image (cached), or None."""
        if self._wm_cache is not None:
            return self._wm_cache or None
        if self._style.watermark_opacity <= 0:
            self._wm_cache = False
            return None
        path = self._logo_path()
        if path is None:
            self._wm_cache = False
            return None
        try:
            from PIL import Image
            logo = Image.open(path).convert("RGBA")
        except Exception:  # pragma: no cover - bad/corrupt image
            _log.warning("Could not load label logo: %s", path)
            self._wm_cache = False
            return None

        w, h = self._pixel_dims()
        header_h = int(h * 0.16)
        body_h = h - header_h - 14
        tw = int(w * 0.84)
        th = int(logo.height * (tw / logo.width))
        max_h = int(body_h * 0.94)
        if th > max_h:
            th = max_h
            tw = int(logo.width * (th / logo.height))
        logo = logo.resize((tw, th), Image.LANCZOS)
        faded = logo.split()[3].point(
            lambda a: int(a * self._style.watermark_opacity)
        )
        logo.putalpha(faded)
        self._wm_cache = logo
        return logo

    # --------------------------------------------------------- dims helper #

    @property
    def style(self) -> LabelStyle:
        return self._style

    def _pixel_dims(self) -> tuple[int, int]:
        s = self._style
        return int(s.width_in * s.dpi), int(s.height_in * s.dpi)

    # ---------------------------------------------------------- rendering  #

    def render(
        self,
        serial_number: str,
        title: str | None = None,
        author: str | None = None,
        category_name: str | None = None,
    ) -> "Image":
        """Build the label as a Pillow RGB Image — header (library name) plus
        SERIAL, BOOK, AUTHOR, CATEGORY.

        Raises ImportError with a friendly message if Pillow isn't installed.
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError as e:
            raise ImportError(
                "Label generation needs Pillow. Install with: pip install pillow"
            ) from e

        s = self._style
        w, h = self._pixel_dims()
        img = Image.new("RGB", (w, h), s.bg)

        border_pad = 7
        inner_left = border_pad + 30
        max_w = w - inner_left - (border_pad + 24)   # usable text width
        header_h = int(h * 0.16)

        # ---- Background watermark (library bookplate logo) --------------
        # Pasted first, faded, centred in the body — text is drawn opaque on
        # top, so nothing is lost. Skipped silently if no logo file is present.
        wm = self._watermark()
        if wm is not None:
            body_top = border_pad + header_h
            body_h = (h - border_pad) - body_top
            img.paste(
                wm,
                ((w - wm.width) // 2, body_top + (body_h - wm.height) // 2),
                wm,
            )

        draw = ImageDraw.Draw(img)

        # ---- Outer border -----------------------------------------------
        draw.rectangle(
            [border_pad, border_pad, w - border_pad, h - border_pad],
            outline=s.border, width=4,
        )

        # ---- Header bar (library name, auto-fit to width) ---------------
        draw.rectangle(
            [border_pad, border_pad, w - border_pad, border_pad + header_h],
            fill=s.header_bg,
        )
        title_font = self._fit_font(
            draw, s.library_name, s.title_pt, w - 2 * (border_pad + 16),
            bold=True,
        )
        self._draw_centered(
            draw, s.library_name, font=title_font,
            cx=w // 2, cy=border_pad + header_h // 2, fill=s.header_fg,
        )

        caption_font = self._load_font(s.caption_pt, bold=True)
        serial_font = self._load_font(s.serial_pt, bold=True)
        field_font = self._load_font(s.field_pt, bold=True)

        y = border_pad + header_h + 34

        def stacked(caption: str, value: str, value_font, color: str,
                    cap_gap: int, after: int) -> None:
            nonlocal y
            draw.text((inner_left, y), caption, font=caption_font, fill=s.muted)
            y += int(s.caption_pt) + cap_gap
            draw.text((inner_left, y),
                      self._truncate(draw, value, value_font, max_w),
                      font=value_font, fill=color)
            # advance by the value's rendered height + spacing
            bbox = draw.textbbox((0, 0), "Ag", font=value_font)
            y += (bbox[3] - bbox[1]) + after

        stacked("SERIAL", serial_number or "—", serial_font, s.accent, 8, 34)
        stacked("BOOK", title or "—", field_font, s.text, 6, 24)
        stacked("AUTHOR", author or "—", field_font, s.text, 6, 24)
        stacked("CATEGORY", category_name or "—", field_font, s.text, 6, 0)

        return img

    # --------------------------------------------------------- file output #

    def save(self, image: "Image", path: Path) -> Path:
        """Save the rendered label. Format is inferred from `path`'s suffix
        (.png / .jpg / .pdf / .tiff all work via Pillow)."""
        path = Path(path)
        # Ensure RGB for JPEG (no alpha)
        if path.suffix.lower() in (".jpg", ".jpeg") and image.mode != "RGB":
            image = image.convert("RGB")
        image.save(path, dpi=(self._style.dpi, self._style.dpi))
        _log.info("Label saved: %s", path)
        return path

    def render_sheet_pdf(
        self,
        path: Path,
        items: Sequence[tuple],
    ) -> Path:
        """Render a label for every `(serial, title, author, category)` item and
        tile them across a multi-page PDF (one file → print & cut).

        The grid auto-fits the label size onto US-Letter pages. Raises
        ValueError if `items` is empty, ImportError if Pillow is missing.
        """
        try:
            from PIL import Image
        except ImportError as e:
            raise ImportError(
                "Label generation needs Pillow. Install with: pip install pillow"
            ) from e
        if not items:
            raise ValueError("No labels to generate.")

        path = Path(path)
        lw, lh = self._pixel_dims()
        page_w = int(8.5 * self._style.dpi)   # US Letter @ dpi
        page_h = int(11.0 * self._style.dpi)
        cols = max(1, (page_w - 120) // (lw + 60))
        rows = max(1, (page_h - 120) // (lh + 60))
        per_page = cols * rows
        col_gap = (page_w - cols * lw) // (cols + 1)
        row_gap = (page_h - rows * lh) // (rows + 1)

        pages: list = []
        page = None
        for i, item in enumerate(items):
            serial, title, author, category = (list(item) + [None, None, None])[:4]
            if i % per_page == 0:
                page = Image.new("RGB", (page_w, page_h), "white")
                pages.append(page)
            label = self.render(serial, title, author, category)
            r, c = divmod(i % per_page, cols)
            page.paste(label, (col_gap + c * (lw + col_gap),
                               row_gap + r * (lh + row_gap)))

        pages[0].save(
            path, "PDF", save_all=True, append_images=pages[1:],
            resolution=float(self._style.dpi),
        )
        _log.info("Bulk labels PDF written: %s (%d labels, %d page(s))",
                  path, len(items), len(pages))
        return path

    # ----------------------------------------------------------- helpers   #

    @staticmethod
    def _draw_centered(draw, text: str, *, font, cx: int, cy: int, fill: str) -> None:
        """Draw `text` centered on (cx, cy) using bbox math."""
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1]),
                  text, font=font, fill=fill)

    @staticmethod
    def _text_w(draw, text: str, font) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    @classmethod
    def _truncate(cls, draw, text: str, font, max_w: int) -> str:
        """Trim `text` with an ellipsis so it fits within `max_w` pixels."""
        if cls._text_w(draw, text, font) <= max_w:
            return text
        ell = "…"
        while text and cls._text_w(draw, text + ell, font) > max_w:
            text = text[:-1]
        return (text + ell) if text else ell

    @classmethod
    def _fit_font(cls, draw, text: str, base_size: int, max_w: int, *, bold: bool):
        """Return a font sized so `text` fits within `max_w` (shrinks only)."""
        size = base_size
        while size > 12:
            font = cls._load_font(size, bold=bold)
            if cls._text_w(draw, text, font) <= max_w:
                return font
            size -= 2
        return cls._load_font(size, bold=bold)

    @staticmethod
    def _load_font(size: int, *, bold: bool):
        """Probe a few common system fonts. Falls back to PIL default if
        nothing is found — ugly but never fails."""
        from PIL import ImageFont
        candidates = (_FONT_CANDIDATES_BOLD if bold
                      else _FONT_CANDIDATES_REG).get(sys.platform, [])
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()
