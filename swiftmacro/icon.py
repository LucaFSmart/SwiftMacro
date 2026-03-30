"""System tray and window icon generation."""
from __future__ import annotations

import ctypes
import os
import tempfile

from swiftmacro.constants import APP_ID, ICON_SIZE


def _draw_icon(size: int) -> "Image.Image":
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_top = (14, 28, 44, 255)
    bg_bottom = (9, 17, 31, 255)
    for y in range(size):
        blend = y / max(size - 1, 1)
        color = tuple(
            int(bg_top[index] + (bg_bottom[index] - bg_top[index]) * blend) for index in range(4)
        )
        draw.line([(0, y), (size, y)], fill=color)

    inset = max(3, size // 18)
    draw.rounded_rectangle(
        [inset, inset, size - inset, size - inset],
        radius=max(8, size // 5),
        outline=(65, 93, 131, 255),
        width=max(1, size // 24),
    )

    cx = cy = size // 2
    outer_radius = size * 0.34
    middle_radius = size * 0.23
    inner_radius = size * 0.09
    accent = (79, 209, 197, 255)
    accent_soft = (79, 209, 197, 90)
    highlight = (153, 244, 232, 255)

    for radius, color, width in (
        (outer_radius, accent_soft, max(2, size // 20)),
        (middle_radius, accent, max(2, size // 18)),
    ):
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=color,
            width=width,
        )

    arm_gap = size * 0.14
    outer_arm = size * 0.42
    arm_width = max(2, size // 20)
    draw.line([(cx - outer_arm, cy), (cx - arm_gap, cy)], fill=accent, width=arm_width)
    draw.line([(cx + arm_gap, cy), (cx + outer_arm, cy)], fill=accent, width=arm_width)
    draw.line([(cx, cy - outer_arm), (cx, cy - arm_gap)], fill=accent, width=arm_width)
    draw.line([(cx, cy + arm_gap), (cx, cy + outer_arm)], fill=accent, width=arm_width)

    draw.ellipse(
        [cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius],
        fill=highlight,
    )
    return img


def create_tray_icon() -> "Image.Image":
    """Return the tray icon image."""
    return _draw_icon(ICON_SIZE)


def ensure_windows_icon_file() -> str:
    """Create an .ico file in the temp directory for Windows shell integrations."""
    icon_path = os.path.join(tempfile.gettempdir(), "mouse_lock_app.ico")
    icon_image = _draw_icon(256)
    icon_image.save(
        icon_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    return icon_path


def set_windows_app_id(app_id: str = APP_ID) -> bool:
    """Set the explicit AppUserModelID so the taskbar uses the custom app icon."""
    if os.name != "nt":
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False


def apply_window_icon(root) -> bool:
    """Apply the generated icon to the Tk window and taskbar."""
    success = False
    try:
        icon_path = ensure_windows_icon_file()
        root.iconbitmap(default=icon_path)
        success = True
    except Exception:
        pass

    try:
        from PIL import ImageTk

        icon_photo = ImageTk.PhotoImage(_draw_icon(128))
        root.iconphoto(True, icon_photo)
        root._mouse_lock_icon = icon_photo
        success = True
    except Exception:
        pass

    return success
