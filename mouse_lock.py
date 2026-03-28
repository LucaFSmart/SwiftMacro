"""
Mouse Position Lock Tool
Windows desktop utility to save and restore cursor position via hotkeys.
"""
from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HOTKEY_SAVE       = "ctrl+alt+s"
HOTKEY_MOVE       = "ctrl+alt+m"
HOTKEY_TOGGLE     = "ctrl+alt+t"
HOTKEY_EXIT       = "ctrl+alt+esc"
LOCK_INTERVAL_MS  = 15    # milliseconds between lock-loop cursor corrections
UI_POLL_MS        = 200   # milliseconds between UI refresh cycles
ICON_SIZE         = 64    # tray icon size in pixels


# ---------------------------------------------------------------------------
# DPI awareness
# ---------------------------------------------------------------------------
def init_dpi_awareness() -> None:
    """Best-effort DPI awareness. Tries modern API first, falls back, never crashes."""
    try:
        # Windows 8.1+: per-monitor DPI awareness
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Windows Vista+: system DPI awareness
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # silently continue; minor coordinate mismatch possible


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
@dataclass
class AppState:
    saved_pos: tuple[int, int] | None
    lock_active: bool
    stop_event: threading.Event
    hotkey_errors: list[str]
    status_message: str
    _lock: threading.Lock = field(repr=False)

    # --- saved position ---
    def get_saved_pos(self) -> tuple[int, int] | None:
        with self._lock:
            return self.saved_pos

    def set_saved_pos(self, pos: tuple[int, int]) -> None:
        with self._lock:
            self.saved_pos = pos
            self.status_message = "Position saved"

    # --- lock ---
    def get_lock_active(self) -> bool:
        with self._lock:
            return self.lock_active

    def toggle_lock(self) -> bool:
        """Toggle lock state. Returns the new value."""
        with self._lock:
            self.lock_active = not self.lock_active
            return self.lock_active

    # --- status message ---
    def get_status_message(self) -> str:
        with self._lock:
            return self.status_message

    def set_status_message(self, msg: str) -> None:
        with self._lock:
            self.status_message = msg

    # --- hotkey errors ---
    def get_hotkey_errors(self) -> list[str]:
        with self._lock:
            return list(self.hotkey_errors)

    def add_hotkey_error(self, error: str) -> None:
        with self._lock:
            self.hotkey_errors.append(error)


def make_state() -> AppState:
    """Factory — creates a fresh AppState with sensible defaults."""
    return AppState(
        saved_pos=None,
        lock_active=False,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        _lock=threading.Lock(),
    )


# ---------------------------------------------------------------------------
# Tray icon (generated at runtime — no image file required)
# ---------------------------------------------------------------------------
def create_tray_icon() -> "Image.Image":
    """Draw a crosshair/target symbol on a dark background. Returns a PIL Image."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 2 - 4
    # Outer circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 100, 255), width=2)
    # Inner dot
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(0, 200, 100, 255))
    # Crosshair lines
    draw.line([(cx - r, cy), (cx - 6, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx + 6, cy), (cx + r, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy - r), (cx, cy - 6)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy + 6), (cx, cy + r)], fill=(0, 200, 100, 255), width=1)
    return img


# ---------------------------------------------------------------------------
# Lock loop — daemon thread that holds cursor at saved position
# ---------------------------------------------------------------------------
class LockLoop:
    """Continuously moves cursor to saved_pos while lock_active is True."""

    def __init__(self, state: AppState) -> None:
        self._state = state

    def run(self) -> None:
        """Thread entry point. Exits when stop_event is set."""
        while not self._state.stop_event.is_set():
            if self._state.get_lock_active():
                pos = self._state.get_saved_pos()
                if pos is not None:
                    try:
                        ctypes.windll.user32.SetCursorPos(pos[0], pos[1])
                    except Exception:
                        pass  # non-critical; next iteration will retry
            # Fast-exit sleep: wakes immediately when stop_event is set
            self._state.stop_event.wait(timeout=LOCK_INTERVAL_MS / 1000.0)

    def start(self) -> threading.Thread:
        """Spawn and return the daemon thread."""
        t = threading.Thread(target=self.run, name="LockLoop", daemon=True)
        t.start()
        return t
