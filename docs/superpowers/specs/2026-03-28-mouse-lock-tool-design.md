# Mouse Position Lock Tool — Design Spec
**Date:** 2026-03-28
**Status:** Approved (rev 4)

---

## Overview

A lightweight Windows desktop utility that lets the user save a mouse position and instantly warp the cursor back to it via hotkey. Optionally locks the cursor to that position continuously. Runs in the system tray with a minimal Tkinter UI.

---

## Tech Stack

| Library | Purpose |
|---|---|
| `tkinter` | UI (stdlib) |
| `ctypes` (stdlib) | Win32 `SetCursorPos` / `GetCursorPos` — all cursor operations |
| `keyboard` | Global hotkey registration |
| `pystray` | System tray icon and menu |
| `Pillow` | Generate tray icon at runtime |

`pyautogui` is **not used**. All cursor positioning (both one-shot and lock loop) uses `ctypes` Win32 APIs directly. This avoids a dependency with known DPI-scaling issues and antivirus false-positive risk.

---

## DPI Awareness

The process must declare itself DPI-aware so that `SetCursorPos` / `GetCursorPos` and Tkinter operate in the same physical pixel coordinate space. Use best-effort cascading initialization — try newer APIs first, fall back gracefully, never crash:

```python
def init_dpi_awareness():
    try:
        # Windows 8.1+ preferred API
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            # Windows Vista+ fallback
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # silently continue; DPI mismatch may occur on rare configs
```

This is called first thing in `main()`, before Tkinter or tray initialization.

---

## Architecture

Four concurrent layers:

1. **Main thread** — Tkinter UI event loop (`root.mainloop()`)
2. **Hotkey thread** — `keyboard` library blocking loop (daemon thread)
3. **Lock loop thread** — polls every `LOCK_INTERVAL_MS` ms, calls `SetCursorPos` if lock is active (daemon thread)
4. **Tray thread** — `pystray` icon; all Tkinter calls routed via `root.after()`

All shared state is protected by a single `threading.Lock`.

---

## Shared State (`AppState`)

```python
@dataclass
class AppState:
    saved_pos: tuple[int, int] | None  # (x, y) or None if not yet saved
    lock_active: bool                   # whether cursor lock is running
    stop_event: threading.Event         # set to signal full shutdown
    hotkey_errors: list[str]            # registration errors, displayed in UI
    status_message: str                 # transient status shown in UI (cleared by next poll)
    _lock: threading.Lock               # protects all mutable fields above
```

All reads and writes go through getter/setter methods that acquire `_lock`. No direct field access from outside `AppState`.

---

## Components

### `HotkeyManager`
- Registers four global hotkeys on startup; each registration is wrapped in its own try/except
- On failure, the error message is appended to `AppState.hotkey_errors` (type `list[str]`); the app continues without that hotkey
- Runs `keyboard.wait()` in a daemon thread
- Unregisters all successfully registered hotkeys on shutdown

**Hotkeys:**

| Hotkey | Action | Thread note |
|---|---|---|
| CTRL+ALT+S | Save current cursor position | Calls `AppState.set_saved_pos()` inline on hotkey thread (locked); then `root.after()` to refresh UI |
| CTRL+ALT+M | Move cursor to saved position (one-shot) | Calls `ctypes.windll.user32.SetCursorPos(x, y)` **inline on hotkey thread** — no `root.after()` needed; `SetCursorPos` is not a Tkinter call |
| CTRL+ALT+T | Toggle lock on/off | Calls `AppState.toggle_lock()` inline on hotkey thread (locked) |
| CTRL+ALT+ESC | Emergency exit | Calls `root.after(0, shutdown)` |

> **Note:** The exit hotkey is `CTRL+ALT+ESC`, not bare `ESC`. Bare `ESC` is too aggressive as a global hotkey (it would interrupt other applications). The chord is an intentional safety choice.

### `LockLoop`
- Daemon thread
- Each iteration: if `lock_active` is True and `saved_pos` is set, calls `ctypes.windll.user32.SetCursorPos(x, y)`; `SetCursorPos` failures are silently ignored (non-critical)
- Uses `stop_event.wait(timeout=LOCK_INTERVAL_MS / 1000.0)` for sleeping — this allows fast exit when `stop_event` is set, avoiding up to 15ms blocking delay during shutdown
- Thread is **not joined** during shutdown (it is a daemon thread; it exits when the process exits or `stop_event` is set at next wait cycle)
- Constant: `LOCK_INTERVAL_MS = 15`

### `TrayManager`
- Creates a 64×64 tray icon at runtime using Pillow (crosshair/target symbol, dark background)
- If tray creation fails (e.g. unsupported environment), a module-level bool `tray_available` is set to `False` at startup and never mutated again; the app continues without tray (see Error Handling). Because `tray_available` is write-once at startup, it does not need lock protection.
- Right-click menu uses `pystray.MenuItem` with a `checked` lambda for the Toggle Lock item, so its visual state reflects `lock_active` without rebuilding the menu:
  ```python
  pystray.MenuItem("Lock", toggle_lock_action, checked=lambda item: state.get_lock_active())
  ```
- Menu items:
  - **Show UI** — `root.after(0, show_window)`
  - **Lock** (checkable) — flips `lock_active`
  - **Exit** — `root.after(0, shutdown)`
- Double-click: `root.after(0, show_window)`

**`show_window` function:** Called from tray thread via `root.after(0, show_window)`. On the main thread it calls `root.deiconify()` then `root.lift()` then `root.focus_force()` to restore and bring the window to the foreground.

### `AppUI`
- Small Tkinter window (non-resizable, ~300×200px)
- Displays:
  - Saved position: `X: 123, Y: 456` (or `Not set` if none)
  - Lock status: `Lock Active` / `Unlocked`
  - Transient status message from `AppState.status_message` (e.g. `Position saved`, `Move failed`, `Tray unavailable`, `Hotkey failed: ...`); updated every poll cycle
  - Hotkey error banner: shown only if `hotkey_errors` is non-empty; lists each error on a separate line
- Buttons: **Save Position**, **Move Now**, **Toggle Lock**
- Polls `AppState` every `UI_POLL_MS` ms via `root.after()`; the poll callback checks `stop_event.is_set()` at the top — if set, it does **not** reschedule itself (prevents `TclError` from updating destroyed widgets)
- `WM_DELETE_WINDOW` behavior depends on tray availability:
  - Tray available: `root.withdraw()` (minimize to tray)
  - Tray unavailable: `shutdown()` (close button exits the app)
- Startup visibility: `root.withdraw()` is called **only if tray initialization succeeds**. If tray fails, the window remains visible from startup so the user can still access the tool.

---

## Startup Order

`main()` must initialize components in this exact order to avoid incorrect behavior:

1. `init_dpi_awareness()` — before any UI or cursor work
2. Create `AppState`
3. Create Tkinter `root` (do **not** call `root.mainloop()` yet)
4. Initialize `TrayManager` — sets module-level `tray_available`
5. If `tray_available`: `root.withdraw()` (start hidden); else: leave window visible, set `status_message = "Tray unavailable"`
6. Start `LockLoop` thread
7. Start `HotkeyManager` thread
8. `root.mainloop()` — blocks until shutdown

---

## Shutdown

Single `shutdown()` function — the only full-exit path. Guards against double invocation:

```python
def shutdown():
    if state.stop_event.is_set():
        return          # already shutting down, no-op
    state.stop_event.set()
    # Unregister hotkeys (best-effort, errors ignored)
    hotkey_manager.unregister_all()
    # Stop tray
    if tray_available:
        tray.stop()
    # Destroy UI on main thread
    root.after(0, root.destroy)
```

Called via `root.after(0, shutdown)` from:
- CTRL+ALT+ESC hotkey callback
- Tray "Exit" menu item
- `WM_DELETE_WINDOW` when tray is unavailable

Never called on window close when tray is available (that path calls `root.withdraw()` instead).

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Hotkey registration fails | Error appended to `AppState.hotkey_errors` (`list[str]`); displayed as a warning label in UI; app continues without that hotkey |
| "Save Position" | Sets `status_message = "Position saved"` |
| "Move Now" with no saved position | Sets `status_message = "No position saved"`, no move |
| "Move Now" and `SetCursorPos` fails | Sets `status_message = "Move failed"` |
| `SetCursorPos` fails in lock loop | Silently ignored; next iteration retries (lock loop is high-frequency, no UI update) |
| Tray creation fails | Module-level `tray_available = False` set at startup; window stays visible; `WM_DELETE_WINDOW` rewired to `shutdown()` so close button exits |
| `shutdown()` called twice | Second call is a no-op (guarded by `stop_event.is_set()` check) |
| UI poll fires after `root.destroy()` | Poll callback checks `stop_event.is_set()` before rescheduling; if set, it returns without touching widgets |

---

## Constants (top of script)

```python
HOTKEY_SAVE      = "ctrl+alt+s"
HOTKEY_MOVE      = "ctrl+alt+m"
HOTKEY_TOGGLE    = "ctrl+alt+t"
HOTKEY_EXIT      = "ctrl+alt+esc"
LOCK_INTERVAL_MS = 15
UI_POLL_MS       = 200
ICON_SIZE        = 64
```

---

## Thread Safety Summary

| Caller | Target | Mechanism |
|---|---|---|
| Tray thread → Tkinter | `root.after()` | Always |
| Hotkey callbacks → Tkinter | `root.after()` | Always (except `SetCursorPos` in CTRL+ALT+M — not a Tkinter call, safe inline) |
| Lock loop → `AppState` | `AppState` locked methods | Always |
| UI thread → `AppState` | `AppState` locked getters | Always |
| `shutdown()` re-entry | `stop_event.is_set()` guard | Always |
| UI poll during shutdown | `stop_event.is_set()` check in poll callback | Always |

---

## Files

```
mouse_lock.py       # full application (~350–450 lines)
requirements.txt    # keyboard, pystray, Pillow
README.md           # setup and usage instructions
```

---

## Out of Scope

- Multi-slot position storage
- Configurable hotkeys via UI
- Non-Windows support
- Persistence of saved position across restarts
