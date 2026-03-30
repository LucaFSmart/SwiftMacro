"""Global hotkey registration and management."""
from __future__ import annotations

from mouse_lock.constants import (
    HOTKEY_EXIT,
    HOTKEY_RUN,
    HOTKEY_STOP_CHAIN,
    SYSTEM_HOTKEYS,
)
from mouse_lock.state import AppState


# Mutable reference so HotkeyManager can call shutdown() without circular import
_shutdown_ref: list = [lambda: None]


class HotkeyManager:
    def __init__(self, state: AppState, root, action_runner=None, profile_store=None) -> None:
        self._state = state
        self._root = root
        self._action_runner = action_runner
        self._profile_store = profile_store
        self._registered: list[str] = []
        self._profile_hotkeys: list[str] = []
        self._system_errors: list[str] = []
        self._profile_errors: list[str] = []

    def _sync_errors(self) -> None:
        self._state.set_hotkey_errors(self._system_errors + self._profile_errors)

    def register_all(self) -> None:
        import keyboard
        self._system_errors = []

        bindings = [
            (HOTKEY_EXIT, self._on_exit),
            (HOTKEY_RUN, self._on_run),
            (HOTKEY_STOP_CHAIN, self._on_stop_chain),
        ]
        for combo, callback in bindings:
            try:
                keyboard.add_hotkey(combo, callback, suppress=False)
                self._registered.append(combo)
            except Exception as exc:
                self._system_errors.append(f"{combo}: {exc}")
        self._sync_errors()

    def unregister_all(self) -> None:
        import keyboard
        for combo in self._registered + self._profile_hotkeys:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        try:
            keyboard.unhook_all_hotkeys()
            keyboard.unhook_all()
        except Exception:
            pass
        self._registered.clear()
        self._profile_hotkeys.clear()
        self._profile_errors = []
        self._system_errors = []
        self._sync_errors()

    def refresh_profile_hotkeys(self, profiles) -> None:
        import keyboard

        # Unregister old profile hotkeys
        for combo in self._profile_hotkeys:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._profile_hotkeys.clear()
        self._profile_errors = []

        # Register new ones (with conflict detection)
        seen: set[str] = set()
        for profile in profiles:
            if profile.hotkey is None:
                continue
            hk = profile.hotkey.lower()
            if hk in SYSTEM_HOTKEYS or hk in seen:
                self._profile_errors.append(
                    f"{profile.hotkey}: conflicts with existing hotkey"
                )
                continue
            seen.add(hk)
            try:
                keyboard.add_hotkey(
                    profile.hotkey,
                    lambda p=profile: self._on_profile_hotkey(p),
                    suppress=False,
                )
                self._profile_hotkeys.append(profile.hotkey)
            except Exception as exc:
                self._profile_errors.append(f"{profile.hotkey}: {exc}")
        self._sync_errors()

    def start(self):
        """No-op hook bootstrap kept for compatibility with the app wiring."""
        return None

    # --- callbacks ---

    def _on_exit(self) -> None:
        self._root.after(0, _shutdown_ref[0])

    def _on_run(self) -> None:
        if self._action_runner is None or self._profile_store is None:
            return
        profile_id = self._state.get_active_profile_id()
        if profile_id is None:
            self._state.set_status_message("No profile selected")
            return
        profile = self._profile_store.get_by_id(profile_id)
        if profile is None:
            self._state.set_status_message("Profile not found")
            return
        self._action_runner.run_profile(profile)

    def _on_stop_chain(self) -> None:
        if self._action_runner is not None:
            self._action_runner.stop()

    def _on_profile_hotkey(self, profile) -> None:
        if self._action_runner is not None:
            self._action_runner.run_profile(profile)
