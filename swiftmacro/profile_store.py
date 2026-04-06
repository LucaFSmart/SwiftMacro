"""Profile persistence — load/save profiles to JSON."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from swiftmacro.constants import MAX_PROFILES, SYSTEM_HOTKEYS
from swiftmacro.log import get_logger
from swiftmacro.models import Profile

_log = get_logger("profile_store")


@dataclass
class ProfileImportResult:
    imported_ids: list[str]
    cleared_hotkeys: int
    skipped_invalid: int
    parse_errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.parse_errors is None:
            self.parse_errors = []


class ProfileStore:
    def __init__(self, profiles_dir: str | None = None, legacy_dir: str | None = None) -> None:
        if profiles_dir is None:
            from swiftmacro.constants import PROFILES_DIR
            profiles_dir = os.path.expanduser(PROFILES_DIR)
        if legacy_dir is None:
            from swiftmacro.constants import PROFILES_DIR_LEGACY
            legacy_dir = os.path.expanduser(PROFILES_DIR_LEGACY)

        self._dir = Path(profiles_dir)
        self._legacy_dir = Path(legacy_dir)
        self._file = self._dir / "profiles.json"
        self._lock = threading.Lock()
        self._profiles: list[Profile] = []
        self._ensure_dir()
        self._maybe_migrate()
        self._profiles = self._load_from_disk()

    def _ensure_dir(self) -> None:
        os.makedirs(self._dir, exist_ok=True)

    def _maybe_migrate(self) -> None:
        """Migrate profiles from the legacy ~/.mouse_lock location if needed."""
        import shutil

        legacy_file = self._legacy_dir / "profiles.json"
        if self._file.exists() or not legacy_file.exists():
            return

        tmp_path_str = None
        try:
            tmp_fd, tmp_path_str = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
            os.close(tmp_fd)
            shutil.copy2(str(legacy_file), tmp_path_str)
            os.replace(tmp_path_str, str(self._file))
            _log.info("Migrated profiles from %s to %s", legacy_file, self._file)
            tmp_path_str = None  # consumed by os.replace
        except Exception as exc:
            _log.error("Profile migration failed: %s", exc)
            if tmp_path_str is not None and os.path.exists(tmp_path_str):
                try:
                    os.unlink(tmp_path_str)
                except OSError:
                    pass

    def _load_from_disk(self) -> list[Profile]:
        if not self._file.exists():
            _log.info("No profiles file found at %s — starting empty", self._file)
            return []
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except Exception as exc:
            _log.warning("Failed to parse profiles JSON at %s: %s", self._file, exc)
            return []
        if not isinstance(data, list):
            _log.warning("profiles.json at %s is not a list — ignoring", self._file)
            return []
        profiles: list[Profile] = []
        skipped = 0
        for entry in data:
            try:
                profiles.append(Profile.from_dict(entry))
            except Exception as exc:
                skipped += 1
                _log.warning("Skipping malformed profile entry: %s", exc)
        if skipped:
            _log.warning(
                "Loaded %d profile(s) from %s (%d skipped)",
                len(profiles), self._file, skipped,
            )
        else:
            _log.info("Loaded %d profile(s) from %s", len(profiles), self._file)
        return profiles

    def _save_to_disk(self) -> None:
        data = [p.to_dict() for p in self._profiles]
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(self._file))
            _log.debug("Saved %d profile(s) to %s", len(data), self._file)
        except Exception as exc:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            _log.error("Failed to save profiles to %s: %s", self._file, exc)
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
        raw_profiles, parse_errors = self._read_import_file(import_path)
        imported_ids: list[str] = []
        cleared_hotkeys = 0
        valid_profiles = [profile for profile in raw_profiles if self._profile_is_valid(profile)]
        skipped_invalid = len(raw_profiles) - len(valid_profiles) + len(parse_errors)

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
            parse_errors=parse_errors,
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
        if profile.has_blocking_lock_before_end():
            return False
        return all(step.validate() for step in profile.steps)

    @staticmethod
    def _read_import_file(import_path: str) -> tuple[list[Profile], list[str]]:
        """Parse an import file. Returns (profiles, parse_errors).

        Individual malformed entries are skipped and reported in parse_errors;
        only an unreadable file or an unsupported top-level type raises.
        """
        try:
            raw = json.loads(Path(import_path).read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError("Could not read profile file") from exc

        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            raise ValueError("Profile import must contain a profile object or list")

        profiles: list[Profile] = []
        errors: list[str] = []
        for index, item in enumerate(raw):
            try:
                profiles.append(Profile.from_dict(item))
            except Exception as exc:
                errors.append(f"Entry {index}: {exc}")
                _log.warning("Skipping malformed import entry %d: %s", index, exc)
        return profiles, errors
