# Profile-Based Macro System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the single-file mouse lock tool into a package and add a profile-based macro system with action chains, visual step builder, and per-profile hotkeys.

**Architecture:** Existing `mouse_lock.py` is split into a `mouse_lock/` package with one module per concern. New modules (`models`, `profile_store`, `action_runner`, `cursor`, `ui/`) implement the profile system. All cross-thread communication goes through `AppState` locked getters/setters. `ActionRunner` delegates cursor locking to the existing `LockLoop` via a `chain_lock_active` flag.

**Tech Stack:** Python 3.10+, tkinter, ctypes (Win32 API), keyboard, pystray, Pillow, pytest

---

## File Structure

### Package: `mouse_lock/`

| File | Responsibility | Source |
|---|---|---|
| `__main__.py` | Entry point: `from mouse_lock.app import main; main()` | New |
| `constants.py` | All constants (hotkeys, intervals, limits, paths) | Extract from `mouse_lock.py` |
| `dpi.py` | `init_dpi_awareness()` | Extract from `mouse_lock.py` |
| `state.py` | `AppState` dataclass + `make_state()` factory | Extract + extend from `mouse_lock.py` |
| `models.py` | `ActionStep`, `Profile` dataclasses | New |
| `cursor.py` | `get_cursor_pos`, `set_cursor_pos`, `click`, `repeat_click` | Partly extracted from `HotkeyManager._get_cursor_pos` + new |
| `profile_store.py` | `ProfileStore` — load/save profiles to JSON | New |
| `action_runner.py` | `ActionRunner` — execute action chains in worker thread | New |
| `lock_loop.py` | `LockLoop` — extended with chain_lock_active support | Extract + extend from `mouse_lock.py` |
| `hotkeys.py` | `HotkeyManager` — extended with profile + run/stop hotkeys | Extract + extend from `mouse_lock.py` |
| `tray.py` | `TrayManager`, `show_window()` | Extract from `mouse_lock.py` |
| `icon.py` | `create_tray_icon()` | Extract from `mouse_lock.py` |
| `app.py` | `main()`, `make_shutdown()`, `_shutdown_ref`, wiring | Extract + extend from `mouse_lock.py` |
| `ui/__init__.py` | Empty package marker | New |
| `ui/main_window.py` | `MainWindow` — expanded Tkinter UI with profile list | Rewrite from `AppUI` in `mouse_lock.py` |
| `ui/step_builder.py` | `StepBuilderDialog` — modal dialog for editing profiles | New |

### Tests: `tests/`

| File | Tests |
|---|---|
| `tests/conftest.py` | Shared fixtures (`stop_event`, `make_state`) |
| `tests/test_models.py` | ActionStep, Profile dataclasses + serialization |
| `tests/test_profile_store.py` | Load, save, max profiles, corruption handling |
| `tests/test_cursor.py` | get_cursor_pos, set_cursor_pos, click, repeat_click |
| `tests/test_action_runner.py` | Chain execution, interruption, param validation |
| `tests/test_state.py` | All AppState methods (migrated + new) |
| `tests/test_lock_loop.py` | LockLoop behavior (migrated + chain_lock) |
| `tests/test_hotkeys.py` | HotkeyManager (migrated + profile hotkeys) |
| `tests/test_dpi.py` | DPI awareness (migrated) |
| `tests/test_icon.py` | Tray icon generation (migrated) |

---

## Task 1: Package scaffold and constants

Extract constants into `mouse_lock/constants.py`, create package entry point, verify existing app still conceptually works at import level.

**Files:**
- Create: `mouse_lock/__init__.py`
- Create: `mouse_lock/__main__.py`
- Create: `mouse_lock/constants.py`

- [ ] **Step 1: Create package directory and `__init__.py`**

```bash
mkdir -p mouse_lock
```

Create `mouse_lock/__init__.py` — empty file.

- [ ] **Step 2: Create `constants.py`**

Create `mouse_lock/constants.py`:

```python
"""All application constants."""

# System hotkeys
HOTKEY_SAVE = "ctrl+alt+s"
HOTKEY_MOVE = "ctrl+alt+m"
HOTKEY_TOGGLE = "ctrl+alt+t"
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
PROFILES_DIR = "~/.mouse_lock"
PROFILES_FILE = "~/.mouse_lock/profiles.json"

# All system hotkeys for conflict detection
SYSTEM_HOTKEYS = frozenset({
    HOTKEY_SAVE, HOTKEY_MOVE, HOTKEY_TOGGLE, HOTKEY_EXIT,
    HOTKEY_RUN, HOTKEY_STOP_CHAIN,
})
```

- [ ] **Step 3: Create `__main__.py`**

Create `mouse_lock/__main__.py`:

```python
from mouse_lock.app import main

main()
```

(This will not run yet — `app.py` doesn't exist. That's expected.)

- [ ] **Step 4: Write test to verify constants are importable**

Create `tests/test_constants.py`:

```python
def test_constants_importable():
    from mouse_lock.constants import (
        HOTKEY_SAVE, HOTKEY_MOVE, HOTKEY_TOGGLE, HOTKEY_EXIT,
        HOTKEY_RUN, HOTKEY_STOP_CHAIN,
        LOCK_INTERVAL_MS, UI_POLL_MS, ICON_SIZE,
        MAX_PROFILES, MAX_STEPS,
        PROFILES_DIR, PROFILES_FILE,
        SYSTEM_HOTKEYS,
    )
    assert LOCK_INTERVAL_MS == 15
    assert MAX_PROFILES == 5
    assert MAX_STEPS == 50
    assert HOTKEY_RUN == "ctrl+alt+r"
    assert HOTKEY_STOP_CHAIN == "ctrl+alt+x"
    assert len(SYSTEM_HOTKEYS) == 6


def test_system_hotkeys_contains_all():
    from mouse_lock.constants import SYSTEM_HOTKEYS, HOTKEY_RUN, HOTKEY_STOP_CHAIN
    assert HOTKEY_RUN in SYSTEM_HOTKEYS
    assert HOTKEY_STOP_CHAIN in SYSTEM_HOTKEYS
```

- [ ] **Step 5: Run test**

Run: `py -m pytest tests/test_constants.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add mouse_lock/__init__.py mouse_lock/__main__.py mouse_lock/constants.py tests/test_constants.py
git commit -m "feat: package scaffold with constants module"
```

---

## Task 2: DPI and icon modules (extract from mouse_lock.py)

Move `init_dpi_awareness` and `create_tray_icon` into their own modules. Update existing tests to import from new locations.

**Files:**
- Create: `mouse_lock/dpi.py`
- Create: `mouse_lock/icon.py`
- Modify: `tests/test_dpi.py`
- Modify: `tests/test_icon.py`

- [ ] **Step 1: Create `mouse_lock/dpi.py`**

```python
"""Best-effort DPI awareness for Windows."""
from __future__ import annotations

import ctypes


def init_dpi_awareness() -> None:
    """Best-effort DPI awareness. Tries modern API first, falls back, never crashes."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
```

- [ ] **Step 2: Create `mouse_lock/icon.py`**

```python
"""System tray icon generation."""
from __future__ import annotations

from mouse_lock.constants import ICON_SIZE


def create_tray_icon() -> "Image.Image":
    """Draw a crosshair/target symbol on a dark background. Returns a PIL Image."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 2 - 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 100, 255), width=2)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(0, 200, 100, 255))
    draw.line([(cx - r, cy), (cx - 6, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx + 6, cy), (cx + r, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy - r), (cx, cy - 6)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy + 6), (cx, cy + r)], fill=(0, 200, 100, 255), width=1)
    return img
```

- [ ] **Step 3: Update `tests/test_dpi.py`**

```python
def test_init_dpi_awareness_does_not_crash():
    """DPI init must never raise, regardless of OS support."""
    from mouse_lock.dpi import init_dpi_awareness
    init_dpi_awareness()
```

- [ ] **Step 4: Update `tests/test_icon.py`**

```python
from PIL import Image
from mouse_lock.icon import create_tray_icon
from mouse_lock.constants import ICON_SIZE


def test_create_tray_icon_returns_image():
    img = create_tray_icon()
    assert isinstance(img, Image.Image)


def test_create_tray_icon_correct_size():
    img = create_tray_icon()
    assert img.size == (ICON_SIZE, ICON_SIZE)


def test_create_tray_icon_is_rgba():
    img = create_tray_icon()
    assert img.mode == "RGBA"
```

- [ ] **Step 5: Run tests**

Run: `py -m pytest tests/test_dpi.py tests/test_icon.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add mouse_lock/dpi.py mouse_lock/icon.py tests/test_dpi.py tests/test_icon.py
git commit -m "feat: extract dpi and icon modules into package"
```

---

## Task 3: Data models (ActionStep, Profile)

Create the data model classes with serialization to/from dicts for JSON persistence.

**Files:**
- Create: `mouse_lock/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/test_models.py`:

```python
import uuid
from mouse_lock.models import ActionStep, Profile, VALID_ACTIONS, REQUIRED_PARAMS


def test_action_step_creation():
    step = ActionStep(action="move", params={"x": 100, "y": 200})
    assert step.action == "move"
    assert step.params == {"x": 100, "y": 200}


def test_action_step_to_dict():
    step = ActionStep(action="click", params={"button": "left", "x": 50, "y": 60})
    d = step.to_dict()
    assert d == {"action": "click", "params": {"button": "left", "x": 50, "y": 60}}


def test_action_step_from_dict():
    d = {"action": "wait", "params": {"ms": 500}}
    step = ActionStep.from_dict(d)
    assert step.action == "wait"
    assert step.params["ms"] == 500


def test_profile_creation():
    p = Profile(id="abc-123", name="Test", hotkey="ctrl+alt+1", steps=[])
    assert p.id == "abc-123"
    assert p.name == "Test"
    assert p.hotkey == "ctrl+alt+1"
    assert p.steps == []


def test_profile_to_dict_and_back():
    steps = [
        ActionStep(action="move", params={"x": 10, "y": 20}),
        ActionStep(action="wait", params={"ms": 100}),
    ]
    p = Profile(id="test-id", name="My Profile", hotkey=None, steps=steps)
    d = p.to_dict()
    p2 = Profile.from_dict(d)
    assert p2.id == p.id
    assert p2.name == p.name
    assert p2.hotkey is None
    assert len(p2.steps) == 2
    assert p2.steps[0].action == "move"


def test_profile_create_new_generates_uuid():
    p = Profile.create_new(name="Fresh", hotkey=None, steps=[])
    uuid.UUID(p.id)  # raises if not valid UUID


def test_valid_actions_complete():
    assert VALID_ACTIONS == {"move", "click", "repeat_click", "keypress", "wait", "lock"}


def test_required_params_defined():
    assert "x" in REQUIRED_PARAMS["move"]
    assert "y" in REQUIRED_PARAMS["move"]
    assert "button" in REQUIRED_PARAMS["click"]
    assert "ms" in REQUIRED_PARAMS["wait"]
    assert "count" in REQUIRED_PARAMS["repeat_click"]
    assert "duration_ms" in REQUIRED_PARAMS["lock"]
    assert "key" in REQUIRED_PARAMS["keypress"]


def test_action_step_validate_valid():
    step = ActionStep(action="move", params={"x": 100, "y": 200})
    assert step.validate() is True


def test_action_step_validate_missing_param():
    step = ActionStep(action="move", params={"x": 100})
    assert step.validate() is False


def test_action_step_validate_unknown_action():
    step = ActionStep(action="explode", params={})
    assert step.validate() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/test_models.py -v`
Expected: FAIL (import errors)

- [ ] **Step 3: Implement `mouse_lock/models.py`**

```python
"""Profile and ActionStep data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


VALID_ACTIONS = {"move", "click", "repeat_click", "keypress", "wait", "lock"}

REQUIRED_PARAMS: dict[str, set[str]] = {
    "move": {"x", "y"},
    "click": {"button", "x", "y"},
    "repeat_click": {"button", "x", "y", "count", "interval_ms"},
    "keypress": {"key"},
    "wait": {"ms"},
    "lock": {"x", "y", "duration_ms"},
}


@dataclass
class ActionStep:
    action: str
    params: dict

    def validate(self) -> bool:
        if self.action not in VALID_ACTIONS:
            return False
        required = REQUIRED_PARAMS.get(self.action, set())
        return required.issubset(self.params.keys())

    def to_dict(self) -> dict:
        return {"action": self.action, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> ActionStep:
        return cls(action=d["action"], params=dict(d["params"]))


@dataclass
class Profile:
    id: str
    name: str
    hotkey: str | None
    steps: list[ActionStep]

    @classmethod
    def create_new(cls, name: str, hotkey: str | None, steps: list[ActionStep]) -> Profile:
        return cls(id=str(uuid.uuid4()), name=name, hotkey=hotkey, steps=steps)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        steps = [ActionStep.from_dict(s) for s in d["steps"]]
        return cls(id=d["id"], name=d["name"], hotkey=d.get("hotkey"), steps=steps)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/test_models.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add mouse_lock/models.py tests/test_models.py
git commit -m "feat: ActionStep and Profile data models with serialization"
```

---

## Task 4: AppState — extract and extend

Move `AppState` into `mouse_lock/state.py`. Add new profile-related fields (`active_profile_id`, `runner_busy`, `chain_lock_active`, `chain_lock_pos`). Migrate existing tests.

**Files:**
- Create: `mouse_lock/state.py`
- Modify: `tests/test_state.py` (replaces `tests/test_app_state.py`)
- Modify: `tests/conftest.py`

- [ ] **Step 1: Create `mouse_lock/state.py`**

```python
"""Thread-safe shared application state."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class AppState:
    saved_pos: tuple[int, int] | None
    lock_active: bool
    stop_event: threading.Event
    hotkey_errors: list[str]
    status_message: str
    active_profile_id: str | None
    runner_busy: bool
    chain_lock_active: bool
    chain_lock_pos: tuple[int, int] | None
    _lock: threading.Lock = field(repr=False)

    # --- saved position ---
    def get_saved_pos(self) -> tuple[int, int] | None:
        with self._lock:
            return self.saved_pos

    def set_saved_pos(self, pos: tuple[int, int]) -> None:
        with self._lock:
            self.saved_pos = pos
            self.status_message = "Position saved"

    # --- lock ---
    def get_lock_active(self) -> bool:
        with self._lock:
            return self.lock_active

    def toggle_lock(self) -> bool:
        with self._lock:
            self.lock_active = not self.lock_active
            return self.lock_active

    # --- status message ---
    def get_status_message(self) -> str:
        with self._lock:
            return self.status_message

    def set_status_message(self, msg: str) -> None:
        with self._lock:
            self.status_message = msg

    # --- hotkey errors ---
    def get_hotkey_errors(self) -> list[str]:
        with self._lock:
            return list(self.hotkey_errors)

    def add_hotkey_error(self, error: str) -> None:
        with self._lock:
            self.hotkey_errors.append(error)

    # --- active profile ---
    def get_active_profile_id(self) -> str | None:
        with self._lock:
            return self.active_profile_id

    def set_active_profile_id(self, profile_id: str | None) -> None:
        with self._lock:
            self.active_profile_id = profile_id

    # --- runner busy ---
    def get_runner_busy(self) -> bool:
        with self._lock:
            return self.runner_busy

    def set_runner_busy(self, busy: bool) -> None:
        with self._lock:
            self.runner_busy = busy

    # --- chain lock ---
    def get_chain_lock(self) -> tuple[bool, tuple[int, int] | None]:
        with self._lock:
            return self.chain_lock_active, self.chain_lock_pos

    def set_chain_lock(self, active: bool, pos: tuple[int, int] | None = None) -> None:
        with self._lock:
            self.chain_lock_active = active
            self.chain_lock_pos = pos


def make_state() -> AppState:
    """Factory — creates a fresh AppState with sensible defaults."""
    return AppState(
        saved_pos=None,
        lock_active=False,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        active_profile_id=None,
        runner_busy=False,
        chain_lock_active=False,
        chain_lock_pos=None,
        _lock=threading.Lock(),
    )
```

- [ ] **Step 2: Update `tests/conftest.py`**

```python
import threading
import pytest


@pytest.fixture
def stop_event():
    e = threading.Event()
    yield e
    e.set()
```

- [ ] **Step 3: Rename and update tests**

Delete `tests/test_app_state.py`. Create `tests/test_state.py`:

```python
from mouse_lock.state import make_state


def test_initial_state():
    s = make_state()
    assert s.get_saved_pos() is None
    assert s.get_lock_active() is False
    assert s.get_status_message() == ""
    assert s.get_hotkey_errors() == []
    assert s.get_active_profile_id() is None
    assert s.get_runner_busy() is False
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None


def test_set_saved_pos():
    s = make_state()
    s.set_saved_pos((100, 200))
    assert s.get_saved_pos() == (100, 200)


def test_set_saved_pos_sets_status():
    s = make_state()
    s.set_saved_pos((10, 20))
    assert s.get_status_message() == "Position saved"


def test_toggle_lock_on():
    s = make_state()
    s.toggle_lock()
    assert s.get_lock_active() is True


def test_toggle_lock_off():
    s = make_state()
    s.toggle_lock()
    s.toggle_lock()
    assert s.get_lock_active() is False


def test_set_status_message():
    s = make_state()
    s.set_status_message("hello")
    assert s.get_status_message() == "hello"


def test_add_hotkey_error():
    s = make_state()
    s.add_hotkey_error("ctrl+alt+s failed")
    assert "ctrl+alt+s failed" in s.get_hotkey_errors()


def test_add_multiple_hotkey_errors():
    s = make_state()
    s.add_hotkey_error("err1")
    s.add_hotkey_error("err2")
    assert len(s.get_hotkey_errors()) == 2


def test_active_profile_id():
    s = make_state()
    s.set_active_profile_id("abc-123")
    assert s.get_active_profile_id() == "abc-123"


def test_runner_busy():
    s = make_state()
    s.set_runner_busy(True)
    assert s.get_runner_busy() is True
    s.set_runner_busy(False)
    assert s.get_runner_busy() is False


def test_chain_lock():
    s = make_state()
    s.set_chain_lock(True, (500, 300))
    active, pos = s.get_chain_lock()
    assert active is True
    assert pos == (500, 300)


def test_chain_lock_reset():
    s = make_state()
    s.set_chain_lock(True, (500, 300))
    s.set_chain_lock(False)
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None
```

- [ ] **Step 4: Run tests**

Run: `py -m pytest tests/test_state.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add mouse_lock/state.py tests/test_state.py tests/conftest.py
git rm tests/test_app_state.py
git commit -m "feat: extract AppState to state.py with new profile fields"
```

---

## Task 5: Cursor operations module

Extract `_get_cursor_pos` from `HotkeyManager` into standalone functions. Add `set_cursor_pos`, `click`, `repeat_click`.

**Files:**
- Create: `mouse_lock/cursor.py`
- Create: `tests/test_cursor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cursor.py`:

```python
import threading
from unittest.mock import patch, MagicMock
from mouse_lock.cursor import get_cursor_pos, set_cursor_pos, click, repeat_click


def test_get_cursor_pos_success():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.Structure = __import__("ctypes").Structure
        mock_ct.c_long = __import__("ctypes").c_long
        mock_ct.byref = __import__("ctypes").byref

        def fake_get(pt_ref):
            pt = pt_ref._obj if hasattr(pt_ref, '_obj') else pt_ref
            pt.x = 42
            pt.y = 99

        mock_ct.windll.user32.GetCursorPos.side_effect = fake_get
        result = get_cursor_pos()
    assert result == (42, 99)


def test_get_cursor_pos_returns_none_on_failure():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.Structure = __import__("ctypes").Structure
        mock_ct.c_long = __import__("ctypes").c_long
        mock_ct.byref = __import__("ctypes").byref
        mock_ct.windll.user32.GetCursorPos.side_effect = Exception("fail")
        result = get_cursor_pos()
    assert result is None


def test_set_cursor_pos_success():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        assert set_cursor_pos(100, 200) is True
        mock_ct.windll.user32.SetCursorPos.assert_called_once_with(100, 200)


def test_set_cursor_pos_failure():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = Exception("fail")
        assert set_cursor_pos(100, 200) is False


def test_click_calls_mouse_event():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        result = click("left", 100, 200)
    assert result is True
    assert mock_ct.windll.user32.SetCursorPos.called
    assert mock_ct.windll.user32.mouse_event.call_count == 2  # down + up


def test_click_right_button():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        result = click("right", 50, 60)
    assert result is True


def test_click_failure_returns_false():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = Exception("fail")
        result = click("left", 100, 200)
    assert result is False


def test_repeat_click_counts():
    stop = threading.Event()
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        completed = repeat_click("left", 100, 200, count=3, interval_ms=10, stop_event=stop)
    assert completed == 3


def test_repeat_click_interrupted():
    stop = threading.Event()
    stop.set()  # pre-set: should stop immediately
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        completed = repeat_click("left", 100, 200, count=100, interval_ms=10, stop_event=stop)
    assert completed < 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/test_cursor.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `mouse_lock/cursor.py`**

```python
"""Win32 cursor operations via ctypes."""
from __future__ import annotations

import ctypes
from threading import Event

# mouse_event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

_BUTTON_FLAGS = {
    "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def get_cursor_pos() -> tuple[int, int] | None:
    """Read current cursor position via Win32 GetCursorPos."""
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT()
    try:
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return None


def set_cursor_pos(x: int, y: int) -> bool:
    """Move cursor to (x, y). Returns True on success."""
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        return True
    except Exception:
        return False


def click(button: str, x: int, y: int) -> bool:
    """Move to (x, y) and perform a single click. Returns True on success."""
    flags = _BUTTON_FLAGS.get(button)
    if flags is None:
        return False
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        ctypes.windll.user32.mouse_event(flags[0], 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(flags[1], 0, 0, 0, 0)
        return True
    except Exception:
        return False


def repeat_click(
    button: str, x: int, y: int, count: int, interval_ms: int, stop_event: Event
) -> int:
    """Perform count clicks with interval. Returns number of clicks completed."""
    completed = 0
    for _ in range(count):
        if stop_event.is_set():
            break
        if click(button, x, y):
            completed += 1
        if stop_event.wait(timeout=interval_ms / 1000.0):
            break
    return completed
```

- [ ] **Step 4: Run tests**

Run: `py -m pytest tests/test_cursor.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add mouse_lock/cursor.py tests/test_cursor.py
git commit -m "feat: cursor operations module with Win32 ctypes"
```

---

## Task 6: ProfileStore — JSON persistence

Implement load/save of profiles to `~/.mouse_lock/profiles.json` with atomic writes, thread safety, and max-profiles enforcement.

**Files:**
- Create: `mouse_lock/profile_store.py`
- Create: `tests/test_profile_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_profile_store.py`:

```python
import json
import os
import pytest
from mouse_lock.models import Profile, ActionStep
from mouse_lock.profile_store import ProfileStore


@pytest.fixture
def store(tmp_path):
    """ProfileStore pointing at a temp directory."""
    return ProfileStore(profiles_dir=str(tmp_path))


@pytest.fixture
def sample_profile():
    return Profile.create_new(
        name="Test",
        hotkey="ctrl+alt+1",
        steps=[ActionStep(action="move", params={"x": 100, "y": 200})],
    )


def test_load_empty(store):
    profiles = store.load()
    assert profiles == []


def test_add_and_load(store, sample_profile):
    store.add_profile(sample_profile)
    profiles = store.load()
    assert len(profiles) == 1
    assert profiles[0].name == "Test"


def test_save_creates_file(store, sample_profile, tmp_path):
    store.add_profile(sample_profile)
    assert (tmp_path / "profiles.json").exists()


def test_update_profile(store, sample_profile):
    store.add_profile(sample_profile)
    sample_profile.name = "Updated"
    store.update_profile(sample_profile)
    profiles = store.load()
    assert profiles[0].name == "Updated"


def test_delete_profile(store, sample_profile):
    store.add_profile(sample_profile)
    store.delete_profile(sample_profile.id)
    assert store.load() == []


def test_max_profiles(store):
    for i in range(5):
        p = Profile.create_new(name=f"P{i}", hotkey=None, steps=[])
        store.add_profile(p)
    with pytest.raises(ValueError, match="Max"):
        store.add_profile(Profile.create_new(name="P6", hotkey=None, steps=[]))


def test_corrupted_json(store, tmp_path):
    (tmp_path / "profiles.json").write_text("not valid json{{{")
    profiles = store.load()
    assert profiles == []


def test_get_by_id(store, sample_profile):
    store.add_profile(sample_profile)
    found = store.get_by_id(sample_profile.id)
    assert found is not None
    assert found.name == "Test"


def test_get_by_id_not_found(store):
    assert store.get_by_id("nonexistent") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/test_profile_store.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `mouse_lock/profile_store.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `py -m pytest tests/test_profile_store.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add mouse_lock/profile_store.py tests/test_profile_store.py
git commit -m "feat: ProfileStore with JSON persistence and atomic writes"
```

---

## Task 7: LockLoop — extract and extend with chain_lock support

Move `LockLoop` from `mouse_lock.py` to `mouse_lock/lock_loop.py`. Add the 3-case branching logic for `chain_lock_active`. Migrate and extend tests.

**Files:**
- Create: `mouse_lock/lock_loop.py`
- Modify: `tests/test_lock_loop.py`

- [ ] **Step 1: Create `mouse_lock/lock_loop.py`**

```python
"""Lock loop — daemon thread that holds cursor at a target position."""
from __future__ import annotations

import ctypes
import threading

from mouse_lock.constants import LOCK_INTERVAL_MS
from mouse_lock.state import AppState


class LockLoop:
    """Continuously moves cursor to target position based on state flags."""

    def __init__(self, state: AppState) -> None:
        self._state = state

    def run(self) -> None:
        """Thread entry point. Exits when stop_event is set."""
        while not self._state.stop_event.is_set():
            target = self._get_target()
            if target is not None:
                try:
                    ctypes.windll.user32.SetCursorPos(target[0], target[1])
                except Exception:
                    pass
            self._state.stop_event.wait(timeout=LOCK_INTERVAL_MS / 1000.0)

    def _get_target(self) -> tuple[int, int] | None:
        """Determine cursor target using 3-case priority."""
        chain_active, chain_pos = self._state.get_chain_lock()
        if chain_active and chain_pos is not None:
            return chain_pos
        if self._state.get_lock_active():
            return self._state.get_saved_pos()
        return None

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run, name="LockLoop", daemon=True)
        t.start()
        return t
```

- [ ] **Step 2: Update `tests/test_lock_loop.py`**

```python
import threading
import time
from unittest.mock import patch
from mouse_lock.state import make_state
from mouse_lock.lock_loop import LockLoop


def test_lock_loop_exits_on_stop_event():
    state = make_state()
    loop = LockLoop(state)
    t = threading.Thread(target=loop.run, daemon=True)
    t.start()
    state.stop_event.set()
    t.join(timeout=0.5)
    assert not t.is_alive()


def test_lock_loop_does_not_move_when_inactive():
    state = make_state()
    state.saved_pos = (100, 200)
    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ct.windll.user32.SetCursorPos.assert_not_called()


def test_lock_loop_moves_when_active():
    state = make_state()
    state.saved_pos = (100, 200)
    state.lock_active = True
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (100, 200)


def test_lock_loop_does_not_move_without_saved_pos():
    state = make_state()
    state.lock_active = True
    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ct.windll.user32.SetCursorPos.assert_not_called()


def test_chain_lock_takes_precedence():
    """When chain_lock_active, LockLoop uses chain_lock_pos, not saved_pos."""
    state = make_state()
    state.saved_pos = (100, 200)
    state.lock_active = True
    state.set_chain_lock(True, (500, 300))
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (500, 300)


def test_chain_lock_overrides_inactive_lock():
    """chain_lock works even if lock_active is False."""
    state = make_state()
    state.lock_active = False
    state.set_chain_lock(True, (300, 400))
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (300, 400)
```

- [ ] **Step 3: Run tests**

Run: `py -m pytest tests/test_lock_loop.py -v`
Expected: PASS (6 tests)

- [ ] **Step 4: Commit**

```bash
git add mouse_lock/lock_loop.py tests/test_lock_loop.py
git commit -m "feat: extract LockLoop with chain_lock_active support"
```

---

## Task 8: ActionRunner — execute action chains

Implement the action chain executor that runs profiles in a worker thread with interruption support.

**Files:**
- Create: `mouse_lock/action_runner.py`
- Create: `tests/test_action_runner.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_action_runner.py`:

```python
import threading
import time
from unittest.mock import patch, MagicMock
from mouse_lock.state import make_state
from mouse_lock.models import ActionStep, Profile
from mouse_lock.action_runner import ActionRunner


def make_profile(steps, name="Test"):
    return Profile(id="test-id", name=name, hotkey=None, steps=steps)


def test_run_empty_profile():
    state = make_state()
    runner = ActionRunner(state)
    profile = make_profile([])
    runner.run_profile(profile)
    time.sleep(0.1)
    assert not runner.is_running()


def test_run_move_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="move", params={"x": 100, "y": 200})]
    profile = make_profile(steps)
    with patch("mouse_lock.action_runner.cursor") as mock_cursor:
        mock_cursor.set_cursor_pos.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.set_cursor_pos.assert_called_with(100, 200)


def test_run_click_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="click", params={"button": "left", "x": 50, "y": 60})]
    profile = make_profile(steps)
    with patch("mouse_lock.action_runner.cursor") as mock_cursor:
        mock_cursor.click.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.click.assert_called_with("left", 50, 60)


def test_run_wait_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 50})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.2)
    assert not runner.is_running()


def test_run_keypress_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="keypress", params={"key": "enter"})]
    profile = make_profile(steps)
    with patch("mouse_lock.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_kb.press_and_release.assert_called_with("enter")


def test_stop_interrupts_chain():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 5000})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.05)
    assert runner.is_running()
    runner.stop()
    time.sleep(0.1)
    assert not runner.is_running()


def test_ignore_while_running():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 5000})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.05)
    runner.run_profile(profile)  # should be ignored
    assert "Already running" in state.get_status_message()
    runner.stop()
    time.sleep(0.1)


def test_invalid_params_skipped():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="move", params={"x": 100})]  # missing y
    profile = make_profile(steps)
    with patch("mouse_lock.action_runner.cursor") as mock_cursor:
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.set_cursor_pos.assert_not_called()


def test_chain_lock_step_sets_state():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="lock", params={"x": 500, "y": 300, "duration_ms": 100})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.02)
    active, pos = state.get_chain_lock()
    assert active is True
    assert pos == (500, 300)
    time.sleep(0.3)
    active, _ = state.get_chain_lock()
    assert active is False


def test_repeat_click_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="repeat_click", params={
        "button": "left", "x": 100, "y": 200, "count": 3, "interval_ms": 10
    })]
    profile = make_profile(steps)
    with patch("mouse_lock.action_runner.cursor") as mock_cursor:
        mock_cursor.repeat_click.return_value = 3
        runner.run_profile(profile)
        time.sleep(0.3)
    mock_cursor.repeat_click.assert_called_once()


def test_status_messages_during_run():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 50})]
    profile = make_profile(steps, name="Farm Spot")
    runner.run_profile(profile)
    time.sleep(0.01)
    msg = state.get_status_message()
    assert "Farm Spot" in msg or "Step" in msg or "Running" in msg
    time.sleep(0.2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/test_action_runner.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `mouse_lock/action_runner.py`**

```python
"""Execute action chains in a worker thread."""
from __future__ import annotations

import threading

import keyboard

from mouse_lock import cursor
from mouse_lock.models import ActionStep, Profile
from mouse_lock.state import AppState


class ActionRunner:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def run_profile(self, profile: Profile) -> None:
        with self._lock:
            if self._running:
                self._state.set_status_message("Already running")
                return
            self._running = True
            self._stop_event.clear()
            self._state.set_runner_busy(True)

        self._thread = threading.Thread(
            target=self._execute_chain,
            args=(profile,),
            name="ActionRunner",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        t = self._thread
        if t is not None:
            t.join(timeout=2.0)

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _execute_chain(self, profile: Profile) -> None:
        try:
            self._state.set_status_message(f"Running: {profile.name}")
            for i, step in enumerate(profile.steps):
                if self._stop_event.is_set():
                    break

                if not step.validate():
                    self._state.set_status_message(f"Step {i+1}: invalid params")
                    continue

                self._state.set_status_message(
                    f"Step {i+1}/{len(profile.steps)}: {step.action}"
                )
                self._execute_step(step)

            if not self._stop_event.is_set():
                self._state.set_status_message("Done")
        finally:
            self._state.set_chain_lock(False)
            self._state.set_runner_busy(False)
            with self._lock:
                self._running = False

    def _execute_step(self, step: ActionStep) -> None:
        p = step.params
        try:
            if step.action == "move":
                cursor.set_cursor_pos(p["x"], p["y"])

            elif step.action == "click":
                cursor.click(p["button"], p["x"], p["y"])

            elif step.action == "repeat_click":
                cursor.repeat_click(
                    p["button"], p["x"], p["y"],
                    p["count"], p["interval_ms"],
                    self._stop_event,
                )

            elif step.action == "keypress":
                keyboard.press_and_release(p["key"])

            elif step.action == "wait":
                self._stop_event.wait(timeout=p["ms"] / 1000.0)

            elif step.action == "lock":
                self._state.set_chain_lock(True, (p["x"], p["y"]))
                duration_ms = p["duration_ms"]
                if duration_ms == 0:
                    self._stop_event.wait()  # block until stopped
                else:
                    self._stop_event.wait(timeout=duration_ms / 1000.0)

        except Exception:
            self._state.set_status_message(f"Step failed: {step.action}")
```

- [ ] **Step 4: Run tests**

Run: `py -m pytest tests/test_action_runner.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add mouse_lock/action_runner.py tests/test_action_runner.py
git commit -m "feat: ActionRunner for executing profile action chains"
```

---

## Task 9: HotkeyManager — extract and extend

Move `HotkeyManager` from `mouse_lock.py` into `mouse_lock/hotkeys.py`. Extend with run/stop hotkeys, profile hotkey management, and conflict detection. Migrate and extend tests.

**Files:**
- Create: `mouse_lock/hotkeys.py`
- Modify: `tests/test_hotkeys.py`

- [ ] **Step 1: Create `mouse_lock/hotkeys.py`**

```python
"""Global hotkey registration and management."""
from __future__ import annotations

import threading

from mouse_lock.constants import (
    HOTKEY_SAVE, HOTKEY_MOVE, HOTKEY_TOGGLE, HOTKEY_EXIT,
    HOTKEY_RUN, HOTKEY_STOP_CHAIN, SYSTEM_HOTKEYS,
)
from mouse_lock.cursor import get_cursor_pos, set_cursor_pos
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

    def register_all(self) -> None:
        import keyboard

        bindings = [
            (HOTKEY_SAVE, self._on_save),
            (HOTKEY_MOVE, self._on_move),
            (HOTKEY_TOGGLE, self._on_toggle),
            (HOTKEY_EXIT, self._on_exit),
            (HOTKEY_RUN, self._on_run),
            (HOTKEY_STOP_CHAIN, self._on_stop_chain),
        ]
        for combo, callback in bindings:
            try:
                keyboard.add_hotkey(combo, callback, suppress=False)
                self._registered.append(combo)
            except Exception as exc:
                self._state.add_hotkey_error(f"{combo}: {exc}")

    def unregister_all(self) -> None:
        import keyboard
        for combo in self._registered + self._profile_hotkeys:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._registered.clear()
        self._profile_hotkeys.clear()

    def refresh_profile_hotkeys(self, profiles) -> None:
        import keyboard

        # Unregister old profile hotkeys
        for combo in self._profile_hotkeys:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._profile_hotkeys.clear()

        # Register new ones (with conflict detection)
        seen: set[str] = set()
        for profile in profiles:
            if profile.hotkey is None:
                continue
            hk = profile.hotkey.lower()
            if hk in SYSTEM_HOTKEYS or hk in seen:
                self._state.add_hotkey_error(
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
                self._state.add_hotkey_error(f"{profile.hotkey}: {exc}")

    def start(self) -> threading.Thread:
        import keyboard
        t = threading.Thread(target=keyboard.wait, name="HotkeyThread", daemon=True)
        t.start()
        return t

    # --- callbacks ---

    def _on_save(self) -> None:
        pos = get_cursor_pos()
        if pos:
            self._state.set_saved_pos(pos)

    def _on_move(self) -> None:
        pos = self._state.get_saved_pos()
        if pos is None:
            self._state.set_status_message("No position saved")
            return
        set_cursor_pos(pos[0], pos[1])

    def _on_toggle(self) -> None:
        self._state.toggle_lock()

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
```

- [ ] **Step 2: Update `tests/test_hotkeys.py`**

```python
import threading
from unittest.mock import patch, MagicMock
from mouse_lock.state import make_state
from mouse_lock.hotkeys import HotkeyManager
from mouse_lock.models import Profile


def test_failed_hotkey_registration_stored_in_state():
    state = make_state()
    root_mock = MagicMock()

    with patch("keyboard.add_hotkey", side_effect=Exception("Cannot register")):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    errors = state.get_hotkey_errors()
    assert len(errors) == 6  # all six system hotkeys failed
    assert any("ctrl+alt+s" in e for e in errors)


def test_partial_registration_failure():
    state = make_state()
    root_mock = MagicMock()
    call_count = [0]

    def sometimes_fail(combo, callback, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise Exception("second hotkey failed")

    with patch("keyboard.add_hotkey", side_effect=sometimes_fail):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    assert len(state.get_hotkey_errors()) == 1


def test_unregister_all_ignores_errors():
    state = make_state()
    root_mock = MagicMock()

    with patch("keyboard.add_hotkey"):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    with patch("keyboard.remove_hotkey", side_effect=Exception("fail")):
        hm.unregister_all()


def test_on_save_captures_cursor_position():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    with patch("mouse_lock.hotkeys.get_cursor_pos", return_value=(42, 99)):
        hm._on_save()

    assert state.get_saved_pos() == (42, 99)
    assert state.get_status_message() == "Position saved"


def test_on_run_no_profile_selected():
    state = make_state()
    root_mock = MagicMock()
    runner = MagicMock()
    store = MagicMock()
    hm = HotkeyManager(state, root_mock, runner, store)
    hm._on_run()
    assert "No profile selected" in state.get_status_message()


def test_on_run_with_profile():
    state = make_state()
    state.set_active_profile_id("test-id")
    root_mock = MagicMock()
    runner = MagicMock()
    profile = Profile(id="test-id", name="Test", hotkey=None, steps=[])
    store = MagicMock()
    store.get_by_id.return_value = profile
    hm = HotkeyManager(state, root_mock, runner, store)
    hm._on_run()
    runner.run_profile.assert_called_once_with(profile)


def test_on_stop_chain():
    state = make_state()
    root_mock = MagicMock()
    runner = MagicMock()
    hm = HotkeyManager(state, root_mock, runner)
    hm._on_stop_chain()
    runner.stop.assert_called_once()


def test_refresh_profile_hotkeys_conflict_detection():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+s", steps=[]),  # conflicts with system
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(profiles)

    errors = state.get_hotkey_errors()
    assert any("conflicts" in e for e in errors)


def test_refresh_profile_hotkeys_duplicate_detection():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+1", steps=[]),
        Profile(id="2", name="P2", hotkey="ctrl+alt+1", steps=[]),  # duplicate
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(profiles)

    errors = state.get_hotkey_errors()
    assert any("conflicts" in e for e in errors)
```

- [ ] **Step 3: Run tests**

Run: `py -m pytest tests/test_hotkeys.py -v`
Expected: PASS (10 tests)

- [ ] **Step 4: Commit**

```bash
git add mouse_lock/hotkeys.py tests/test_hotkeys.py
git commit -m "feat: HotkeyManager with profile hotkeys and conflict detection"
```

---

## Task 10: TrayManager — extract

Move `TrayManager` and `show_window` from `mouse_lock.py` into `mouse_lock/tray.py`. No functional changes.

**Files:**
- Create: `mouse_lock/tray.py`

- [ ] **Step 1: Create `mouse_lock/tray.py`**

```python
"""System tray icon manager."""
from __future__ import annotations

import threading

from mouse_lock.hotkeys import _shutdown_ref
from mouse_lock.icon import create_tray_icon
from mouse_lock.state import AppState


def show_window(root) -> None:
    """Restore and bring the Tkinter window to the foreground."""
    root.deiconify()
    root.lift()
    root.focus_force()


class TrayManager:
    def __init__(self, state: AppState, root) -> None:
        self._state = state
        self._root = root
        self._icon = None

    def start(self) -> bool:
        try:
            import pystray

            icon_image = create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Show UI",
                    lambda icon, item: self._root.after(0, lambda: show_window(self._root)),
                ),
                pystray.MenuItem(
                    "Lock",
                    lambda icon, item: self._state.toggle_lock(),
                    checked=lambda item: self._state.get_lock_active(),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit",
                    lambda icon, item: self._root.after(0, _shutdown_ref[0]),
                ),
            )
            self._icon = pystray.Icon(
                name="MouseLock", icon=icon_image, title="Mouse Lock", menu=menu,
            )
            self._icon.default_action = lambda icon, item: self._root.after(
                0, lambda: show_window(self._root)
            )
            t = threading.Thread(target=self._icon.run, name="TrayThread", daemon=True)
            t.start()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
```

- [ ] **Step 2: Verify package imports work**

Run: `py -c "from mouse_lock.tray import TrayManager, show_window; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mouse_lock/tray.py
git commit -m "feat: extract TrayManager into tray module"
```

---

## Task 11: Main window UI

Create the expanded Tkinter main window with profile list, buttons, and polling loop.

**Files:**
- Create: `mouse_lock/ui/__init__.py`
- Create: `mouse_lock/ui/main_window.py`

- [ ] **Step 1: Create `mouse_lock/ui/__init__.py`**

Empty file.

- [ ] **Step 2: Create `mouse_lock/ui/main_window.py`**

```python
"""Main application window with profile list."""
from __future__ import annotations

import tkinter as tk

from mouse_lock.constants import UI_POLL_MS, MAX_PROFILES
from mouse_lock.cursor import get_cursor_pos, set_cursor_pos
from mouse_lock.hotkeys import _shutdown_ref
from mouse_lock.state import AppState


class MainWindow:
    def __init__(
        self, root: tk.Tk, state: AppState, tray_available: bool,
        profile_store=None, hotkey_mgr=None, action_runner=None,
    ) -> None:
        self._root = root
        self._state = state
        self._tray_available = tray_available
        self._profile_store = profile_store
        self._hotkey_mgr = hotkey_mgr
        self._action_runner = action_runner

        root.title("Mouse Lock")
        root.resizable(False, False)
        root.geometry("500x450")

        # --- Position row ---
        tk.Label(root, text="Saved Position:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self._pos_label = tk.Label(root, text="Not set", anchor="w", fg="gray")
        self._pos_label.pack(fill="x", padx=20)

        # --- Lock status row ---
        tk.Label(root, text="Lock Status:", anchor="w").pack(fill="x", padx=10, pady=(6, 0))
        self._lock_label = tk.Label(root, text="Unlocked", anchor="w", fg="gray")
        self._lock_label.pack(fill="x", padx=20)

        # --- Status message row ---
        self._status_label = tk.Label(root, text="", anchor="w", fg="steelblue")
        self._status_label.pack(fill="x", padx=10, pady=(4, 0))

        # --- Buttons ---
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=6)
        tk.Button(btn_frame, text="Save Position", width=13, command=self._cmd_save).grid(row=0, column=0, padx=4)
        tk.Button(btn_frame, text="Move Now", width=10, command=self._cmd_move).grid(row=0, column=1, padx=4)
        tk.Button(btn_frame, text="Toggle Lock", width=11, command=self._cmd_toggle).grid(row=0, column=2, padx=4)

        # --- Separator ---
        tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=10, pady=6)

        # --- Profile section ---
        tk.Label(root, text="Profiles:", anchor="w").pack(fill="x", padx=10)

        list_frame = tk.Frame(root)
        list_frame.pack(fill="x", padx=10, pady=(2, 4))
        self._profile_listbox = tk.Listbox(list_frame, height=5, font=("Consolas", 10))
        self._profile_listbox.pack(fill="x")
        self._profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        profile_btn_frame = tk.Frame(root)
        profile_btn_frame.pack(pady=4)
        self._add_btn = tk.Button(profile_btn_frame, text="Add", width=8, command=self._cmd_add)
        self._add_btn.grid(row=0, column=0, padx=3)
        tk.Button(profile_btn_frame, text="Edit", width=8, command=self._cmd_edit).grid(row=0, column=1, padx=3)
        tk.Button(profile_btn_frame, text="Delete", width=8, command=self._cmd_delete).grid(row=0, column=2, padx=3)
        self._run_btn = tk.Button(profile_btn_frame, text="Run", width=8, command=self._cmd_run)
        self._run_btn.grid(row=0, column=3, padx=3)

        # --- Error banner ---
        self._error_frame = tk.Frame(root, bg="#ffcccc")
        self._error_label = tk.Label(
            self._error_frame, text="", bg="#ffcccc", fg="#990000",
            anchor="w", justify="left", wraplength=480,
        )
        self._error_label.pack(padx=6, pady=4, fill="x")

        # --- Window close ---
        if tray_available:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)
        else:
            root.protocol("WM_DELETE_WINDOW", lambda: _shutdown_ref[0]())

        # Initial profile list refresh
        self._refresh_profile_list()

        # Start polling
        root.after(UI_POLL_MS, self._poll)

    # --- Profile list ---

    def _refresh_profile_list(self) -> None:
        self._profile_listbox.delete(0, tk.END)
        if self._profile_store is None:
            return
        profiles = self._profile_store.load()
        active_id = self._state.get_active_profile_id()
        for p in profiles:
            marker = "\u25ba " if p.id == active_id else "  "
            hotkey_str = f"  [{p.hotkey}]" if p.hotkey else "  [\u2014]"
            self._profile_listbox.insert(tk.END, f"{marker}{p.name}{hotkey_str}")
        # Disable Add if at max
        if len(profiles) >= MAX_PROFILES:
            self._add_btn.config(state="disabled")
        else:
            self._add_btn.config(state="normal")

    def _on_profile_select(self, event) -> None:
        sel = self._profile_listbox.curselection()
        if not sel:
            return
        if self._profile_store is None:
            return
        profiles = self._profile_store.load()
        if sel[0] < len(profiles):
            self._state.set_active_profile_id(profiles[sel[0]].id)
            self._refresh_profile_list()

    # --- Button commands ---

    def _cmd_save(self) -> None:
        pos = get_cursor_pos()
        if pos:
            self._state.set_saved_pos(pos)

    def _cmd_move(self) -> None:
        pos = self._state.get_saved_pos()
        if pos is None:
            self._state.set_status_message("No position saved")
            return
        set_cursor_pos(pos[0], pos[1])

    def _cmd_toggle(self) -> None:
        self._state.toggle_lock()

    def _cmd_add(self) -> None:
        from mouse_lock.ui.step_builder import StepBuilderDialog
        dialog = StepBuilderDialog(self._root, self._profile_store)
        self._root.wait_window(dialog.top)
        if dialog.result is not None:
            self._profile_store.add_profile(dialog.result)
            if self._hotkey_mgr:
                self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
            self._refresh_profile_list()

    def _cmd_edit(self) -> None:
        if self._profile_store is None:
            return
        profile_id = self._state.get_active_profile_id()
        if profile_id is None:
            self._state.set_status_message("No profile selected")
            return
        profile = self._profile_store.get_by_id(profile_id)
        if profile is None:
            return
        from mouse_lock.ui.step_builder import StepBuilderDialog
        dialog = StepBuilderDialog(self._root, self._profile_store, profile)
        self._root.wait_window(dialog.top)
        if dialog.result is not None:
            self._profile_store.update_profile(dialog.result)
            if self._hotkey_mgr:
                self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
            self._refresh_profile_list()

    def _cmd_delete(self) -> None:
        if self._profile_store is None:
            return
        profile_id = self._state.get_active_profile_id()
        if profile_id is None:
            self._state.set_status_message("No profile selected")
            return
        self._profile_store.delete_profile(profile_id)
        self._state.set_active_profile_id(None)
        if self._hotkey_mgr:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()

    def _cmd_run(self) -> None:
        if self._action_runner is None or self._profile_store is None:
            return
        profile_id = self._state.get_active_profile_id()
        if profile_id is None:
            self._state.set_status_message("No profile selected")
            return
        profile = self._profile_store.get_by_id(profile_id)
        if profile is None:
            return
        self._action_runner.run_profile(profile)

    # --- Polling ---

    def _poll(self) -> None:
        if self._state.stop_event.is_set():
            return

        pos = self._state.get_saved_pos()
        self._pos_label.config(
            text=f"X: {pos[0]},  Y: {pos[1]}" if pos else "Not set",
            fg="black" if pos else "gray",
        )

        active = self._state.get_lock_active()
        self._lock_label.config(
            text="Lock Active" if active else "Unlocked",
            fg="red" if active else "gray",
        )

        self._status_label.config(text=self._state.get_status_message())

        errors = self._state.get_hotkey_errors()
        if errors:
            self._error_label.config(text="\n".join(errors))
            self._error_frame.pack(fill="x", padx=10)
        else:
            self._error_frame.pack_forget()

        self._root.after(UI_POLL_MS, self._poll)
```

- [ ] **Step 3: Verify import works**

Run: `py -c "from mouse_lock.ui.main_window import MainWindow; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add mouse_lock/ui/__init__.py mouse_lock/ui/main_window.py
git commit -m "feat: MainWindow with profile list and action buttons"
```

---

## Task 12: Step builder dialog

Create the modal dialog for creating/editing profiles with step management and "Pick Position" countdown.

**Files:**
- Create: `mouse_lock/ui/step_builder.py`

- [ ] **Step 1: Create `mouse_lock/ui/step_builder.py`**

```python
"""Step builder dialog for creating and editing profiles."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from mouse_lock.constants import MAX_STEPS, SYSTEM_HOTKEYS
from mouse_lock.cursor import get_cursor_pos
from mouse_lock.models import ActionStep, Profile, VALID_ACTIONS


# Action type → list of (param_name, label, default_value)
_PARAM_FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "move": [("x", "X:", "0"), ("y", "Y:", "0")],
    "click": [("button", "Button:", "left"), ("x", "X:", "0"), ("y", "Y:", "0")],
    "repeat_click": [
        ("button", "Button:", "left"), ("x", "X:", "0"), ("y", "Y:", "0"),
        ("count", "Count:", "5"), ("interval_ms", "Interval (ms):", "100"),
    ],
    "keypress": [("key", "Key:", "enter")],
    "wait": [("ms", "Duration (ms):", "100")],
    "lock": [("x", "X:", "0"), ("y", "Y:", "0"), ("duration_ms", "Duration (ms, 0=forever):", "0")],
}

_NEEDS_POSITION = {"move", "click", "repeat_click", "lock"}

_INT_PARAMS = {"x", "y", "count", "interval_ms", "ms", "duration_ms"}


def _format_step(step: ActionStep) -> str:
    p = step.params
    if step.action == "move":
        return f"move \u2192 ({p.get('x', '?')}, {p.get('y', '?')})"
    if step.action == "click":
        return f"click {p.get('button', '?')} \u2192 ({p.get('x', '?')}, {p.get('y', '?')})"
    if step.action == "repeat_click":
        return f"repeat_click {p.get('button', '?')} x{p.get('count', '?')} \u2192 ({p.get('x', '?')}, {p.get('y', '?')})"
    if step.action == "keypress":
        return f"keypress \"{p.get('key', '?')}\""
    if step.action == "wait":
        return f"wait {p.get('ms', '?')}ms"
    if step.action == "lock":
        dur = p.get("duration_ms", 0)
        dur_str = "forever" if dur == 0 else f"{dur}ms"
        return f"lock ({p.get('x', '?')}, {p.get('y', '?')}) {dur_str}"
    return str(step)


class StepBuilderDialog:
    def __init__(self, parent: tk.Tk, profile_store, profile: Profile | None = None) -> None:
        self._profile_store = profile_store
        self._editing = profile
        self._steps: list[ActionStep] = list(profile.steps) if profile else []
        self.result: Profile | None = None

        self.top = tk.Toplevel(parent)
        self.top.title("Edit Profile" if profile else "New Profile")
        self.top.resizable(False, False)
        self.top.geometry("460x520")
        self.top.grab_set()

        # --- Name ---
        tk.Label(self.top, text="Profile Name:").pack(anchor="w", padx=10, pady=(10, 0))
        self._name_var = tk.StringVar(value=profile.name if profile else "")
        tk.Entry(self.top, textvariable=self._name_var, width=40).pack(padx=10, anchor="w")

        # --- Hotkey ---
        tk.Label(self.top, text="Hotkey (optional, e.g. ctrl+alt+1):").pack(anchor="w", padx=10, pady=(6, 0))
        self._hotkey_var = tk.StringVar(value=profile.hotkey or "" if profile else "")
        tk.Entry(self.top, textvariable=self._hotkey_var, width=30).pack(padx=10, anchor="w")

        # --- Steps list ---
        tk.Label(self.top, text="Steps:").pack(anchor="w", padx=10, pady=(8, 0))
        list_frame = tk.Frame(self.top)
        list_frame.pack(fill="x", padx=10)
        self._steps_listbox = tk.Listbox(list_frame, height=6, font=("Consolas", 9))
        self._steps_listbox.pack(fill="x")

        step_btn_frame = tk.Frame(self.top)
        step_btn_frame.pack(pady=2)
        tk.Button(step_btn_frame, text="\u25b2", width=3, command=self._move_up).grid(row=0, column=0, padx=2)
        tk.Button(step_btn_frame, text="\u25bc", width=3, command=self._move_down).grid(row=0, column=1, padx=2)
        tk.Button(step_btn_frame, text="Remove", width=8, command=self._remove_step).grid(row=0, column=2, padx=2)

        # --- Add step section ---
        tk.Frame(self.top, height=2, bd=1, relief="sunken").pack(fill="x", padx=10, pady=6)
        tk.Label(self.top, text="Add Step:").pack(anchor="w", padx=10)

        action_frame = tk.Frame(self.top)
        action_frame.pack(fill="x", padx=10)
        tk.Label(action_frame, text="Action:").pack(side="left")
        self._action_var = tk.StringVar(value="move")
        action_menu = tk.OptionMenu(action_frame, self._action_var, *sorted(VALID_ACTIONS), command=self._on_action_change)
        action_menu.pack(side="left", padx=4)

        # Pick position button
        self._pick_btn = tk.Button(action_frame, text="Pick Position", command=self._pick_position)
        self._pick_btn.pack(side="right", padx=4)

        # Param fields container
        self._param_frame = tk.Frame(self.top)
        self._param_frame.pack(fill="x", padx=10, pady=4)
        self._param_entries: dict[str, tk.Entry] = {}
        self._param_vars: dict[str, tk.StringVar] = {}
        self._build_param_fields("move")

        self._add_step_btn = tk.Button(self.top, text="+ Add Step", command=self._add_step)
        self._add_step_btn.pack(pady=4)

        # --- Save / Cancel ---
        bottom_frame = tk.Frame(self.top)
        bottom_frame.pack(pady=10)
        tk.Button(bottom_frame, text="Save Profile", width=14, command=self._save).grid(row=0, column=0, padx=6)
        tk.Button(bottom_frame, text="Cancel", width=10, command=self.top.destroy).grid(row=0, column=1, padx=6)

        self._refresh_steps_list()

    def _build_param_fields(self, action: str) -> None:
        for w in self._param_frame.winfo_children():
            w.destroy()
        self._param_entries.clear()
        self._param_vars.clear()

        fields = _PARAM_FIELDS.get(action, [])
        for i, (name, label, default) in enumerate(fields):
            tk.Label(self._param_frame, text=label).grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=default)
            entry = tk.Entry(self._param_frame, textvariable=var, width=20)
            entry.grid(row=i, column=1, padx=4)
            self._param_entries[name] = entry
            self._param_vars[name] = var

        # Show/hide pick button
        if action in _NEEDS_POSITION:
            self._pick_btn.pack(side="right", padx=4)
        else:
            self._pick_btn.pack_forget()

    def _on_action_change(self, action: str) -> None:
        self._build_param_fields(action)

    def _refresh_steps_list(self) -> None:
        self._steps_listbox.delete(0, tk.END)
        for i, step in enumerate(self._steps):
            self._steps_listbox.insert(tk.END, f"{i+1}. {_format_step(step)}")
        if len(self._steps) >= MAX_STEPS:
            self._add_step_btn.config(state="disabled")
        else:
            self._add_step_btn.config(state="normal")

    def _add_step(self) -> None:
        action = self._action_var.get()
        params = {}
        for name, var in self._param_vars.items():
            val = var.get().strip()
            if name in _INT_PARAMS:
                try:
                    params[name] = int(val)
                except ValueError:
                    messagebox.showwarning("Invalid", f"{name} must be an integer")
                    return
            else:
                params[name] = val

        step = ActionStep(action=action, params=params)
        if not step.validate():
            messagebox.showwarning("Invalid", "Missing required parameters")
            return

        self._steps.append(step)
        self._refresh_steps_list()

    def _remove_step(self) -> None:
        sel = self._steps_listbox.curselection()
        if sel:
            del self._steps[sel[0]]
            self._refresh_steps_list()

    def _move_up(self) -> None:
        sel = self._steps_listbox.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            self._steps[i-1], self._steps[i] = self._steps[i], self._steps[i-1]
            self._refresh_steps_list()
            self._steps_listbox.selection_set(i-1)

    def _move_down(self) -> None:
        sel = self._steps_listbox.curselection()
        if sel and sel[0] < len(self._steps) - 1:
            i = sel[0]
            self._steps[i], self._steps[i+1] = self._steps[i+1], self._steps[i]
            self._refresh_steps_list()
            self._steps_listbox.selection_set(i+1)

    def _pick_position(self) -> None:
        self._pick_btn.config(state="disabled")
        self._countdown(3)

    def _countdown(self, remaining: int) -> None:
        if remaining > 0:
            self._pick_btn.config(text=f"{remaining}...")
            self.top.after(1000, lambda: self._countdown(remaining - 1))
        else:
            pos = get_cursor_pos()
            if pos:
                if "x" in self._param_vars:
                    self._param_vars["x"].set(str(pos[0]))
                if "y" in self._param_vars:
                    self._param_vars["y"].set(str(pos[1]))
            self._pick_btn.config(text="Pick Position", state="normal")

    def _save(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Invalid", "Name cannot be empty")
            return
        if not self._steps:
            messagebox.showwarning("Invalid", "Add at least one step")
            return

        hotkey = self._hotkey_var.get().strip() or None

        # Hotkey conflict check
        if hotkey:
            hk_lower = hotkey.lower()
            if hk_lower in SYSTEM_HOTKEYS:
                messagebox.showwarning("Conflict", f"{hotkey} conflicts with a system hotkey")
                return
            # Check against other profiles
            if self._profile_store:
                for p in self._profile_store.load():
                    if self._editing and p.id == self._editing.id:
                        continue
                    if p.hotkey and p.hotkey.lower() == hk_lower:
                        messagebox.showwarning("Conflict", f"{hotkey} is used by profile '{p.name}'")
                        return

        # Warn about unreachable steps after terminal lock
        for i, step in enumerate(self._steps):
            if (step.action == "lock" and step.params.get("duration_ms", 0) == 0
                    and i < len(self._steps) - 1):
                messagebox.showinfo(
                    "Note",
                    f"Step {i+1} is a terminal lock (duration=0). Steps after it will not execute.",
                )
                break

        if self._editing:
            self._editing.name = name
            self._editing.hotkey = hotkey
            self._editing.steps = list(self._steps)
            self.result = self._editing
        else:
            self.result = Profile.create_new(name=name, hotkey=hotkey, steps=list(self._steps))

        self.top.destroy()
```

- [ ] **Step 2: Verify import works**

Run: `py -c "from mouse_lock.ui.step_builder import StepBuilderDialog; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add mouse_lock/ui/step_builder.py
git commit -m "feat: StepBuilderDialog with pick position and validation"
```

---

## Task 13: App wiring — main(), shutdown(), entry point

Create `mouse_lock/app.py` with the full startup sequence, shutdown coordination, and entry point. Remove old `mouse_lock.py`.

**Files:**
- Create: `mouse_lock/app.py`
- Delete: `mouse_lock.py` (the old single file)

- [ ] **Step 1: Create `mouse_lock/app.py`**

```python
"""Application entry point, shutdown, and wiring."""
from __future__ import annotations

from mouse_lock.dpi import init_dpi_awareness
from mouse_lock.state import AppState, make_state
from mouse_lock.profile_store import ProfileStore
from mouse_lock.action_runner import ActionRunner
from mouse_lock.lock_loop import LockLoop
from mouse_lock.hotkeys import HotkeyManager, _shutdown_ref
from mouse_lock.tray import TrayManager


def make_shutdown(
    state: AppState,
    hotkey_mgr: HotkeyManager,
    action_runner: ActionRunner,
    tray_mgr: TrayManager | None,
    root,
) -> callable:
    def shutdown() -> None:
        if state.stop_event.is_set():
            return
        state.stop_event.set()
        action_runner.stop()
        hotkey_mgr.unregister_all()
        if tray_mgr is not None:
            tray_mgr.stop()
        root.after(0, root.destroy)

    return shutdown


def main() -> None:
    import tkinter as tk

    # 1. DPI awareness
    init_dpi_awareness()

    # 2. Shared state
    state = make_state()

    # 3. Tkinter root
    root = tk.Tk()

    # 4. Load profiles
    profile_store = ProfileStore()

    # 5. Action runner
    action_runner = ActionRunner(state)

    # 6. Tray
    tray_mgr = TrayManager(state, root)
    tray_available = tray_mgr.start()
    if not tray_available:
        state.set_status_message("Tray unavailable")

    # 7. Build UI
    from mouse_lock.ui.main_window import MainWindow
    hotkey_mgr = HotkeyManager(state, root, action_runner, profile_store)
    MainWindow(
        root, state, tray_available,
        profile_store=profile_store,
        hotkey_mgr=hotkey_mgr,
        action_runner=action_runner,
    )

    # 8. Hide window if tray available
    if tray_available:
        root.withdraw()

    # 9. Lock loop
    lock_loop = LockLoop(state)
    lock_loop.start()

    # 10. Register hotkeys
    hotkey_mgr.register_all()
    hotkey_mgr.refresh_profile_hotkeys(profile_store.load())

    # 11. Wire shutdown (MUST happen before step 12)
    shutdown_fn = make_shutdown(state, hotkey_mgr, action_runner, tray_mgr if tray_available else None, root)
    _shutdown_ref[0] = shutdown_fn

    # 12. Start hotkey thread
    hotkey_mgr.start()

    # 13. Run
    root.mainloop()
```

- [ ] **Step 2: Delete old `mouse_lock.py`**

```bash
git rm mouse_lock.py
```

- [ ] **Step 3: Verify the app can be launched**

Run: `py -m mouse_lock`
Expected: Window appears (or tray icon appears). Close via CTRL+ALT+ESC or closing the window.

- [ ] **Step 4: Commit**

```bash
git add mouse_lock/app.py
git commit -m "feat: app.py wiring with full startup/shutdown sequence"
```

---

## Task 14: Migrate all remaining tests and run full suite

Ensure all tests import from the new package, clean up old test pycache, and verify everything passes.

**Files:**
- Modify: `tests/test_state.py` (verify imports correct)
- Modify: `tests/test_lock_loop.py` (verify imports correct)
- Modify: `tests/test_hotkeys.py` (verify imports correct)
- Modify: `tests/test_dpi.py` (verify imports correct)
- Modify: `tests/test_icon.py` (verify imports correct)

- [ ] **Step 1: Verify all tests import from `mouse_lock.*` not `mouse_lock`**

Check that no test file contains `from mouse_lock import` (old single-file style). All should use `from mouse_lock.module import`.

- [ ] **Step 2: Delete old pycache**

```bash
rm -rf __pycache__ tests/__pycache__
```

- [ ] **Step 3: Run full test suite**

Run: `py -m pytest tests/ -v`
Expected: All tests PASS. Count should be approximately:
- test_constants: 2
- test_models: 11
- test_state: 13
- test_cursor: 9
- test_profile_store: 9
- test_lock_loop: 6
- test_action_runner: 11
- test_hotkeys: 10
- test_dpi: 1
- test_icon: 3
Total: ~75 tests

- [ ] **Step 4: Run app manually to verify**

Run: `py -m mouse_lock`
Test: Save position, move, toggle lock, add a profile with a few steps, run it.

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "chore: migrate all tests to package imports, full suite green"
```

---

## Summary

| Task | Module | Tests |
|---|---|---|
| 1 | Package scaffold + constants | 2 |
| 2 | DPI + icon extraction | 4 |
| 3 | Data models | 11 |
| 4 | AppState extraction + extension | 13 |
| 5 | Cursor operations | 9 |
| 6 | ProfileStore | 9 |
| 7 | LockLoop extraction + chain_lock | 6 |
| 8 | ActionRunner | 11 |
| 9 | HotkeyManager extraction + extension | 10 |
| 10 | TrayManager extraction | 0 (visual) |
| 11 | MainWindow UI | 0 (visual) |
| 12 | StepBuilderDialog | 0 (visual) |
| 13 | App wiring + entry point | 0 (integration) |
| 14 | Final migration + full suite | ~75 total |
