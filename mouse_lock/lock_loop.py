"""Lock loop — daemon thread that holds cursor at a target position."""
from __future__ import annotations

import ctypes
import threading

from mouse_lock.constants import LOCK_INTERVAL_MS
from mouse_lock.state import AppState


class LockLoop:
    """Continuously moves cursor to target position based on state flags."""

    def __init__(self, state: AppState) -> None:
        self._state = state

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
        """Determine cursor target using 3-case priority."""
        chain_active, chain_pos = self._state.get_chain_lock()
        if chain_active and chain_pos is not None:
            return chain_pos
        if self._state.get_lock_active():
            return self._state.get_saved_pos()
        return None

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run, name="LockLoop", daemon=True)
        t.start()
        return t
