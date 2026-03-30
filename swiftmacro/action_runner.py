"""Execute action chains in a worker thread."""
from __future__ import annotations

import random
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
        _log.info("Chain started: %s (%d steps, repeat=%s)", profile.name, len(profile.steps), profile.repeat)
        iteration = 0
        try:
            self._state.set_status_message(f"Running: {profile.name}")
            while True:
                if self._stop_event.is_set():
                    break
                had_error = self._run_pass(profile)
                iteration += 1
                if had_error:
                    break
                if profile.repeat != 0 and iteration >= profile.repeat:
                    # Ran the requested number of times, no errors
                    if profile.repeat == 1:
                        self._state.set_status_message("Done")
                    else:
                        self._state.set_status_message(f"Done ({iteration}x)")
                    _log.info("Chain completed: %s (%d iterations)", profile.name, iteration)
                    break

            if self._stop_event.is_set():
                _log.info("Chain stopped: %s", profile.name)
        finally:
            self._state.set_chain_lock(False)
            self._state.set_runner_busy(False)
            with self._lock:
                self._running = False

    def _run_pass(self, profile: Profile) -> bool:
        """Run all steps once. Returns True if any step had an error."""
        had_error = False
        n = len(profile.steps)
        for i, step in enumerate(profile.steps):
            if self._stop_event.is_set():
                return had_error
            if not step.validate():
                self._state.set_status_message(f"Step {i+1}/{n}: invalid params")
                had_error = True
                continue
            self._state.set_status_message(f"Step {i+1}/{n}: {step.action}")
            if not self._execute_step(step):
                had_error = True
        return had_error

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

            elif step.action == "scroll":
                cursor.scroll(p["x"], p["y"], p["direction"], p["amount"])

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

            elif step.action == "hold_key":
                keyboard.press(p["key"])
                try:
                    duration_ms = p["duration_ms"]
                    if duration_ms == 0:
                        self._stop_event.wait()
                    else:
                        self._stop_event.wait(timeout=duration_ms / 1000.0)
                finally:
                    keyboard.release(p["key"])

            elif step.action == "random_delay":
                ms = random.randint(p["min_ms"], p["max_ms"])
                self._stop_event.wait(timeout=ms / 1000.0)

            return True
        except Exception as exc:
            _log.warning("Step failed [%s]: %s", step.action, exc)
            self._state.set_status_message(f"Step failed: {step.action}")
            return False
