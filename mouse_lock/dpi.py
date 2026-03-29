"""Best-effort DPI awareness for Windows."""
from __future__ import annotations

import ctypes


def init_dpi_awareness() -> None:
    """Best-effort DPI awareness. Tries modern API first, falls back, never crashes."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
