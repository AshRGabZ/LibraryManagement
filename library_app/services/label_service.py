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
from typing import TYPE_CHECKING


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

    library_name: str = "GHCC LIBRARY"

    # Final pixel dimensions = inches × DPI. 3"×2" at 300dpi prints sharp on
    # any label printer and fits most pre-cut label sheets (e.g. Avery 5163).
    dpi: int = 300
    width_in: float = 3.0
    height_in: float = 2.0

    # Colors
    bg: str = "white"
    header_bg: str = "#1f2937"          # matches the app's HEADER_BG
    header_fg: str = "#ffffff"
    accent: str = "#2563eb"             # matches PRIMARY
    text: str = "#111827"
    muted: str = "#6b7280"
    border: str = "#1f2937"

    # Font sizes (in px at the target DPI — adjust if dimensions change).
    # `caption_pt` is for the small "SERIAL" / "CATEGORY" headings inside
    # the label; `value_pt` is for the big serial number and category text.
    title_pt: int = 56
    caption_pt: int = 22
    value_pt: int = 64


class LabelService:
    """Stateless renderer + saver for book labels."""

    def __init__(self, style: LabelStyle | None = None) -> None:
        self._style = style or LabelStyle()

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
        category_name: str | None,
    ) -> "Image":
        """Build the label as a Pillow RGB Image.

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
        draw = ImageDraw.Draw(img)

        # ---- Outer border -----------------------------------------------
        border_pad = 6
        draw.rectangle(
            [border_pad, border_pad, w - border_pad, h - border_pad],
            outline=s.border, width=4,
        )

        # ---- Header bar -------------------------------------------------
        header_h = int(h * 0.22)
        draw.rectangle(
            [border_pad, border_pad, w - border_pad, border_pad + header_h],
            fill=s.header_bg,
        )
        title_font = self._load_font(s.title_pt, bold=True)
        self._draw_centered(
            draw, s.library_name, font=title_font,
            cx=w // 2, cy=border_pad + header_h // 2,
            fill=s.header_fg,
        )

        # ---- Body content ----------------------------------------------
        caption_font = self._load_font(s.caption_pt, bold=False)
        value_font = self._load_font(s.value_pt, bold=True)
        category_font = self._load_font(
            int(s.value_pt * 0.65), bold=True
        )

        body_top = border_pad + header_h + 30
        left_pad = 50

        # SERIAL block
        draw.text(
            (left_pad, body_top),
            "SERIAL", font=caption_font, fill=s.muted,
        )
        draw.text(
            (left_pad, body_top + int(s.caption_pt * 1.3)),
            serial_number, font=value_font, fill=s.accent,
        )

        # CATEGORY block
        cat_top = body_top + int(s.caption_pt * 1.3) + s.value_pt + 24
        draw.text(
            (left_pad, cat_top),
            "CATEGORY", font=caption_font, fill=s.muted,
        )
        # Truncate long category names so they don't bleed off the label
        cat = (category_name or "—")
        max_chars = 22
        if len(cat) > max_chars:
            cat = cat[: max_chars - 1] + "…"
        draw.text(
            (left_pad, cat_top + int(s.caption_pt * 1.3)),
            cat, font=category_font, fill=s.text,
        )

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

    # ----------------------------------------------------------- helpers   #

    @staticmethod
    def _draw_centered(draw, text: str, *, font, cx: int, cy: int, fill: str) -> None:
        """Draw `text` centered on (cx, cy) using bbox math."""
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1]),
                  text, font=font, fill=fill)

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
