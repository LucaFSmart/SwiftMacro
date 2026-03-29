"""System tray icon generation."""
from __future__ import annotations

from mouse_lock.constants import ICON_SIZE


def create_tray_icon() -> "Image.Image":
    """Draw a crosshair/target symbol on a dark background. Returns a PIL Image."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 2 - 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 100, 255), width=2)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(0, 200, 100, 255))
    draw.line([(cx - r, cy), (cx - 6, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx + 6, cy), (cx + r, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy - r), (cx, cy - 6)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy + 6), (cx, cy + r)], fill=(0, 200, 100, 255), width=1)
    return img
