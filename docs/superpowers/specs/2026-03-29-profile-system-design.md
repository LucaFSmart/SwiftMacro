# Profile-Based Macro System — Design Spec
**Date:** 2026-03-29
**Status:** Approved (rev 3 — addresses rev 2 review gaps)

---

## Overview

Extend the Mouse Lock Tool from a single-position utility into a profile-based macro system. Users create up to 5 profiles, each containing an action chain (sequence of steps like move, click, repeated click, keypress, wait, cursor lock). Profiles are built via a visual step-builder in the UI, triggered via per-profile hotkeys or a global "run active profile" hotkey, and persisted to a JSON file.

---

## Tech Stack (additions to existing)

| Library | Purpose |
|---|---|
| `uuid` (stdlib) | Generate unique profile IDs |
| `json` (stdlib) | Profile persistence |
| `time` (stdlib) | Wait steps, timing |

No new external dependencies. Mouse clicks use `ctypes` Win32 API (`mouse_event`). Keypresses use `keyboard` library (already installed).

---

## Package Structure

Refactor the existing single-file `mouse_lock.py` into a package:

```
mouse_lock/
  __main__.py          # Entry point: from mouse_lock.app import main; main()
  constants.py         # All constants (hotkeys, intervals, icon size, max profiles)
  dpi.py               # init_dpi_awareness()
  state.py             # AppState dataclass with thread-safe methods
  models.py            # Profile, ActionStep dataclasses
  profile_store.py     # Load/save profiles from/to JSON
  action_runner.py     # Execute action chains in a worker thread
  cursor.py            # Win32 cursor ops: get_pos, set_pos, click, repeated_click
  lock_loop.py         # LockLoop (extended: defers to chain lock when active)
  hotkeys.py           # HotkeyManager (extended for profile hotkeys)
  tray.py              # TrayManager (minimal changes)
  icon.py              # create_tray_icon()
  app.py               # main(), shutdown(), wiring
  ui/
    __init__.py
    main_window.py     # Main window with profile list, status, buttons
    step_builder.py    # Dialog for editing an action chain visually
tests/
  test_models.py
  test_profile_store.py
  test_action_runner.py
  test_cursor.py
  test_state.py        # updated from existing
  test_hotkeys.py      # updated from existing
  test_lock_loop.py    # existing, path updated
  test_dpi.py          # existing, path updated
  test_icon.py         # existing, path updated
```

The existing `mouse_lock.py` is replaced by the package. Launch with `py -m mouse_lock`.

---

## Data Model (`models.py`)

```python
@dataclass
class ActionStep:
    action: str      # "move", "click", "repeat_click", "keypress", "wait", "lock"
    params: dict     # action-specific parameters (see below)

@dataclass
class Profile:
    id: str                        # UUID string, auto-generated
    name: str                      # user-facing name, e.g. "Farm Spot 1"
    hotkey: str | None             # e.g. "ctrl+alt+1" or None (no dedicated hotkey)
    steps: list[ActionStep]        # ordered action chain
```

### Action Types and Parameters

| Action | Params | Description |
|---|---|---|
| `move` | `{"x": int, "y": int}` | Move cursor to position |
| `click` | `{"button": "left"\|"right"\|"middle", "x": int, "y": int}` | Single click at position |
| `repeat_click` | `{"button": "left"\|"right"\|"middle", "x": int, "y": int, "count": int, "interval_ms": int}` | N clicks with interval; checks `stop_event` between each click for fast interruption |
| `keypress` | `{"key": str}` | Tap key or combo via `keyboard.press_and_release()`, e.g. "enter", "ctrl+c" |
| `wait` | `{"ms": int}` | Pause for N milliseconds via `stop_event.wait(timeout=ms/1000)` |
| `lock` | `{"x": int, "y": int, "duration_ms": int}` | Lock cursor to position for duration. `duration_ms > 0`: lock for that duration then continue chain. `duration_ms = 0`: lock until chain is stopped (no subsequent steps execute — this is a terminal step). |

**Lock step vs LockLoop interaction:** When an action chain `lock` step is active, the ActionRunner sets `AppState.chain_lock_active = True` with the chain's target position. The `LockLoop` main loop changes to:

1. If `chain_lock_active` is True: use `chain_lock_pos` as the target (ignoring `saved_pos` and `lock_active`).
2. Else if `lock_active` is True and `saved_pos` is not None: use `saved_pos` as the target (existing behavior).
3. Else: do nothing this iteration.

Both cases use `SetCursorPos` at `LOCK_INTERVAL_MS` interval. When the chain ends or is stopped, ActionRunner resets `chain_lock_active = False` and `LockLoop` resumes case 2/3.

---

## Profile Store (`profile_store.py`)

- Loads/saves `list[Profile]` from/to `~/.mouse_lock/profiles.json` (stable location independent of working directory)
- On load, creates `~/.mouse_lock/` directory if it does not exist (`os.makedirs(..., exist_ok=True)`)
- On first launch, `profiles.json` does not exist → returns empty list
- Max 5 profiles enforced at the store level (add_profile raises if full)
- File is written atomically: write to temp file, then rename
- Thread-safe: all public methods acquire a lock

---

## Action Runner (`action_runner.py`)

Executes an action chain in a **dedicated daemon thread**. One chain at a time — if a chain is already running, new triggers are ignored.

```python
class ActionRunner:
    def __init__(self, state: AppState) -> None
    def run_profile(self, profile: Profile) -> None   # starts chain in thread
    def stop(self) -> None                             # stops current chain
    def is_running(self) -> bool
```

- Each step is dispatched to the appropriate `cursor.py` or `keyboard` function
- Between steps, checks `stop_event` so chains can be interrupted (ESC hotkey)
- `wait` steps use `stop_event.wait(timeout=ms/1000)` for fast interruption
- `repeat_click` passes `stop_event` to `cursor.repeat_click()` which checks the event between each click
- `lock` steps set `AppState.chain_lock_active = True` and `chain_lock_pos = (x, y)`. The ActionRunner does NOT run its own mini lock-loop — instead, the existing `LockLoop` thread sees the `chain_lock_active` flag and handles cursor correction at `LOCK_INTERVAL_MS`. The ActionRunner simply waits: `stop_event.wait(timeout=duration_ms/1000)` for timed locks, or `stop_event.wait()` (no timeout) for `duration_ms=0`
- On chain end (normal or interrupted), always resets `chain_lock_active = False`
- **Param validation:** Before executing each step, validates that all required params are present and have correct types. Invalid steps are skipped with status "Step N: invalid params"
- Status messages are set on `AppState` during execution: "Running: Farm Spot 1", "Step 3/5: click", "Done"

---

## Cursor Operations (`cursor.py`)

All mouse operations via Win32 `ctypes`. No `pyautogui`.

```python
def get_cursor_pos() -> tuple[int, int] | None
def set_cursor_pos(x: int, y: int) -> bool
def click(button: str, x: int, y: int) -> bool          # move + mouse_event down + up
def repeat_click(button: str, x: int, y: int, count: int, interval_ms: int, stop_event: Event) -> int  # returns number of clicks completed
```

Mouse clicks use `user32.mouse_event` with `MOUSEEVENTF_LEFTDOWN/LEFTUP`, `RIGHTDOWN/RIGHTUP`, `MIDDLEDOWN/MIDDLEUP`. Position is set via `SetCursorPos` before each click.

---

## AppState Changes (`state.py`)

Extend AppState with profile-related fields:

```python
@dataclass
class AppState:
    # --- existing fields ---
    saved_pos: tuple[int, int] | None
    lock_active: bool
    stop_event: threading.Event
    hotkey_errors: list[str]
    status_message: str
    # --- new fields ---
    active_profile_id: str | None     # ID of selected profile in UI
    runner_busy: bool                 # True while ActionRunner is executing
    chain_lock_active: bool           # True when an action chain lock step is running
    chain_lock_pos: tuple[int, int] | None  # Position the chain lock step is holding
    _lock: threading.Lock
```

New thread-safe methods:
- `get_active_profile_id() / set_active_profile_id(id)`
- `get_runner_busy() / set_runner_busy(busy)`
- `get_chain_lock() / set_chain_lock(active, pos)` — used by ActionRunner and LockLoop

---

## HotkeyManager Changes (`hotkeys.py`)

Extended to handle dynamic profile hotkeys:

- Constructor: `HotkeyManager(state, root, action_runner, profile_store)` — extended from `(state, root)` to include ActionRunner and ProfileStore references
- Still registers the existing 4 system hotkeys (save, move, toggle, exit)
- Adds a new global hotkey: `CTRL+ALT+R` — "Run active profile" (looks up `active_profile_id` from state, fetches profile from store, calls `action_runner.run_profile()`)
- Adds a new global hotkey: `CTRL+ALT+X` — "Stop running chain" (calls `action_runner.stop()` without exiting the app). If no chain is running, this is a no-op
- Registers per-profile hotkeys when profiles are loaded or changed
- `refresh_profile_hotkeys(profiles)` — unregisters old profile hotkeys, registers new ones. During the brief window between unregister and re-register, old hotkeys are dead and new ones not yet live — this is acceptable (sub-second gap)
- **Hotkey conflict detection:** `refresh_profile_hotkeys` rejects profile hotkeys that collide with system hotkeys or other profile hotkeys. Conflicts are reported in `hotkey_errors` and the conflicting profile hotkey is skipped (profile still works via UI "Run" button)
- Profile hotkey callbacks call `action_runner.run_profile(profile)`

---

## UI Changes

### Main Window (`ui/main_window.py`)

Window grows to ~500x450. Layout:

```
┌─────────────────────────────────────┐
│  Saved Position: X: 123, Y: 456    │
│  Lock Status: Unlocked              │
│  Status: Ready                      │
│  [Save Position] [Move Now] [Lock]  │
│─────────────────────────────────────│
│  Profiles:                          │
│  ┌─────────────────────────────────┐│
│  │ ► Farm Spot 1    [Ctrl+Alt+1]  ││
│  │   Doppelklick    [Ctrl+Alt+2]  ││
│  │   Quick Tap      [—]           ││
│  └─────────────────────────────────┘│
│  [Add] [Edit] [Delete] [Run]       │
│─────────────────────────────────────│
│  [Hotkey errors if any]            │
└─────────────────────────────────────┘
```

- Profile list is a `tk.Listbox` (max 5 items)
- `►` marker shows the active profile
- Single-click selects = sets active profile
- Buttons: Add (opens step builder), Edit (opens step builder with data), Delete, Run (executes active profile)
- "Run" button and `CTRL+ALT+R` do the same thing: run the active profile's chain
- **Profile save wiring:** When the step builder returns a saved profile, `main_window` calls `profile_store.save()` then `hotkey_mgr.refresh_profile_hotkeys(profiles)`. Same flow for Delete. The `main_window` holds references to both `profile_store` and `hotkey_mgr` (passed in constructor).

### Step Builder Dialog (`ui/step_builder.py`)

A `tk.Toplevel` modal dialog:

```
┌─────────────────────────────────────┐
│  Profile Name: [_______________]    │
│  Hotkey (optional): [__________]    │
│                                     │
│  Steps:                             │
│  ┌─────────────────────────────────┐│
│  │ 1. move → (500, 300)           ││
│  │ 2. click left → (500, 300)     ││
│  │ 3. wait 150ms                  ││
│  │ 4. click left → (500, 300)     ││
│  └─────────────────────────────────┘│
│  [▲] [▼] [Remove Step]             │
│                                     │
│  Add Step:                          │
│  Action: [▼ move        ]          │
│  Params: [x: ___] [y: ___]         │
│  [+ Add Step]                       │
│                                     │
│  [Save Profile] [Cancel]           │
└─────────────────────────────────────┘
```

- Dropdown selects action type; param fields change dynamically per action type
- Steps list is a `tk.Listbox` with formatted step descriptions
- Up/Down buttons reorder steps
- "Save Profile" validates (name non-empty, at least 1 step, max `MAX_STEPS` steps, hotkey not conflicting with system hotkeys or other profiles, shows advisory warning if steps exist after a terminal `lock` with `duration_ms=0` — warning does not block save, user may intentionally keep dead steps for later reordering) and returns the profile to main_window
- **Pick Position UX:** For actions requiring x/y (move, click, repeat_click, lock), a "Pick Position" button appears next to the coordinate fields. Clicking it starts a 3-second countdown in the button text ("3...", "2...", "1...") via `root.after()`, then reads `GetCursorPos` and fills x/y fields. This gives the user time to move the cursor to the desired position.
- `+ Add Step` button is disabled when step count reaches `MAX_STEPS`

---

## Constants (`constants.py`)

```python
# System hotkeys (existing)
HOTKEY_SAVE       = "ctrl+alt+s"
HOTKEY_MOVE       = "ctrl+alt+m"
HOTKEY_TOGGLE     = "ctrl+alt+t"
HOTKEY_EXIT       = "ctrl+alt+esc"

# New
HOTKEY_RUN        = "ctrl+alt+r"      # run active profile
HOTKEY_STOP_CHAIN = "ctrl+alt+x"      # stop running chain without exiting app

# Intervals
LOCK_INTERVAL_MS  = 15
UI_POLL_MS        = 200
ICON_SIZE         = 64

# Limits
MAX_PROFILES      = 5
MAX_STEPS         = 50            # max action steps per profile

# File paths
PROFILES_DIR      = "~/.mouse_lock"           # expanded via os.path.expanduser() at runtime
PROFILES_FILE     = "~/.mouse_lock/profiles.json"  # expanded via os.path.expanduser() at runtime
```

---

## Startup Order

`main()` in `app.py`:

1. `init_dpi_awareness()`
2. Create `AppState`
3. Create `tk.Tk()` root
4. Load profiles from `profile_store`
5. Create `ActionRunner(state)`
6. Initialize `TrayManager` → set `tray_available`
7. Build UI (main_window with profile list)
8. If `tray_available`: `root.withdraw()`
9. Start `LockLoop`
10. Create `HotkeyManager`, register system + profile hotkeys
11. Wire `shutdown()`, set `_shutdown_ref[0]` — **must happen before step 12**
12. `hotkey_mgr.start()` — starts after `_shutdown_ref` is populated, preventing race where CTRL+ALT+ESC fires before shutdown is wired
13. `root.mainloop()`

---

## Shutdown

Same pattern as before. Additionally:
- `action_runner.stop()` — interrupts any running chain
- Profile hotkeys are unregistered along with system hotkeys
- **ESC during chain:** CTRL+ALT+ESC still triggers full app shutdown even mid-chain. `shutdown()` calls `action_runner.stop()` first, then proceeds with normal teardown. CTRL+ALT+X is for stopping chains without exiting.

---

## Thread Safety

| Caller | Target | Mechanism |
|---|---|---|
| Profile hotkey → ActionRunner | `run_profile()` acquires internal lock | Only one chain at a time |
| ActionRunner → AppState | Locked getters/setters | Always |
| ActionRunner → cursor.py | Win32 calls inline on runner thread | Safe |
| Step builder → ProfileStore | Store has its own lock | Always |
| UI → ProfileStore | Reads on main thread | Through store lock |
| HotkeyManager refresh | Unregister old + register new | Called on main (Tk) thread during profile save; `keyboard.add_hotkey`/`remove_hotkey` are thread-safe per library docs |

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Profile hotkey registration fails | Error in `hotkey_errors`, profile works via UI "Run" button |
| Action step fails (click, move) | Status message "Step N failed", chain continues to next step |
| Chain already running | New trigger ignored, status "Already running" |
| profiles.json corrupted | Log warning, start with empty profile list |
| profiles.json write fails | Status message "Save failed", profiles remain in memory |
| Max profiles reached | "Add" button disabled, status "Max 5 profiles" |

---

## Migration from Single File

The existing `mouse_lock.py` is replaced. All existing functionality is preserved:
- Save/Move/Toggle Lock buttons and hotkeys work exactly as before
- ESC emergency exit still works
- Tray behavior unchanged
- The only user-visible change: launch command becomes `py -m mouse_lock` instead of `py mouse_lock.py`

---

## Out of Scope

- Profile groups or folders
- Conditional logic in chains (if/else)
- Loop steps (repeat chain N times)
- Recording mode (capture mouse movements)
- Import/Export of profiles
- More than 5 profiles
