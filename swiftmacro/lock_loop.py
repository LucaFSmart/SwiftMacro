"""Lock loop — daemon thread that holds cursor at a target position."""
from __future__ import annotations

import ctypes
import threading

from swiftmacro.constants import LOCK_INTERVAL_MS
from swiftmacro.log import get_logger
from swiftmacro.state import AppState

_log = get_logger("lock_loop")


class LockLoop:
    """Continuously moves cursor to target position based on state flags."""

    def __init__(self, state: AppState) -> None:
        self._state = state
        self._thread: threading.Thread | None = None

    def run(self) -> None:
        """Thread entry point. Exits when stop_event is set."""
        while not self._state.stop_event.is_set():
            target = self._get_target()
            if target is not None:
                try:
                    ctypes.windll.user32.SetCursorPos(target[0], target[1])
                except Exception:
                    pass
            self._state.stop_event.wait(timeout=LOCK_INTERVAL_MS / 1000.0)

    def _get_target(self) -> tuple[int, int] | None:
        """Determine cursor target from the active profile chain lock only."""
        chain_active, chain_pos = self._state.get_chain_lock()
        if chain_active and chain_pos is not None:
            return chain_pos
        return None

    def start(self) -> threading.Thread:
        if self._thread is not None and self._thread.is_alive():
            return self._thread
        self._thread = threading.Thread(target=self.run, name="LockLoop", daemon=True)
        self._thread.start()
        _log.debug("LockLoop started")
        return self._thread

    def stop(self, timeout: float = 2.0) -> None:
        self._state.stop_event.set()
        _log.debug("LockLoop stopped")
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
