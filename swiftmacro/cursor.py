"""Win32 cursor operations via ctypes."""
from __future__ import annotations

import ctypes
from threading import Event

# mouse_event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def get_cursor_pos() -> tuple[int, int] | None:
    """Read current cursor position via Win32 GetCursorPos."""
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    try:
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return None


def set_cursor_pos(x: int, y: int) -> bool:
    """Move cursor to (x, y). Returns True on success."""
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        return True
    except Exception:
        return False


def click(button: str, x: int, y: int) -> bool:
    """Move to (x, y) and perform a single click. Returns True on success."""
    flags = _BUTTON_FLAGS.get(button)
    if flags is None:
        return False
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(flags[0], 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(flags[1], 0, 0, 0, 0)
        return True
    except Exception:
        return False


def repeat_click(
    button: str, x: int, y: int, count: int, interval_ms: int, stop_event: Event
) -> int:
    """Perform count clicks with interval. Returns number of clicks completed."""
    completed = 0
    for _ in range(count):
        if stop_event.is_set():
            break
        if click(button, x, y):
            completed += 1
        if stop_event.wait(timeout=interval_ms / 1000.0):
            break
    return completed
