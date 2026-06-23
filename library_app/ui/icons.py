"""Render emoji glyphs into fixed-size Tk images for aligned menu/icon use.

Inline emoji inside a widget's *text* can't be column-aligned: every glyph has a
different advance width, so labels start at ragged x-positions. The reliable fix
is to draw each emoji into a fixed WxH image and place it via ``compound="left"``
— equal-width images make every text label line up.

Rendering is best-effort: if Pillow or a colour-emoji font is unavailable the
helper returns ``None`` and callers fall back to plain text. Colour emoji fonts:
macOS = Apple Color Emoji, Windows = Segoe UI Emoji, Linux = Noto Color Emoji.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Any

# (font path, native render size). Bitmap-strike fonts (Apple/Noto) only render
# at a fixed size; COLR fonts (Segoe) render at any size — a large native size
# downsamples to a crisp icon either way.
_EMOJI_FONTS: dict[str, list[tuple[str, int]]] = {
    "darwin": [("/System/Library/Fonts/Apple Color Emoji.ttc", 160),
               ("/Library/Fonts/Apple Color Emoji.ttc", 160)],
    "win32": [("C:/Windows/Fonts/seguiemj.ttf", 109)],
    "linux": [("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 128),
              ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 128)],
}


def _font_candidates() -> list[tuple[str, int]]:
    """Platform-native emoji fonts first, then the rest as a fallback."""
    order = list(_EMOJI_FONTS.get(sys.platform, []))
    for plat, fonts in _EMOJI_FONTS.items():
        if plat != sys.platform:
            order.extend(fonts)
    return order


@lru_cache(maxsize=64)
def emoji_image(char: str, size: int = 18) -> Any | None:
    """Return a square ``ImageTk.PhotoImage`` of ``char``, or ``None`` on failure.

    A Tk root must already exist. The caller MUST keep a reference to the
    returned image — Tk garbage-collects images that nothing references.
    Results are cached so repeated requests reuse one image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageTk
    except Exception:
        return None

    for path, native in _font_candidates():
        if not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, native)
            canvas = Image.new("RGBA", (native, native), (0, 0, 0, 0))
            ImageDraw.Draw(canvas).text((0, 0), char, font=font,
                                        embedded_color=True)
            bbox = canvas.getbbox()
            if not bbox:
                continue
            glyph = canvas.crop(bbox)
            glyph.thumbnail((size, size), Image.LANCZOS)
            out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            out.paste(glyph, ((size - glyph.width) // 2,
                              (size - glyph.height) // 2), glyph)
            return ImageTk.PhotoImage(out)
        except Exception:
            continue
    return None
