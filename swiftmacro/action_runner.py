"""Execute action chains in a worker thread."""
from __future__ import annotations

import threading

import keyboard

from swiftmacro import cursor
from swiftmacro.log import get_logger
from swiftmacro.models import ActionStep, Profile
from swiftmacro.state import AppState

_log = get_logger("action_runner")


class ActionRunner:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def run_profile(self, profile: Profile) -> None:
        with self._lock:
            if self._running:
                self._state.set_status_message("Already running")
                return
            self._running = True
            self._stop_event.clear()
            self._state.set_runner_busy(True)

        self._thread = threading.Thread(
            target=self._execute_chain,
            args=(profile,),
            name="ActionRunner",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        was_running = self.is_running()
        self._stop_event.set()
        t = self._thread
        if t is not None:
            t.join(timeout=2.0)
        self._thread = None
        if was_running and not self.is_running():
            self._state.set_status_message("Stopped")

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _execute_chain(self, profile: Profile) -> None:
        had_error = False
        _log.info("Chain started: %s (%d steps)", profile.name, len(profile.steps))
        try:
            self._state.set_status_message(f"Running: {profile.name}")
            for i, step in enumerate(profile.steps):
                if self._stop_event.is_set():
                    break

                if not step.validate():
                    self._state.set_status_message(f"Step {i+1}/{len(profile.steps)}: invalid params")
                    had_error = True
                    continue

                self._state.set_status_message(
                    f"Step {i+1}/{len(profile.steps)}: {step.action}"
                )
                if not self._execute_step(step):
                    had_error = True

            if not self._stop_event.is_set() and not had_error:
                self._state.set_status_message("Done")
                _log.info("Chain completed: %s", profile.name)
            else:
                _log.info("Chain stopped/errored: %s", profile.name)
        finally:
            self._state.set_chain_lock(False)
            self._state.set_runner_busy(False)
            with self._lock:
                self._running = False

    def _execute_step(self, step: ActionStep) -> bool:
        p = step.params
        try:
            if step.action == "move":
                cursor.set_cursor_pos(p["x"], p["y"])

            elif step.action == "click":
                cursor.click(p["button"], p["x"], p["y"])

            elif step.action == "repeat_click":
                cursor.repeat_click(
                    p["button"], p["x"], p["y"],
                    p["count"], p["interval_ms"],
                    self._stop_event,
                )

            elif step.action == "keypress":
                keyboard.press_and_release(p["key"])

            elif step.action == "wait":
                self._stop_event.wait(timeout=p["ms"] / 1000.0)

            elif step.action == "lock":
                self._state.set_chain_lock(True, (p["x"], p["y"]))
                duration_ms = p["duration_ms"]
                if duration_ms == 0:
                    self._stop_event.wait()  # block until stopped
                else:
                    self._stop_event.wait(timeout=duration_ms / 1000.0)

            return True
        except Exception as exc:
            _log.warning("Step failed [%s]: %s", step.action, exc)
            self._state.set_status_message(f"Step failed: {step.action}")
            return False
