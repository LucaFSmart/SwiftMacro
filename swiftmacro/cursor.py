"""Win32 cursor operations via ctypes."""
from __future__ import annotations

import ctypes
import time
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


MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
WHEEL_DELTA = 120


def drag(
    button: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int,
    stop_event: Event,
) -> bool:
    """Press at (x1, y1), interpolate to (x2, y2), then release.

    ``duration_ms`` controls how long the move takes; 0 means "snap" — only
    a single SetCursorPos to the destination is issued. The interpolation is
    interrupted promptly when ``stop_event`` is set, and the button is always
    released so we never leave the user with a stuck mouse button.
    """
    flags = _BUTTON_FLAGS.get(button)
    if flags is None:
        return False
    try:
        ctypes.windll.user32.SetCursorPos(x1, y1)
        ctypes.windll.user32.mouse_event(flags[0], 0, 0, 0, 0)
        try:
            if duration_ms <= 0:
                ctypes.windll.user32.SetCursorPos(x2, y2)
            else:
                # ~120 Hz interpolation, capped to avoid wasting cycles for
                # very short drags. The dx/dy fixed-step approach is enough
                # for typical drag-and-drop targets in games and apps.
                steps = max(2, min(int(duration_ms / 8), 240))
                step_sleep = (duration_ms / 1000.0) / steps
                for i in range(1, steps + 1):
                    if stop_event.is_set():
                        break
                    progress = i / steps
                    cur_x = int(x1 + (x2 - x1) * progress)
                    cur_y = int(y1 + (y2 - y1) * progress)
                    ctypes.windll.user32.SetCursorPos(cur_x, cur_y)
                    if step_sleep > 0:
                        time.sleep(step_sleep)
                # Always finish exactly on target.
                ctypes.windll.user32.SetCursorPos(x2, y2)
        finally:
            ctypes.windll.user32.mouse_event(flags[1], 0, 0, 0, 0)
        return True
    except Exception:
        # Best-effort: try to release the button so we never leave it stuck.
        try:
            ctypes.windll.user32.mouse_event(flags[1], 0, 0, 0, 0)
        except Exception:
            pass
        return False


def scroll(x: int, y: int, direction: str, amount: int) -> bool:
    """Scroll at (x, y). direction: up/down/left/right. amount: notch count."""
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        if direction in ("up", "down"):
            delta = WHEEL_DELTA * amount * (1 if direction == "up" else -1)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        else:
            delta = WHEEL_DELTA * amount * (1 if direction == "right" else -1)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, delta, 0)
        return True
    except Exception:
        return False
