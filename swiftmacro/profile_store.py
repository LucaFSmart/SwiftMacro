"""Profile persistence — load/save profiles to JSON."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from swiftmacro.constants import MAX_PROFILES, SYSTEM_HOTKEYS
from swiftmacro.models import Profile


@dataclass
class ProfileImportResult:
    imported_ids: list[str]
    cleared_hotkeys: int
    skipped_invalid: int


class ProfileStore:
    def __init__(self, profiles_dir: str | None = None) -> None:
        if profiles_dir is None:
            from swiftmacro.constants import PROFILES_DIR
            profiles_dir = os.path.expanduser(PROFILES_DIR)
        self._dir = Path(profiles_dir)
        self._file = self._dir / "profiles.json"
        self._lock = threading.Lock()
        self._profiles: list[Profile] = []
        self._ensure_dir()
        self._profiles = self._load_from_disk()

    def _ensure_dir(self) -> None:
        os.makedirs(self._dir, exist_ok=True)

    def _load_from_disk(self) -> list[Profile]:
        if not self._file.exists():
            return []
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            return [Profile.from_dict(d) for d in data]
        except Exception:
            return []

    def _save_to_disk(self) -> None:
        data = [p.to_dict() for p in self._profiles]
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(self._file))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self) -> list[Profile]:
        with self._lock:
            return [self._clone_profile(profile) for profile in self._profiles]

    def add_profile(self, profile: Profile) -> None:
        with self._lock:
            if len(self._profiles) >= MAX_PROFILES:
                raise ValueError(f"Max {MAX_PROFILES} profiles")
            self._profiles.append(self._clone_profile(profile))
            self._save_to_disk()

    def update_profile(self, profile: Profile) -> None:
        with self._lock:
            for i, p in enumerate(self._profiles):
                if p.id == profile.id:
                    self._profiles[i] = self._clone_profile(profile)
                    self._save_to_disk()
                    return
            raise KeyError(f"Profile {profile.id} not found")

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            self._profiles = [p for p in self._profiles if p.id != profile_id]
            self._save_to_disk()

    def get_by_id(self, profile_id: str) -> Profile | None:
        with self._lock:
            for p in self._profiles:
                if p.id == profile_id:
                    return self._clone_profile(p)
            return None

    def duplicate_profile(self, profile_id: str) -> Profile:
        with self._lock:
            if len(self._profiles) >= MAX_PROFILES:
                raise ValueError(f"Max {MAX_PROFILES} profiles")
            for profile in self._profiles:
                if profile.id == profile_id:
                    duplicate = self._clone_profile(profile)
                    duplicate.id = Profile.create_new(
                        name=duplicate.name,
                        hotkey=None,
                        steps=duplicate.steps,
                    ).id
                    duplicate.name = self._make_duplicate_name(duplicate.name)
                    duplicate.hotkey = None
                    self._profiles.append(self._clone_profile(duplicate))
                    self._save_to_disk()
                    return duplicate
            raise KeyError(f"Profile {profile_id} not found")

    def export_profiles(self, export_path: str, profile_ids: list[str] | None = None) -> int:
        with self._lock:
            if profile_ids is None:
                profiles = [self._clone_profile(profile) for profile in self._profiles]
            else:
                selected = set(profile_ids)
                profiles = [
                    self._clone_profile(profile)
                    for profile in self._profiles
                    if profile.id in selected
                ]
            Path(export_path).write_text(
                json.dumps([profile.to_dict() for profile in profiles], indent=2),
                encoding="utf-8",
            )
            return len(profiles)

    def import_profiles(self, import_path: str) -> ProfileImportResult:
        raw_profiles = self._read_import_file(import_path)
        imported_ids: list[str] = []
        cleared_hotkeys = 0
        valid_profiles = [profile for profile in raw_profiles if self._profile_is_valid(profile)]
        skipped_invalid = len(raw_profiles) - len(valid_profiles)

        with self._lock:
            if len(self._profiles) + len(valid_profiles) > MAX_PROFILES:
                free_slots = MAX_PROFILES - len(self._profiles)
                raise ValueError(f"Only {free_slots} profile slot(s) available")

            existing_hotkeys = {
                profile.hotkey.lower()
                for profile in self._profiles
                if profile.hotkey is not None
            }
            imported_hotkeys: set[str] = set()

            for raw_profile in valid_profiles:
                imported = Profile.create_new(
                    name=raw_profile.name,
                    hotkey=raw_profile.hotkey,
                    steps=raw_profile.steps,
                )
                if imported.hotkey is not None:
                    hotkey_lower = imported.hotkey.lower()
                    if (
                        hotkey_lower in SYSTEM_HOTKEYS
                        or hotkey_lower in existing_hotkeys
                        or hotkey_lower in imported_hotkeys
                    ):
                        imported.hotkey = None
                        cleared_hotkeys += 1
                    else:
                        existing_hotkeys.add(hotkey_lower)
                        imported_hotkeys.add(hotkey_lower)

                self._profiles.append(self._clone_profile(imported))
                imported_ids.append(imported.id)

            self._save_to_disk()

        return ProfileImportResult(
            imported_ids=imported_ids,
            cleared_hotkeys=cleared_hotkeys,
            skipped_invalid=skipped_invalid,
        )

    @staticmethod
    def _clone_profile(profile: Profile) -> Profile:
        return Profile.from_dict(profile.to_dict())

    def _make_duplicate_name(self, base_name: str) -> str:
        existing_names = {profile.name for profile in self._profiles}
        candidate = f"{base_name} (Copy)"
        suffix = 2
        while candidate in existing_names:
            candidate = f"{base_name} (Copy {suffix})"
            suffix += 1
        return candidate

    @staticmethod
    def _profile_is_valid(profile: Profile) -> bool:
        if not profile.name.strip():
            return False
        if not profile.steps:
            return False
        return all(step.validate() for step in profile.steps)

    @staticmethod
    def _read_import_file(import_path: str) -> list[Profile]:
        try:
            raw = json.loads(Path(import_path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError("Could not read profile file") from exc

        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            raise ValueError("Profile import must contain a profile object or list")

        try:
            return [Profile.from_dict(item) for item in raw]
        except Exception as exc:
            raise ValueError("Profile file format is invalid") from exc
