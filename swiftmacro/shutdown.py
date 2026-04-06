"""Shutdown coordination — replaces the old `_shutdown_ref` global hack.

`HotkeyManager` and `TrayManager` need to trigger application shutdown without
importing `app.py` (which would create a circular import). Previously this was
solved by a module-level mutable list. Now they take a `ShutdownCoordinator`
instance via constructor injection — cleaner, easier to test, no global state.
"""
from __future__ import annotations

from typing import Callable

from swiftmacro.log import get_logger

_log = get_logger("shutdown")


class ShutdownCoordinator:
    """Holds a single shutdown callback that can be set late and triggered safely."""

    def __init__(self) -> None:
        self._callback: Callable[[], None] | None = None

    def set_callback(self, callback: Callable[[], None]) -> None:
        self._callback = callback

    def trigger(self) -> None:
        cb = self._callback
        if cb is None:
            _log.warning("Shutdown triggered before a callback was registered — ignoring")
            return
        try:
            cb()
        except Exception as exc:
            _log.error("Shutdown callback raised: %s", exc)
