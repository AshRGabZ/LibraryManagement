"""Printable book labels.

Renders a high-DPI label per physical copy. Output is a Pillow Image that
can be previewed in the UI or saved as PNG/JPG/PDF for a print shop.

Why Pillow? It's the de-facto standard for image generation in Python, ships
PNG/JPG/PDF/TIFF writers in one library, and gives us crisp text at any size.
The service stays UI-agnostic — `LabelPreviewDialog` consumes the Image
returned here without coupling to Tk.

Design: the bookplate art (assets/label_logo.png) is a full-frame illustration
— a "From the Library of" header at the top, a books/quill/banner cluster at
the bottom, and a large white band in the middle. We scale that art to fill the
label and overlay the details (SERIAL, BOOK, AUTHOR, CATEGORY) centered in the
white band. If no logo is found we fall back to a plain framed text label.
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

    # Final pixel dimensions = inches × DPI. A roomy **portrait 2"** wide tag at
    # 300 dpi; with a full-frame logo the height follows the artwork's aspect so
    # the frame never distorts (otherwise it's `height_in` tall).
    dpi: int = 300
    width_in: float = 2.0
    height_in: float = 3.0

    # Colors
    bg: str = "white"
    header_bg: str = "#1f2937"          # matches the app's HEADER_BG
    header_fg: str = "#ffffff"
    accent: str = "#1e3a8a"             # deep navy — matches the banner ink
    text: str = "#111827"
    muted: str = "#6b7280"
    border: str = "#1f2937"

    # Font sizes (px at the target DPI). `caption_pt` is the small field
    # headings; `serial_pt` is the big serial; `field_pt` is the book / author /
    # category values; `title_pt` is only used by the no-logo text fallback.
    title_pt: int = 46
    caption_pt: int = 24
    serial_pt: int = 70
    field_pt: int = 36

    # The bookplate logo is a full-frame background. The details are overlaid,
    # centered, in the white band between the top header art and the bottom
    # books/banner — these fractions of the label HEIGHT/WIDTH bound that band.
    # Tuned to the shipped assets/label_logo.png (content runs ~14%–62%).
    frame_top_frac: float = 0.17      # just below the "From the Library of" sprig
    frame_bottom_frac: float = 0.59   # just above the book stack / banner
    frame_side_frac: float = 0.12     # left/right inset for the centered text

    # Smallest the field text may auto-shrink to (so very long titles still fit
    # fully without being cut off).
    field_min_pt: int = 22


class LabelService:
    """Stateless renderer + saver for book labels."""

    def __init__(self, style: LabelStyle | None = None) -> None:
        self._style = style or LabelStyle()
        self._full_logo_cache = None   # native-size frame art, or False if none

    # --------------------------------------------------------- logo / frame #

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

    def _full_logo(self):
        """Return the full-frame bookplate art as a native-size RGBA image
        (cached), or None if no logo file is available."""
        if self._full_logo_cache is not None:
            return self._full_logo_cache or None
        path = self._logo_path()
        if path is None:
            self._full_logo_cache = False
            return None
        try:
            from PIL import Image
            logo = Image.open(path).convert("RGBA")
        except Exception:  # pragma: no cover - bad/corrupt image
            _log.warning("Could not load label logo: %s", path)
            self._full_logo_cache = False
            return None
        self._full_logo_cache = logo
        return logo

    # --------------------------------------------------------- dims helpers #

    @property
    def style(self) -> LabelStyle:
        return self._style

    def _pixel_dims(self) -> tuple[int, int]:
        """Fallback canvas size (no logo) — straight width_in × height_in."""
        s = self._style
        return int(s.width_in * s.dpi), int(s.height_in * s.dpi)

    def _label_dims(self) -> tuple[int, int]:
        """Working canvas size. With a full-frame logo the height follows the
        artwork's aspect (no distortion); otherwise width_in × height_in."""
        s = self._style
        w = int(s.width_in * s.dpi)
        logo = self._full_logo()
        if logo is not None:
            return w, round(w * logo.height / logo.width)
        return w, int(s.height_in * s.dpi)

    # ---------------------------------------------------------- rendering  #

    def render(
        self,
        serial_number: str,
        title: str | None = None,
        author: str | None = None,
        category_name: str | None = None,
    ) -> "Image":
        """Build the label as a Pillow RGB Image: the bookplate frame with the
        SERIAL, BOOK, AUTHOR and CATEGORY details centered in its white band.

        Raises ImportError with a friendly message if Pillow isn't installed.
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError as e:
            raise ImportError(
                "Label generation needs Pillow. Install with: pip install pillow"
            ) from e

        s = self._style
        logo = self._full_logo()
        if logo is None:
            return self._render_text_fallback(
                serial_number, title, author, category_name)

        w, h = self._label_dims()
        img = Image.new("RGB", (w, h), s.bg)
        frame = logo.resize((w, h), Image.LANCZOS)
        img.paste(frame, (0, 0), frame)
        draw = ImageDraw.Draw(img)

        cx = w // 2
        band_top = int(h * s.frame_top_frac)
        band_bottom = int(h * s.frame_bottom_frac)
        band_h = band_bottom - band_top
        max_w = int(w * (1 - 2 * s.frame_side_frac))
        group_gap = int(h * 0.022)

        caption_font = self._load_font(s.caption_pt, bold=True)
        serial_font = self._load_font(s.serial_pt, bold=True)
        cap_h = self._text_h(draw, caption_font)

        # (caption, value, is_serial, color). Serial is the big call-number;
        # the BOOK/AUTHOR/CATEGORY values wrap over as many lines as needed.
        specs = [
            ("SERIAL", serial_number or "—", True, s.accent),
            ("BOOK", title or "—", False, s.text),
            ("AUTHOR", author or "—", False, s.text),
            ("CATEGORY", category_name or "—", False, s.text),
        ]

        def _plan(field_pt: int):
            """Wrap every field at `field_pt`; return (rows, total_height)."""
            field_font = self._load_font(field_pt, bold=True)
            field_lh = self._text_h(draw, field_font) + 6
            serial_lh = self._text_h(draw, serial_font) + 6
            rows, total = [], 0
            for caption, value, is_serial, color in specs:
                vf = serial_font if is_serial else field_font
                lh = serial_lh if is_serial else field_lh
                lines = self._wrap(draw, value, vf, max_w,
                                   max_lines=2 if is_serial else 6)
                rows.append((caption, vf, lines, color, lh))
                total += cap_h + 6 + len(lines) * lh + group_gap
            return rows, total - group_gap   # no trailing gap

        # Auto-shrink the field text just enough that the FULL block fits the
        # white band — long titles wrap and shrink instead of being cut off.
        field_pt = s.field_pt
        rows, total = _plan(field_pt)
        while total > band_h and field_pt > s.field_min_pt:
            field_pt -= 2
            rows, total = _plan(field_pt)

        # Vertically center the block within the band; everything is centered
        # on the label's mid-line.
        y = band_top + max(0, (band_h - total) // 2)
        for caption, vf, lines, color, lh in rows:
            self._draw_center_x(draw, caption, caption_font, cx, y, s.muted)
            y += cap_h + 6
            for line in lines:
                self._draw_center_x(draw, line, vf, cx, y, color)
                y += lh
            y += group_gap

        return img

    def _render_text_fallback(
        self,
        serial_number: str,
        title: str | None,
        author: str | None,
        category_name: str | None,
    ) -> "Image":
        """Plain framed label used when no bookplate logo file is available."""
        from PIL import Image, ImageDraw

        s = self._style
        w, h = self._pixel_dims()
        img = Image.new("RGB", (w, h), s.bg)
        draw = ImageDraw.Draw(img)

        border_pad = 7
        margin = border_pad + 30
        max_w = w - 2 * margin

        draw.rectangle(
            [border_pad, border_pad, w - border_pad, h - border_pad],
            outline=s.border, width=4,
        )
        header_h = int(h * 0.16)
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
        y = border_pad + header_h + 34

        cx = w // 2
        caption_font = self._load_font(s.caption_pt, bold=True)
        serial_font = self._load_font(s.serial_pt, bold=True)
        cap_h = self._text_h(draw, caption_font)
        content_bottom = h - border_pad - 12
        group_gap = 16

        specs = [
            ("SERIAL", serial_number or "—", True, s.accent),
            ("BOOK", title or "—", False, s.text),
            ("AUTHOR", author or "—", False, s.text),
            ("CATEGORY", category_name or "—", False, s.text),
        ]

        def _plan(field_pt: int):
            field_font = self._load_font(field_pt, bold=True)
            field_lh = self._text_h(draw, field_font) + 5
            serial_lh = self._text_h(draw, serial_font) + 5
            rows, total = [], 0
            for caption, value, is_serial, color in specs:
                vf = serial_font if is_serial else field_font
                lh = serial_lh if is_serial else field_lh
                lines = self._wrap(draw, value, vf, max_w,
                                   max_lines=2 if is_serial else 8)
                rows.append((caption, vf, lines, color, lh))
                total += cap_h + 6 + len(lines) * lh + group_gap
            return rows, total

        field_pt = s.field_pt
        rows, total = _plan(field_pt)
        avail = content_bottom - y
        while total > avail and field_pt > s.field_min_pt:
            field_pt -= 2
            rows, total = _plan(field_pt)

        for caption, vf, lines, color, lh in rows:
            self._draw_center_x(draw, caption, caption_font, cx, y, s.muted)
            y += cap_h + 6
            for line in lines:
                self._draw_center_x(draw, line, vf, cx, y, color)
                y += lh
            y += group_gap

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
        lw, lh = self._label_dims()
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

    @classmethod
    def _draw_center_x(cls, draw, text: str, font, cx: int, y: int, fill: str) -> None:
        """Draw `text` horizontally centered on `cx`, with its top at `y`."""
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2 - bbox[0], y), text, font=font, fill=fill)

    @staticmethod
    def _text_w(draw, text: str, font) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]

    @staticmethod
    def _text_h(draw, font) -> int:
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        return bbox[3] - bbox[1]

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
    def _wrap(cls, draw, text: str, font, max_w: int, max_lines: int) -> list[str]:
        """Word-wrap `text` to lines fitting `max_w`, at most `max_lines`.

        Words longer than a line are hard-trimmed; if the text needs more than
        `max_lines`, the last line is ellipsised so nothing overflows."""
        text = (text or "").strip()
        if not text:
            return ["—"]
        words = text.split()
        lines: list[str] = []
        cur = ""
        i = 0
        while i < len(words):
            trial = words[i] if not cur else f"{cur} {words[i]}"
            if cls._text_w(draw, trial, font) <= max_w:
                cur = trial
                i += 1
            elif not cur:                      # single word too wide for a line
                cur = cls._truncate(draw, words[i], font, max_w)
                i += 1
            else:                              # wrap to next line
                lines.append(cur)
                cur = ""
                if len(lines) == max_lines - 1:   # last allowed line → rest here
                    rest = " ".join(words[i:])
                    lines.append(cls._truncate(draw, rest, font, max_w))
                    return lines
        if cur:
            lines.append(cur)
        return lines

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
