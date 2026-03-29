"""Profile persistence — load/save profiles to JSON."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from mouse_lock.constants import MAX_PROFILES
from mouse_lock.models import Profile


class ProfileStore:
    def __init__(self, profiles_dir: str | None = None) -> None:
        if profiles_dir is None:
            from mouse_lock.constants import PROFILES_DIR
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
            return list(self._profiles)

    def add_profile(self, profile: Profile) -> None:
        with self._lock:
            if len(self._profiles) >= MAX_PROFILES:
                raise ValueError(f"Max {MAX_PROFILES} profiles")
            self._profiles.append(profile)
            self._save_to_disk()

    def update_profile(self, profile: Profile) -> None:
        with self._lock:
            for i, p in enumerate(self._profiles):
                if p.id == profile.id:
                    self._profiles[i] = profile
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
                    return p
            return None
