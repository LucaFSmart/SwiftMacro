"""Thread-safe shared application state."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class AppState:
    stop_event: threading.Event
    hotkey_errors: list[str]
    status_message: str
    active_profile_id: str | None
    runner_busy: bool
    chain_lock_active: bool
    chain_lock_pos: tuple[int, int] | None
    _lock: threading.Lock = field(repr=False)

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

    def set_hotkey_errors(self, errors: list[str]) -> None:
        with self._lock:
            self.hotkey_errors = list(errors)

    def add_hotkey_error(self, error: str) -> None:
        with self._lock:
            self.hotkey_errors.append(error)

    # --- active profile ---
    def get_active_profile_id(self) -> str | None:
        with self._lock:
            return self.active_profile_id

    def set_active_profile_id(self, profile_id: str | None) -> None:
        with self._lock:
            self.active_profile_id = profile_id

    # --- runner busy ---
    def get_runner_busy(self) -> bool:
        with self._lock:
            return self.runner_busy

    def set_runner_busy(self, busy: bool) -> None:
        with self._lock:
            self.runner_busy = busy

    # --- chain lock ---
    def get_chain_lock(self) -> tuple[bool, tuple[int, int] | None]:
        with self._lock:
            return self.chain_lock_active, self.chain_lock_pos

    def set_chain_lock(self, active: bool, pos: tuple[int, int] | None = None) -> None:
        with self._lock:
            self.chain_lock_active = active
            self.chain_lock_pos = pos


def make_state() -> AppState:
    """Factory creates a fresh AppState with sensible defaults."""
    return AppState(
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        active_profile_id=None,
        runner_busy=False,
        chain_lock_active=False,
        chain_lock_pos=None,
        _lock=threading.Lock(),
    )
