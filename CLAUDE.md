# SwiftMacro – CLAUDE.md

## Commands

```bash
# Install dependencies
py -m pip install -r requirements.txt

# Run (with console)
py swiftmacro.py
py -m swiftmacro

# Run (no console window – production mode)
pyw swiftmacro.pyw

# Tests
py -m pytest tests/ -q

# Build EXE (PowerShell)
py -m pip install pyinstaller
.\scripts\build_exe.ps1
# Output: dist\SwiftMacro.exe
```

## Architecture

```
swiftmacro/
  app.py              # Startup/shutdown wiring – assembles all components
  models.py           # ActionStep, Profile dataclasses + validation
  state.py            # AppState – thread-safe shared state
  profile_store.py    # JSON persistence (~/.swiftmacro/profiles.json), atomic writes
  action_runner.py    # Executes profile action chains in a background thread
  hotkeys.py          # HotkeyManager – global hotkeys + conflict detection
  lock_loop.py        # LockLoop – keeps cursor pinned during chain_lock_active
  tray.py             # TrayManager – pystray system tray icon
  single_instance.py  # Windows mutex guard (one app instance only)
  cursor.py           # Win32 cursor operations (ctypes)
  dpi.py              # DPI awareness init (SetProcessDpiAwareness)
  icon.py             # Generated app icon (PIL) for window + tray
  constants.py        # All magic values in one place
  ui/
    main_window.py    # Primary Tkinter window (980×720, profile-centric layout)
    step_builder.py   # StepBuilderDialog – modal profile/step editor
    theme.py          # Dark theme colors, fonts, ttk styles
```

**Entry point:** `app.main()` ← called by `swiftmacro.py` and `swiftmacro.pyw`

## Key Constants (`swiftmacro/constants.py`)

| Constant | Value | Notes |
|---|---|---|
| `MAX_PROFILES` | 5 | Hard cap on stored profiles |
| `MAX_STEPS` | 50 | Hard cap per profile |
| `PROFILES_FILE` | `~/.swiftmacro/profiles.json` | Persisted across runs |
| `HOTKEY_RUN` | `ctrl+alt+r` | Run active profile |
| `HOTKEY_STOP_CHAIN` | `ctrl+alt+x` | Stop running chain |
| `HOTKEY_EXIT` | `ctrl+alt+esc` | Emergency exit |
| `UI_POLL_MS` | 200 | Tkinter polling interval |
| `LOCK_INTERVAL_MS` | 15 | Cursor re-pin interval in LockLoop |

## Action Steps

Valid actions: `move`, `click`, `repeat_click`, `keypress`, `wait`, `lock`

`lock` step with `duration_ms=0` pins the cursor permanently until the chain is stopped.

## Non-obvious Patterns

- **Tray close behavior:** `WM_DELETE_WINDOW` calls `root.withdraw()` (hides), not destroy. Only exits if tray is unavailable.
- **Single instance:** Uses a named Windows mutex (`Local\SwiftMacro.Desktop`). Second launch silently exits.
- **`_shutdown_ref`:** A `list[callable]` singleton in `hotkeys.py` shared by `tray.py` and `main_window.py` to avoid circular imports.
- **Hotkey refresh:** After every profile add/edit/delete/import, call `hotkey_mgr.refresh_profile_hotkeys(profile_store.load())`.
- **Import conflict resolution:** On import, conflicting hotkeys in incoming profiles are cleared (not rejected).
- **DPI:** `init_dpi_awareness()` must be called before any window or coordinate operation.

## Requirements

- Windows 10/11, Python 3.10+
- No admin rights needed
- `keyboard`, `pystray`, `Pillow` (runtime); `pytest` (tests)
