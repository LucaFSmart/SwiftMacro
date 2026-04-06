"""Profile manager — single entry point for profile CRUD + side effects.

Before this layer existed, the UI talked to ``ProfileStore`` directly and was
responsible for calling ``HotkeyManager.refresh_profile_hotkeys()`` after every
mutation. That was easy to forget; one missed refresh meant a profile would
silently lose its hotkey binding.

``ProfileManager`` centralises the contract: every CRUD operation that can
change the set of registered hotkeys triggers a refresh automatically.
"""
from __future__ import annotations

import time
from typing import Optional

from swiftmacro.log import get_logger
from swiftmacro.models import Profile
from swiftmacro.profile_store import ProfileImportResult, ProfileStore

_log = get_logger("profile_manager")


class ProfileManager:
    def __init__(self, store: ProfileStore, hotkey_mgr=None) -> None:
        self._store = store
        self._hotkey_mgr = hotkey_mgr

    # --- read --------------------------------------------------------------
    def list(self) -> list[Profile]:
        return self._store.load()

    def get(self, profile_id: str) -> Optional[Profile]:
        return self._store.get_by_id(profile_id)

    # --- write -------------------------------------------------------------
    def add(self, profile: Profile) -> None:
        self._store.add_profile(profile)
        self._sync_hotkeys()

    def update(self, profile: Profile) -> None:
        self._store.update_profile(profile)
        self._sync_hotkeys()

    def delete(self, profile_id: str) -> None:
        self._store.delete_profile(profile_id)
        self._sync_hotkeys()

    def duplicate(self, profile_id: str) -> Profile:
        duplicate = self._store.duplicate_profile(profile_id)
        self._sync_hotkeys()
        return duplicate

    # --- io ----------------------------------------------------------------
    def import_file(self, path: str) -> ProfileImportResult:
        result = self._store.import_profiles(path)
        self._sync_hotkeys()
        return result

    def export_file(self, path: str, profile_ids: list[str] | None = None) -> int:
        return self._store.export_profiles(path, profile_ids)

    # --- run history -------------------------------------------------------
    def record_run(self, profile_id: str) -> None:
        """Bump ``run_count`` and ``last_run_at`` after a successful run.

        Called from the ActionRunner's completion callback. Failures are
        swallowed and logged so a recording glitch can never affect the
        running chain or the next run.
        """
        try:
            profile = self._store.get_by_id(profile_id)
            if profile is None:
                return
            profile.run_count += 1
            profile.last_run_at = time.time()
            self._store.update_profile(profile)
        except Exception as exc:
            _log.warning("Failed to record run for %s: %s", profile_id, exc)

    # --- internal ----------------------------------------------------------
    def _sync_hotkeys(self) -> None:
        if self._hotkey_mgr is None:
            return
        try:
            self._hotkey_mgr.refresh_profile_hotkeys(self._store.load())
        except Exception as exc:
            # Hotkey binding failures must never break a profile mutation.
            _log.warning("Hotkey refresh failed after profile mutation: %s", exc)
