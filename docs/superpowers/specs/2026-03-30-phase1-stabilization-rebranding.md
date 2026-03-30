# SwiftMacro — Phase 1: Stabilization & Rebranding
**Date:** 2026-03-30
**Status:** Draft v3
**Scope:** Rename project to SwiftMacro, add logging, fix silent failures, add critical test coverage

---

## 1. Overview

Phase 1 prepares the existing Mouse Lock codebase for public release under the name **SwiftMacro**. It does not add new user-facing features. Goals:

1. Rename all branding from "Mouse Lock" to "SwiftMacro"
2. Replace silent failures with visible feedback and structured logging
3. Add test coverage for the three most critical untested components
4. Fix known bugs found during code review

---

## 2. Rebranding

### 2.1 Constants (`mouse_lock/constants.py`)

| Old | New |
|-----|-----|
| `APP_NAME = "Mouse Lock"` | `APP_NAME = "SwiftMacro"` |
| `APP_ID = "MouseLock.Desktop"` | `APP_ID = "SwiftMacro.Desktop"` |
| `APP_MUTEX_NAME = "Local\\MouseLock.Desktop"` | `APP_MUTEX_NAME = "Local\\SwiftMacro.Desktop"` |
| `PROFILES_DIR = "~/.mouse_lock"` | `PROFILES_DIR = "~/.swiftmacro"` |
| `PROFILES_FILE = "~/.mouse_lock/profiles.json"` | `PROFILES_FILE = "~/.swiftmacro/profiles.json"` |

### 2.2 Package & Entry Points

| File | Change |
|------|--------|
| `mouse_lock/` directory | Rename to `swiftmacro/` |
| `mouse_lock.py` | Rename to `swiftmacro.py` |
| `mouse_lock.pyw` | Rename to `swiftmacro.pyw` |
| All `from mouse_lock.X import Y` in `swiftmacro/` | Update to `from swiftmacro.X import Y` |
| All `from mouse_lock.X import Y` in `tests/` | Update to `from swiftmacro.X import Y` |
| `mouse_lock/__main__.py` | Update module reference |

**Note:** Every import in `tests/` must also be updated to `from swiftmacro.X import Y`. Failing to do so will cause `ModuleNotFoundError` for the entire test suite.

### 2.3 UI Strings

- Window title: `"SwiftMacro Control Center"`
- Tray icon title: `"SwiftMacro"`
- Tray icon name: `"SwiftMacro"`
- Hero label in `main_window.py`: `APP_NAME` (already uses constant — no change needed)
- Hero body text (exact replacement): `"Profile-first desktop automation for gamers and power users — build reusable click, keypress, wait and lock flows."`

### 2.6 Documentation Files

| File | Change |
|------|--------|
| `README.md` | Update app name, all command references (`swiftmacro.py`, `swiftmacro.pyw`), EXE path (`dist\SwiftMacro.exe`) |
| `AGENTS.md` | Update all `mouse_lock` references to `swiftmacro`, update paths |
| `CLAUDE.md` | Update all branding references and file paths (`~/.swiftmacro`, `swiftmacro.py`, etc.) |

### 2.4 Build Script (`scripts/build_exe.ps1`)

Update the following strings inside `build_exe.ps1`:

| Old | New |
|-----|-----|
| Entry point argument (e.g. `mouse_lock.py` or `mouse_lock.pyw`) | `swiftmacro.pyw` |
| `--name MouseLock` | `--name SwiftMacro` |
| Output reference `dist\MouseLock.exe` | `dist\SwiftMacro.exe` |
| Any `mouse_lock` path references | `swiftmacro` |

### 2.5 Data Migration

On first launch after rename, `ProfileStore` must migrate existing profiles from `~/.mouse_lock/profiles.json` to `~/.swiftmacro/profiles.json` if the old path exists and the new path does not.

**Initialization order in `app.main()`** (must be respected):

1. `os.makedirs(PROFILES_DIR_EXPANDED, exist_ok=True)` — creates `~/.swiftmacro/` if it does not exist.
2. Configure logging (section 3.1) — file handler can now safely write to `~/.swiftmacro/`.
3. Instantiate `ProfileStore()` — migration may now log via the registered handlers.

**Migration logic inside `ProfileStore.__init__()`:**

1. If `~/.swiftmacro/profiles.json` does NOT exist AND `~/.mouse_lock/profiles.json` DOES exist:
   a. Copy old file to a temp path inside `~/.swiftmacro/` using `shutil.copy2`.
   b. Atomically rename temp path to `~/.swiftmacro/profiles.json` using `os.replace()`.
   c. Log INFO: `"Migrated profiles from ~/.mouse_lock to ~/.swiftmacro"`.
   d. On any exception: log ERROR with details; clean up temp file if it was created; continue startup with an empty profile list (do not re-raise).
2. Old file at `~/.mouse_lock/profiles.json` is left in place (not deleted) to allow rollback. Cleanup is deferred to Phase 2.
3. The "first run" INFO message (`"Profile directory initialized at ~/.swiftmacro"`) is emitted in `app.main()` when `os.makedirs` creates the directory for the first time. This is detected by checking whether the directory existed before the `makedirs` call. It is NOT emitted on subsequent runs.

---

## 3. Logging

Add a module-level logger to each key module using Python's standard `logging` library. No third-party dependency.

### 3.1 Logger Setup (`swiftmacro/log.py` — new file)

```python
import logging

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"swiftmacro.{name}")
```

**Root logger configuration in `app.main()`** — called before any other initialization, and after `~/.swiftmacro/` directory is created:

- **Production mode** (`sys.stdout is None` — true for any process where stdout is suppressed, including `.pyw`, `pythonw.exe`, and PyInstaller `--noconsole` builds):
  File handler → `~/.swiftmacro/swiftmacro.log`, level `INFO`, `RotatingFileHandler(maxBytes=1_000_000, backupCount=2)`.
- **Development mode** (all other cases, i.e. `sys.stdout is not None`):
  `logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")`.

The rule is simply: if `sys.stdout is None`, use file logging. The build script (section 2.4) must pass `--noconsole` to PyInstaller so the distributed EXE satisfies this condition.

**Directory guarantee:** `~/.swiftmacro/` is created by `app.main()` before logging is configured (see section 2.5 initialization order), preventing `FileNotFoundError` on first launch.

### 3.2 Log Calls Per Module

| Module | What to log |
|--------|-------------|
| `profile_store.py` | INFO: load/save/add/delete/import/export counts; WARNING: file not found, JSON parse error, atomic write failure |
| `action_runner.py` | INFO: chain start/stop/complete; WARNING: step validation failure, step execution exception |
| `hotkeys.py` | INFO: hotkey registered/unregistered; WARNING: registration failure, conflict detected |
| `app.py` | INFO: startup sequence steps, shutdown |
| `single_instance.py` | WARNING: second instance detected |
| `lock_loop.py` | DEBUG: cursor reposition (too noisy for INFO) |

---

## 4. Bug Fixes & Silent Failure Improvements

### 4.1 ProfileStore — corrupt file recovery
**Current:** `_load_from_disk()` catches all exceptions silently, returns `[]`.
**Fix:** Log a WARNING with the exception message. Behavior (return `[]`) stays the same.

### 4.2 ProfileStore — atomic write failure
**Current:** `_save_to_disk()` uses `os.replace()` with no error handling.
**Fix:** Wrap in `try/except`, log ERROR on failure, re-raise so callers can surface it. All callers of `ProfileStore` methods that trigger a save (e.g. `add_profile`, `delete_profile`, `update_profile`) must catch this exception and call `state.set_status_message("Save failed — check log for details")` rather than letting it propagate to the UI framework. No modal dialogs; status bar message is sufficient.

### 4.3 ActionRunner — step execution exceptions
**Current:** `_execute_step()` catches `Exception` silently, sets a status message.
**Fix:** Log WARNING with exception details before setting status message.

### 4.4 HotkeyManager — unregister errors
**Current:** `unregister_all()` silently ignores `keyboard.remove_hotkey()` failures.
**Fix:** Log DEBUG for each failure (expected for hotkeys that were never registered).

### 4.5 AppState — chain_lock atomicity
**Current:** `set_chain_lock(active, pos)` may acquire the lock separately for each field if not implemented carefully.
**Fix:** Implement `set_chain_lock` to acquire the lock exactly once, set both `_chain_lock_active` and `_chain_lock_pos` under that single acquisition, then release. Example:
```python
def set_chain_lock(self, active: bool, pos: tuple | None) -> None:
    with self._lock:
        self._chain_lock_active = active
        self._chain_lock_pos = pos
```
This ensures no observer can read `active=True` with `pos=None` between the two assignments.

---

## 5. Test Coverage

All tests use `unittest.mock` and `pytest`. No real OS calls (cursor, keyboard) in unit tests. File I/O tests use `tmp_path` pytest fixture for isolation.

### 5.1 `tests/test_action_runner.py` (expand existing)

| Test | What it covers |
|------|----------------|
| `test_run_profile_sets_runner_busy` | `runner_busy` becomes True during execution |
| `test_run_profile_clears_runner_busy_on_complete` | `runner_busy` cleared after chain finishes |
| `test_stop_interrupts_chain` | `stop()` interrupts a running chain via stop_event |
| `test_execute_step_move` | Dispatches `move` step to `cursor.set_cursor_pos` |
| `test_execute_step_click` | Dispatches `click` step to `cursor.click` |
| `test_execute_step_keypress` | Dispatches `keypress` step to `keyboard.press_and_release` |
| `test_execute_step_wait` | `wait` step respects stop_event |
| `test_execute_step_invalid_step_logs_warning` | Invalid step logs WARNING via Python logging |
| `test_run_profile_only_one_chain_at_a_time` | Second `run_profile()` while busy is a no-op |

### 5.2 `tests/test_profile_store.py` (expand existing)

| Test | What it covers |
|------|----------------|
| `test_add_profile_persists` | Added profile survives a reload from disk |
| `test_add_profile_enforces_max` | Adding beyond MAX_PROFILES raises ValueError |
| `test_delete_profile` | Delete removes profile and persists |
| `test_import_clears_conflicting_hotkeys` | Imported profile with conflicting hotkey gets hotkey cleared |
| `test_import_skips_invalid_profiles` | Invalid profiles are skipped, valid ones imported |
| `test_load_returns_empty_on_corrupt_file` | Corrupt JSON returns `[]` and logs WARNING via `caplog` |
| `test_duplicate_profile` | Duplicate gets new UUID and "(Copy)" name suffix |
| `test_export_then_import_roundtrip` | Export + re-import produces identical profiles |
| `test_migrate_profiles_on_first_launch` | If `~/.mouse_lock/profiles.json` exists and `~/.swiftmacro/profiles.json` does not, profiles are copied; logs INFO |
| `test_migrate_profiles_failure_leaves_no_partial_file` | If copy raises mid-migration, no partial file exists at destination; logs ERROR |

### 5.3 `tests/test_state.py` (expand existing)

| Test | What it covers |
|------|----------------|
| `test_set_get_active_profile_id` | Basic getter/setter roundtrip |
| `test_set_chain_lock_atomic` | Both fields readable atomically after `set_chain_lock(True, (x, y))` |
| `test_concurrent_state_access` | 10 threads read/write simultaneously — no deadlock within 5s |
| `test_stop_event_propagates` | `stop_event.set()` is observable from a second thread |

---

## 6. Files Changed

| File | Action |
|------|--------|
| `mouse_lock/` → `swiftmacro/` | Rename directory |
| `mouse_lock.py` → `swiftmacro.py` | Rename |
| `mouse_lock.pyw` → `swiftmacro.pyw` | Rename |
| `tests/*.py` | Update all `from mouse_lock.X` imports to `from swiftmacro.X` |
| `swiftmacro/constants.py` | Update APP_NAME, APP_ID, mutex, paths |
| `swiftmacro/log.py` | New file — logger factory |
| `swiftmacro/app.py` | Init directory + logging first, then all other init; add migration call |
| `swiftmacro/profile_store.py` | Add migration, logging, fix atomic write, fix corrupt-file logging |
| `swiftmacro/action_runner.py` | Add logging |
| `swiftmacro/hotkeys.py` | Add logging |
| `swiftmacro/lock_loop.py` | Add logging |
| `swiftmacro/single_instance.py` | Add logging |
| `swiftmacro/state.py` | Fix `set_chain_lock` atomicity |
| `swiftmacro/tray.py` | Update icon title/name |
| `swiftmacro/ui/main_window.py` | Update hardcoded strings |
| `tests/test_action_runner.py` | Expand with new tests |
| `tests/test_profile_store.py` | Expand with new tests |
| `tests/test_state.py` | Expand with new tests |
| `AGENTS.md` | Update all references |
| `README.md` | Update branding, commands |
| `CLAUDE.md` | Update branding, paths |
| `scripts/build_exe.ps1` | Update EXE name, entry point, output path |

---

## 7. Out of Scope for Phase 1

- New step types (Phase 2)
- Loop/Repeat feature (Phase 2)
- Profile limit increase (Phase 2)
- UI redesign (Phase 3)
- Installer (Phase 4)
- Cleanup of `~/.mouse_lock/` old data (Phase 2)
- Any Pro/Freemium features (future)

---

## 8. Success Criteria

- [ ] All UI strings, window titles, tray labels show "SwiftMacro"
- [ ] Profile data stored in `~/.swiftmacro/profiles.json`
- [ ] Existing `~/.mouse_lock/profiles.json` automatically migrated on first run (atomic, safe on failure)
- [ ] Log file created at `~/.swiftmacro/swiftmacro.log` when running as `.pyw` or EXE
- [ ] `py -m pytest tests/ -q` passes with 0 failures
- [ ] All WARNING/ERROR log calls in section 3.2 are exercised by at least one test that asserts the log message is emitted via `pytest`'s `caplog` fixture; migration INFO logs covered by `test_migrate_profiles_on_first_launch`
- [ ] `py swiftmacro.py` and `pyw swiftmacro.pyw` both launch the app
- [ ] `dist\SwiftMacro.exe` produced by `scripts/build_exe.ps1`
