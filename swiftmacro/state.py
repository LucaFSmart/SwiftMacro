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
    chain_progress: tuple[int, int] = field(default=(0, 0))  # (current_step, total_steps)
    update_available: bool = field(default=False)
    update_url: str = field(default="")

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
            self.chain_progress = (0, 0)  # reset on both start and stop

    # --- chain lock ---
    def get_chain_lock(self) -> tuple[bool, tuple[int, int] | None]:
        with self._lock:
            return self.chain_lock_active, self.chain_lock_pos

    def set_chain_lock(self, active: bool, pos: tuple[int, int] | None = None) -> None:
        with self._lock:
            self.chain_lock_active = active
            self.chain_lock_pos = pos

    # --- chain progress ---
    def set_chain_progress(self, current: int, total: int) -> None:
        with self._lock:
            self.chain_progress = (current, total)

    def get_chain_progress(self) -> tuple[int, int]:
        with self._lock:
            return self.chain_progress

    # --- update availability ---
    def set_update_available(self, url: str) -> None:
        with self._lock:
            self.update_available = True
            self.update_url = url

    def get_update_available(self) -> tuple[bool, str]:
        with self._lock:
            return self.update_available, self.update_url


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
        chain_progress=(0, 0),
        update_available=False,
        update_url="",
        _lock=threading.Lock(),
    )
