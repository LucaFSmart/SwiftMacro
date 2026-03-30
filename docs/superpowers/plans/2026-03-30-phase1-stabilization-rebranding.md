# SwiftMacro Phase 1 — Stabilization & Rebranding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the project from "Mouse Lock" to "SwiftMacro", add structured logging, fix silent failures, and add critical test coverage so the codebase is ready for public release.

**Architecture:** The rename is purely mechanical (directory, files, imports, constants, UI strings). Logging is added via a new `swiftmacro/log.py` factory module consumed by all key modules. Bug fixes are surgical — all touched behavior is verified first with failing tests (TDD).

**Tech Stack:** Python 3.10+, pytest, unittest.mock, logging (stdlib), shutil (stdlib)

**Spec:** `docs/superpowers/specs/2026-03-30-phase1-stabilization-rebranding.md`

---

## File Map

| File | Action |
|------|--------|
| `mouse_lock/` → `swiftmacro/` | Rename (git mv) |
| `mouse_lock.py` → `swiftmacro.py` | Rename (git mv) |
| `mouse_lock.pyw` → `swiftmacro.pyw` | Rename (git mv) |
| `swiftmacro/log.py` | **New** — logger factory |
| `swiftmacro/constants.py` | Update 5 constants |
| `swiftmacro/app.py` | New startup order: dir → logging → ProfileStore; add migration call |
| `swiftmacro/profile_store.py` | Add migration, add logging to _load/_save, update imports |
| `swiftmacro/action_runner.py` | Add logging to _execute_step exception handler |
| `swiftmacro/hotkeys.py` | Add logging; DEBUG on unregister failures |
| `swiftmacro/lock_loop.py` | Add DEBUG logging |
| `swiftmacro/single_instance.py` | Add WARNING logging |
| `swiftmacro/tray.py` | Update icon title/name strings |
| `swiftmacro/ui/main_window.py` | Update hero body text |
| `tests/*.py` | Update all `from mouse_lock` imports |
| `tests/test_state.py` | Add 3 new tests |
| `tests/test_action_runner.py` | Add 2 new tests (runner_busy + log warning) |
| `tests/test_profile_store.py` | Add 4 new tests (log warning, roundtrip, migration x2) |
| `scripts/build_exe.ps1` | Update entry point, name, icon path |
| `README.md` | Update branding + commands |
| `AGENTS.md` | Update all mouse_lock → swiftmacro references |
| `CLAUDE.md` | Update branding + paths |

---

## Task 1: Package Rename

**Files:**
- Rename: `mouse_lock/` → `swiftmacro/`
- Rename: `mouse_lock.py` → `swiftmacro.py`
- Rename: `mouse_lock.pyw` → `swiftmacro.pyw`
- Modify: All `*.py` files in `swiftmacro/` and `tests/`

- [ ] **Step 1: Rename the package directory and entry points**

```bash
cd D:/Projekte/Coding/Auto
git mv mouse_lock swiftmacro
git mv mouse_lock.py swiftmacro.py
git mv mouse_lock.pyw swiftmacro.pyw
```

- [ ] **Step 2: Update all imports inside the package**

In every file under `swiftmacro/`, replace `from mouse_lock.` with `from swiftmacro.` and `import mouse_lock.` with `import swiftmacro.`. Also update `mouse_lock/__main__.py` reference.

Files to edit (replace `from mouse_lock.` → `from swiftmacro.`):
- `swiftmacro/app.py`
- `swiftmacro/profile_store.py`
- `swiftmacro/action_runner.py`
- `swiftmacro/hotkeys.py`
- `swiftmacro/lock_loop.py`
- `swiftmacro/single_instance.py`
- `swiftmacro/tray.py`
- `swiftmacro/icon.py`
- `swiftmacro/cursor.py`
- `swiftmacro/dpi.py`
- `swiftmacro/state.py`
- `swiftmacro/models.py`
- `swiftmacro/ui/main_window.py`
- `swiftmacro/ui/step_builder.py`
- `swiftmacro/ui/theme.py`
- `swiftmacro/__main__.py`

In `swiftmacro/__main__.py`, update the module name if it references `mouse_lock`:
```python
# swiftmacro/__main__.py
from swiftmacro.app import main

if __name__ == "__main__":
    main()
```

In `swiftmacro.py` (the root entry point), update imports:
```python
from swiftmacro.app import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update all imports in tests/**

In every file under `tests/`, replace `from mouse_lock.` with `from swiftmacro.` and `import mouse_lock.` with `import swiftmacro.`:
- `tests/conftest.py`
- `tests/test_action_runner.py`
- `tests/test_constants.py`
- `tests/test_hotkeys.py`
- `tests/test_lock_loop.py`
- `tests/test_models.py`
- `tests/test_profile_store.py`
- `tests/test_state.py`
- `tests/test_app.py`
- `tests/test_single_instance.py`
- `tests/test_ui.py`
- `tests/test_cursor.py`
- `tests/test_dpi.py`
- `tests/test_icon.py`

- [ ] **Step 4: Run tests — all must pass**

```bash
cd D:/Projekte/Coding/Auto
py -m pytest tests/ -q
```

Expected: all existing tests pass, 0 errors (no `ModuleNotFoundError`).

- [ ] **Step 5: Verify app launches**

```bash
py swiftmacro.py
```

Expected: app window opens, title shows "Mouse Lock Control Center" (branding update comes in Task 3).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename package mouse_lock → swiftmacro"
```

---

## Task 2: Update Constants

**Files:**
- Modify: `swiftmacro/constants.py`

- [ ] **Step 1: Update constants.py**

Replace the entire file content:

```python
"""All application constants."""

APP_NAME = "SwiftMacro"
APP_ID = "SwiftMacro.Desktop"
APP_MUTEX_NAME = "Local\\SwiftMacro.Desktop"

# System hotkeys
HOTKEY_EXIT = "ctrl+alt+esc"

# Profile hotkeys
HOTKEY_RUN = "ctrl+alt+r"
HOTKEY_STOP_CHAIN = "ctrl+alt+x"

# Intervals
LOCK_INTERVAL_MS = 15
UI_POLL_MS = 200
ICON_SIZE = 64

# Limits
MAX_PROFILES = 5
MAX_STEPS = 50

# File paths (expanded at runtime via os.path.expanduser)
PROFILES_DIR = "~/.swiftmacro"
PROFILES_FILE = "~/.swiftmacro/profiles.json"

# Legacy path for migration
PROFILES_DIR_LEGACY = "~/.mouse_lock"
PROFILES_FILE_LEGACY = "~/.mouse_lock/profiles.json"

# All system hotkeys for conflict detection
SYSTEM_HOTKEYS = frozenset({
    HOTKEY_EXIT, HOTKEY_RUN, HOTKEY_STOP_CHAIN,
})
```

- [ ] **Step 2: Run tests**

```bash
py -m pytest tests/test_constants.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add swiftmacro/constants.py
git commit -m "feat: update constants for SwiftMacro branding and legacy migration path"
```

---

## Task 3: Create swiftmacro/log.py

**Files:**
- Create: `swiftmacro/log.py`

- [ ] **Step 1: Create the logger factory**

```python
# swiftmacro/log.py
"""Central logging factory for SwiftMacro."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under swiftmacro.<name>."""
    return logging.getLogger(f"swiftmacro.{name}")


def configure_logging(profiles_dir: str) -> None:
    """Configure the root swiftmacro logger.

    Production mode (sys.stdout is None — .pyw / PyInstaller --noconsole):
        Rotating file handler → <profiles_dir>/swiftmacro.log, level INFO.
    Development mode (all other cases):
        basicConfig to stderr, level DEBUG.
    """
    import sys

    root = logging.getLogger("swiftmacro")
    root.setLevel(logging.DEBUG)

    if sys.stdout is None:
        # Production: write to rotating log file
        log_path = os.path.join(profiles_dir, "swiftmacro.log")
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    else:
        # Development: log to console
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s %(name)s: %(message)s",
        )
```

- [ ] **Step 2: Run tests to confirm nothing broken**

```bash
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add swiftmacro/log.py
git commit -m "feat: add log.py — central logging factory with dev/prod mode"
```

---

## Task 4: Update app.main() Startup Order + UI Strings

**Files:**
- Modify: `swiftmacro/app.py`
- Modify: `swiftmacro/tray.py`
- Modify: `swiftmacro/ui/main_window.py`

- [ ] **Step 1: Update app.py with correct initialization order**

The new startup sequence in `main()`:
1. `init_dpi_awareness()`
2. `set_windows_app_id(APP_ID)`
3. Create `~/.swiftmacro/` dir (detect first-run)
4. Configure logging
5. Single-instance check
6. All other init (state, root, profile_store, ...)

Replace the `main()` function in `swiftmacro/app.py`:

```python
def main() -> None:
    import os
    import sys

    from swiftmacro.constants import APP_ID, APP_MUTEX_NAME, PROFILES_DIR
    from swiftmacro.log import configure_logging, get_logger

    init_dpi_awareness()
    set_windows_app_id(APP_ID)

    # Step 1: Ensure profile directory exists (must happen before logging)
    profiles_dir = os.path.expanduser(PROFILES_DIR)
    first_run = not os.path.isdir(profiles_dir)
    os.makedirs(profiles_dir, exist_ok=True)

    # Step 2: Configure logging (file handler now has a valid directory)
    configure_logging(profiles_dir)
    log = get_logger("app")

    if first_run:
        log.info("Profile directory initialized at %s", profiles_dir)
    log.info("SwiftMacro starting up")

    # Step 3: Single-instance guard
    instance_guard = acquire_single_instance(APP_MUTEX_NAME)
    if instance_guard.already_running:
        log.warning("Another instance is already running — exiting")
        instance_guard.release()
        return

    import tkinter as tk

    state = make_state()
    root = tk.Tk()
    apply_window_icon(root)
    profile_store = ProfileStore()  # migration runs here
    action_runner = ActionRunner(state)

    tray_mgr = TrayManager(state, root)
    tray_available = tray_mgr.start()
    if not tray_available:
        state.set_status_message("Tray unavailable")

    hotkey_mgr = HotkeyManager(state, root, action_runner, profile_store)
    MainWindow(
        root,
        state,
        tray_available,
        profile_store=profile_store,
        hotkey_mgr=hotkey_mgr,
        action_runner=action_runner,
    )

    lock_loop = LockLoop(state)
    lock_loop.start()

    shutdown_fn = make_shutdown(
        state,
        hotkey_mgr,
        action_runner,
        lock_loop,
        tray_mgr if tray_available else None,
        instance_guard,
        root,
    )
    _shutdown_ref[0] = shutdown_fn

    hotkey_mgr.register_all()
    hotkey_mgr.refresh_profile_hotkeys(profile_store.load())
    hotkey_mgr.start()

    log.info("Startup complete")
    try:
        root.mainloop()
    finally:
        shutdown_fn()
        log.info("SwiftMacro shut down")
```

Also add the missing imports at the top of `app.py`:
```python
from swiftmacro.dpi import init_dpi_awareness
from swiftmacro.hotkeys import HotkeyManager, _shutdown_ref
from swiftmacro.icon import apply_window_icon, set_windows_app_id
from swiftmacro.lock_loop import LockLoop
from swiftmacro.profile_store import ProfileStore
from swiftmacro.single_instance import SingleInstanceGuard, acquire_single_instance
from swiftmacro.state import AppState, make_state
from swiftmacro.tray import TrayManager
from swiftmacro.ui.main_window import MainWindow
from swiftmacro.action_runner import ActionRunner
```

- [ ] **Step 2: Update tray.py icon strings**

In `swiftmacro/tray.py`, update the `pystray.Icon(...)` call:
```python
self._icon = pystray.Icon(
    name="SwiftMacro",
    icon=icon_image,
    title="SwiftMacro",
    menu=menu,
)
```

- [ ] **Step 3: Update main_window.py hero body text**

In `swiftmacro/ui/main_window.py`, find the hero body label text and replace:
```python
# Old:
"Profile-first desktop automation for reusable click, keypress, wait and lock flows."
# New:
"Profile-first desktop automation for gamers and power users — build reusable click, keypress, wait and lock flows."
```

- [ ] **Step 4: Run tests**

```bash
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add swiftmacro/app.py swiftmacro/tray.py swiftmacro/ui/main_window.py
git commit -m "feat: update startup order, tray strings, and hero body text for SwiftMacro"
```

---

## Task 5: TDD — AppState Thread Safety Tests

**Files:**
- Modify: `tests/test_state.py`

The existing `test_chain_lock` and `test_chain_lock_reset` don't verify concurrent safety or stop_event propagation. These three new tests are required by the spec.

- [ ] **Step 1: Write the failing/new tests**

Append to `tests/test_state.py`:

```python
import threading
import time


def test_set_chain_lock_atomic():
    """Both fields must be readable together consistently after set_chain_lock."""
    s = make_state()
    s.set_chain_lock(True, (123, 456))
    active, pos = s.get_chain_lock()
    assert active is True
    assert pos == (123, 456)
    # Reset — pass pos explicitly (pos has a default of None in state.py:64 but be explicit)
    s.set_chain_lock(False, None)
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None


def test_concurrent_state_access():
    """10 threads reading and writing simultaneously must not deadlock within 5s."""
    s = make_state()
    errors = []

    def worker(i):
        try:
            for _ in range(50):
                s.set_status_message(f"thread-{i}")
                _ = s.get_status_message()
                s.set_chain_lock(i % 2 == 0, (i, i))
                _ = s.get_chain_lock()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    alive = [t for t in threads if t.is_alive()]
    assert alive == [], f"{len(alive)} threads still running — possible deadlock"
    assert errors == [], f"Errors during concurrent access: {errors}"


def test_stop_event_propagates():
    """stop_event.set() in one thread must be observed from another thread."""
    s = make_state()
    observed = []

    def waiter():
        # wait up to 1s for the event
        s.stop_event.wait(timeout=1.0)
        observed.append(s.stop_event.is_set())

    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.05)
    s.stop_event.set()
    t.join(timeout=2.0)

    assert observed == [True]
```

- [ ] **Step 2: Run the new tests to verify they pass (state.py is already correct)**

```bash
py -m pytest tests/test_state.py -v -k "atomic or concurrent or propagates"
```

Expected: all 3 PASS (the implementation is already correct per code review).

- [ ] **Step 3: Commit**

```bash
git add tests/test_state.py
git commit -m "test: add thread-safety and atomicity tests for AppState"
```

---

## Task 6: TDD — ProfileStore Logging, Migration, Corrupt-File Warning

**Files:**
- Modify: `tests/test_profile_store.py`
- Modify: `swiftmacro/profile_store.py`

### 6a: Corrupt-file warning test + fix

- [ ] **Step 1: Write failing test for corrupt-file log warning**

Append to `tests/test_profile_store.py`:

```python
import logging


def test_load_returns_empty_on_corrupt_file_and_logs_warning(tmp_path, caplog):
    """Corrupt JSON must return [] AND log a WARNING."""
    (tmp_path / "profiles.json").write_text("not valid json{{{", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="swiftmacro.profile_store"):
        store = ProfileStore(profiles_dir=str(tmp_path))
    assert store.load() == []
    assert any("WARNING" in r.levelname and "profiles.json" in r.message.lower()
               or "parse" in r.message.lower() or "json" in r.message.lower()
               for r in caplog.records), \
        f"Expected a WARNING about corrupt JSON, got: {[r.message for r in caplog.records]}"
```

- [ ] **Step 2: Run to see it FAIL**

```bash
py -m pytest tests/test_profile_store.py::test_load_returns_empty_on_corrupt_file_and_logs_warning -v
```

Expected: FAIL — no log warning emitted yet.

- [ ] **Step 3: Fix _load_from_disk to log the warning**

In `swiftmacro/profile_store.py`, add import and logger at the top:
```python
from swiftmacro.log import get_logger

_log = get_logger("profile_store")
```

Update `_load_from_disk`:
```python
def _load_from_disk(self) -> list[Profile]:
    if not self._file.exists():
        _log.info("No profiles file found at %s — starting empty", self._file)
        return []
    try:
        data = json.loads(self._file.read_text(encoding="utf-8"))
        profiles = [Profile.from_dict(d) for d in data]
        _log.info("Loaded %d profile(s) from %s", len(profiles), self._file)
        return profiles
    except Exception as exc:
        _log.warning("Failed to load profiles from %s: %s", self._file, exc)
        return []
```

- [ ] **Step 4: Run to see it PASS**

```bash
py -m pytest tests/test_profile_store.py::test_load_returns_empty_on_corrupt_file_and_logs_warning -v
```

Expected: PASS.

### 6b: Export-then-import roundtrip test

- [ ] **Step 5: Write roundtrip test**

Append to `tests/test_profile_store.py`:

```python
def test_export_then_import_roundtrip(tmp_path, sample_profile):
    """Export a profile and re-import it; result must be identical."""
    store = ProfileStore(profiles_dir=str(tmp_path / "profiles"))
    store.add_profile(sample_profile)

    export_path = tmp_path / "export.json"
    store.export_profiles(str(export_path))

    store2 = ProfileStore(profiles_dir=str(tmp_path / "profiles2"))
    result = store2.import_profiles(str(export_path))

    assert len(result.imported_ids) == 1
    loaded = store2.load()
    assert loaded[0].name == sample_profile.name
    assert len(loaded[0].steps) == len(sample_profile.steps)
    assert loaded[0].steps[0].action == sample_profile.steps[0].action
```

- [ ] **Step 6: Run to verify it PASSES (existing code already supports this)**

```bash
py -m pytest tests/test_profile_store.py::test_export_then_import_roundtrip -v
```

Expected: PASS.

### 6c: Migration tests

- [ ] **Step 7: Write failing migration tests**

Append to `tests/test_profile_store.py`:

```python
import shutil


def test_migrate_profiles_on_first_launch(tmp_path, caplog):
    """If old ~/.mouse_lock/profiles.json exists and new path does not, profiles are migrated."""
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    # Create a valid profiles file in the old location
    old_file = old_dir / "profiles.json"
    old_file.write_text(
        '[{"id":"abc","name":"Migrated","hotkey":null,"steps":[{"action":"wait","params":{"ms":100}}]}]',
        encoding="utf-8",
    )
    # new_dir does NOT exist yet — ProfileStore will create it
    with caplog.at_level(logging.INFO, logger="swiftmacro.profile_store"):
        store = ProfileStore(profiles_dir=str(new_dir), legacy_dir=str(old_dir))

    assert (new_dir / "profiles.json").exists(), "New profiles.json should have been created"
    assert old_file.exists(), "Old file must NOT be deleted"
    profiles = store.load()
    assert len(profiles) == 1
    assert profiles[0].name == "Migrated"
    assert any("migrat" in r.message.lower() for r in caplog.records), \
        f"Expected migration INFO log, got: {[r.message for r in caplog.records]}"


def test_migrate_profiles_failure_leaves_no_partial_file(tmp_path, caplog, monkeypatch):
    """If migration copy raises, no partial file is left at destination."""
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    old_dir.mkdir()
    (old_dir / "profiles.json").write_text("[]", encoding="utf-8")
    new_dir.mkdir()

    # Patch shutil.copy2 to raise
    import shutil as _shutil
    monkeypatch.setattr(_shutil, "copy2", lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")))

    with caplog.at_level(logging.ERROR, logger="swiftmacro.profile_store"):
        store = ProfileStore(profiles_dir=str(new_dir), legacy_dir=str(old_dir))

    assert not (new_dir / "profiles.json").exists(), "No partial file should remain"
    assert store.load() == []
    assert any("ERROR" in r.levelname for r in caplog.records), \
        f"Expected ERROR log on migration failure, got: {[r.message for r in caplog.records]}"
```

- [ ] **Step 8: Run to see FAIL**

```bash
py -m pytest tests/test_profile_store.py -k "migrate" -v
```

Expected: FAIL — `ProfileStore.__init__` doesn't accept `legacy_dir` param or do migration yet.

- [ ] **Step 9: Implement migration in profile_store.py**

Update `ProfileStore.__init__` to accept an optional `legacy_dir` and perform atomic migration:

```python
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
```

Add the `_maybe_migrate` method:

```python
def _maybe_migrate(self) -> None:
    """Migrate profiles from the legacy ~/.mouse_lock location if needed."""
    import shutil
    import tempfile

    legacy_file = self._legacy_dir / "profiles.json"
    if self._file.exists() or not legacy_file.exists():
        return

    tmp_path = None
    try:
        tmp_fd, tmp_str = tempfile.mkstemp(dir=str(self._dir), suffix=".tmp")
        tmp_path = Path(tmp_str)
        os.close(tmp_fd)
        shutil.copy2(str(legacy_file), str(tmp_path))
        os.replace(str(tmp_path), str(self._file))
        _log.info("Migrated profiles from %s to %s", legacy_file, self._file)
        tmp_path = None  # consumed by os.replace
    except Exception as exc:
        _log.error("Profile migration failed: %s", exc)
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
```

Also add `_log.info` for save/add/delete in `_save_to_disk` and public mutators:

```python
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
```

- [ ] **Step 10: Run migration tests**

```bash
py -m pytest tests/test_profile_store.py -k "migrate" -v
```

Expected: both PASS.

- [ ] **Step 11: Run full test suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 12: Commit**

```bash
git add swiftmacro/profile_store.py tests/test_profile_store.py
git commit -m "feat: add ProfileStore logging, atomic migration from ~/.mouse_lock, and corrupt-file warning"
```

---

## Task 7: TDD — ActionRunner Logging

**Files:**
- Modify: `tests/test_action_runner.py`
- Modify: `swiftmacro/action_runner.py`

The existing `test_failed_step_status_is_not_overwritten_by_done` tests that the status message is set but does NOT verify a log WARNING is emitted. We need one test that asserts the log.

- [ ] **Step 1: Write failing test**

Append to `tests/test_action_runner.py`:

```python
import logging


def test_execute_step_exception_logs_warning(caplog):
    """When a step raises an exception, a WARNING must be logged."""
    from swiftmacro.state import make_state
    from swiftmacro.models import ActionStep, Profile
    from swiftmacro.action_runner import ActionRunner

    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="keypress", params={"key": "enter"})]
    profile = Profile(id="x", name="Test", hotkey=None, steps=steps)

    with caplog.at_level(logging.WARNING, logger="swiftmacro.action_runner"):
        with patch("swiftmacro.action_runner.keyboard.press_and_release",
                   side_effect=RuntimeError("boom")):
            runner.run_profile(profile)
            time.sleep(0.3)

    assert any("WARNING" in r.levelname for r in caplog.records), \
        f"Expected WARNING log, got: {[(r.levelname, r.message) for r in caplog.records]}"


def test_run_profile_sets_and_clears_runner_busy():
    """runner_busy must be True during execution and False when done.
    Note: get_runner_busy() already exists on AppState (state.py:52).
    """
    from swiftmacro.state import make_state
    from swiftmacro.models import ActionStep, Profile
    from swiftmacro.action_runner import ActionRunner

    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 100})]
    profile = Profile(id="x", name="Test", hotkey=None, steps=steps)

    runner.run_profile(profile)
    time.sleep(0.02)
    assert state.get_runner_busy() is True, "runner_busy should be True during execution"

    time.sleep(0.3)
    assert state.get_runner_busy() is False, "runner_busy should be False after completion"
```

- [ ] **Step 2: Run to see FAIL (log warning not yet emitted)**

```bash
py -m pytest tests/test_action_runner.py::test_execute_step_exception_logs_warning -v
```

Expected: FAIL.

- [ ] **Step 3: Add logging to action_runner.py**

Add import and logger at top of `swiftmacro/action_runner.py`:
```python
from swiftmacro.log import get_logger
_log = get_logger("action_runner")
```

Update `_execute_chain` to log start/stop:
```python
def _execute_chain(self, profile: Profile) -> None:
    had_error = False
    _log.info("Chain started: %s (%d steps)", profile.name, len(profile.steps))
    try:
        # ... existing code unchanged ...
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
```

Update `_execute_step` exception handler to log:
```python
        except Exception as exc:
            _log.warning("Step failed [%s]: %s", step.action, exc)
            self._state.set_status_message(f"Step failed: {step.action}")
            return False
```

- [ ] **Step 4: Run the new tests**

```bash
py -m pytest tests/test_action_runner.py -k "logs_warning or runner_busy" -v
```

Expected: both PASS.

- [ ] **Step 5: Run full suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add swiftmacro/action_runner.py tests/test_action_runner.py
git commit -m "feat: add ActionRunner logging and runner_busy lifecycle tests"
```

---

## Task 8: Add Logging to hotkeys, lock_loop, single_instance

**Files:**
- Modify: `swiftmacro/hotkeys.py`
- Modify: `swiftmacro/lock_loop.py`
- Modify: `swiftmacro/single_instance.py`

These are straightforward additions — no failing tests required since they're INFO/DEBUG/WARNING additions with no behavior change.

- [ ] **Step 1: Add logging to hotkeys.py**

Add import + logger at top:
```python
from swiftmacro.log import get_logger
_log = get_logger("hotkeys")
```

In `register_all()`, after each successful `keyboard.add_hotkey`:
```python
_log.info("Registered system hotkey: %s", combo)
```
After each failure:
```python
_log.warning("Failed to register system hotkey %s: %s", combo, exc)
```

In `unregister_all()`, in the except block:
```python
except Exception as exc:
    _log.debug("Could not remove hotkey %s (may not have been registered): %s", combo, exc)
```

In `refresh_profile_hotkeys()`, on conflict:
```python
_log.warning("Hotkey conflict detected for profile '%s': %s", profile.name, hk)
```
On success:
```python
_log.info("Registered profile hotkey %s for '%s'", profile.hotkey, profile.name)
```
On failure:
```python
_log.warning("Failed to register profile hotkey %s: %s", profile.hotkey, exc)
```

- [ ] **Step 2: Add logging to lock_loop.py**

Add import + logger at top:
```python
from swiftmacro.log import get_logger
_log = get_logger("lock_loop")
```

In `start()`:
```python
_log.debug("LockLoop started")
```

In the `run()` loop, after SetCursorPos fails (in except):
```python
_log.debug("SetCursorPos failed silently")
```

- [ ] **Step 3: Add logging to single_instance.py**

Add import at top (note: logging not yet configured when `acquire_single_instance` is called — log only after `configure_logging` runs in `app.py`; use a module-level logger that will pick up the handler once configured):
```python
from swiftmacro.log import get_logger
_log = get_logger("single_instance")
```

In `acquire_single_instance`, after detecting `already_running`:
```python
if already_running:
    _log.warning("Another SwiftMacro instance is already running")
```

- [ ] **Step 4: Run full test suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add swiftmacro/hotkeys.py swiftmacro/lock_loop.py swiftmacro/single_instance.py
git commit -m "feat: add logging to HotkeyManager, LockLoop, and SingleInstanceGuard"
```

---

## Task 9: Update Build Script

**Files:**
- Modify: `scripts/build_exe.ps1`

- [ ] **Step 1: Update build_exe.ps1**

Replace the entire file:

```powershell
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$iconPath = Join-Path $repoRoot "build\swiftmacro.ico"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $iconPath) | Out-Null

@'
from pathlib import Path
from swiftmacro.icon import ensure_windows_icon_file

source = Path(ensure_windows_icon_file())
target = Path("build/swiftmacro.ico")
target.write_bytes(source.read_bytes())
print(target)
'@ | py -

py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --noconsole `
    --name SwiftMacro `
    --specpath build `
    --icon "$iconPath" `
    --collect-submodules pystray `
    --collect-submodules PIL `
    --hidden-import PIL._tkinter_finder `
    swiftmacro.pyw
```

- [ ] **Step 2: Commit**

```bash
git add scripts/build_exe.ps1
git commit -m "feat: update build script for SwiftMacro EXE (swiftmacro.pyw, --noconsole)"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update README.md**

Replace all occurrences:
- `Mouse Lock Tool` → `SwiftMacro`
- `mouse_lock.py` → `swiftmacro.py`
- `mouse_lock.pyw` → `swiftmacro.pyw`
- `py -m mouse_lock` → `py -m swiftmacro`
- `pyw mouse_lock.pyw` → `pyw swiftmacro.pyw`
- `dist\MouseLock.exe` → `dist\SwiftMacro.exe`
- Title and description to reflect SwiftMacro

- [ ] **Step 2: Update AGENTS.md**

Replace all `mouse_lock` references with `swiftmacro` (package name, file paths, import examples).

- [ ] **Step 3: Update CLAUDE.md**

Replace all `mouse_lock` references and `~/.mouse_lock` paths with `swiftmacro` and `~/.swiftmacro`. Update the entry points section and all command examples.

- [ ] **Step 4: Run final test suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass, 0 failures.

- [ ] **Step 5: Final commit**

```bash
git add README.md AGENTS.md CLAUDE.md
git commit -m "docs: update README, AGENTS.md, CLAUDE.md for SwiftMacro rebranding"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Run full test suite with verbose output**

```bash
py -m pytest tests/ -v
```

Expected: all tests pass, 0 failures, 0 errors.

- [ ] **Step 2: Verify app launches with new branding**

```bash
py swiftmacro.py
```

Expected: window title "SwiftMacro Control Center", tray icon labeled "SwiftMacro".

- [ ] **Step 3: Verify profile directory**

After first launch, confirm `~/.swiftmacro/profiles.json` exists.

- [ ] **Step 4: Check success criteria from spec**

- [ ] All UI strings, window titles, tray labels show "SwiftMacro"
- [ ] Profile data stored in `~/.swiftmacro/profiles.json`
- [ ] Migration tested (task 6)
- [ ] Log file created at `~/.swiftmacro/swiftmacro.log` when running as `.pyw`
- [ ] `py -m pytest tests/ -q` passes with 0 failures
- [ ] WARNING/ERROR log calls covered by caplog tests
- [ ] `py swiftmacro.py` and `pyw swiftmacro.pyw` both launch
