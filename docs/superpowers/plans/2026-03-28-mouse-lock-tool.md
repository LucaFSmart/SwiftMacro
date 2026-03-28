# Mouse Lock Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop tray utility that saves a mouse position and snaps/locks the cursor to it via global hotkeys.

**Architecture:** Single script `mouse_lock.py` with four concurrent layers (main/UI thread, hotkey thread, lock-loop thread, tray thread). All shared state lives in `AppState` behind a `threading.Lock`. All cross-thread Tkinter calls go through `root.after()`.

**Tech Stack:** Python 3.10+, `tkinter` (stdlib), `ctypes` (stdlib), `keyboard`, `pystray`, `Pillow`

**Spec:** `docs/superpowers/specs/2026-03-28-mouse-lock-tool-design.md`

---

## File Map

| File | Role |
|---|---|
| `mouse_lock.py` | Full application — constants, AppState, DPI init, icon, LockLoop, HotkeyManager, TrayManager, AppUI, main() |
| `requirements.txt` | `keyboard`, `pystray`, `Pillow` |
| `README.md` | Setup and usage instructions |
| `tests/test_app_state.py` | Unit tests for AppState methods |
| `tests/test_dpi.py` | Smoke test for DPI init (no crash) |
| `tests/test_icon.py` | Unit test for tray icon generation |
| `tests/test_lock_loop.py` | Unit tests for LockLoop thread behaviour |
| `tests/test_hotkey_manager.py` | Unit tests for HotkeyManager error handling, save action, GetCursorPos |
| `tests/conftest.py` | Shared fixtures |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
keyboard
pystray
Pillow
pytest
```

- [ ] **Step 2: Create empty test package**

```python
# tests/__init__.py
# (empty)
```

- [ ] **Step 3: Create conftest.py**

```python
# tests/conftest.py
import pytest

@pytest.fixture
def stop_event():
    import threading
    e = threading.Event()
    yield e
    e.set()
```

- [ ] **Step 4: Install dependencies**

Run: `pip install keyboard pystray Pillow pytest`

- [ ] **Step 5: Verify pytest runs (no tests yet)**

Run: `pytest tests/ -v`
Expected: `no tests ran`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/
git commit -m "chore: project setup — requirements and test scaffolding"
```

---

## Task 2: AppState

**Files:**
- Create: `mouse_lock.py` (initial skeleton — constants + AppState only)
- Create: `tests/test_app_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_app_state.py
import threading
import pytest
from mouse_lock import AppState


def make_state():
    return AppState(
        saved_pos=None,
        lock_active=False,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        _lock=threading.Lock(),
    )


def test_initial_state():
    s = make_state()
    assert s.get_saved_pos() is None
    assert s.get_lock_active() is False
    assert s.get_status_message() == ""
    assert s.get_hotkey_errors() == []


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
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_app_state.py -v`
Expected: `ImportError` or `ModuleNotFoundError` (mouse_lock doesn't exist yet)

- [ ] **Step 3: Create mouse_lock.py with constants and AppState**

```python
"""
Mouse Position Lock Tool
Windows desktop utility to save and restore cursor position via hotkeys.
"""
from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HOTKEY_SAVE       = "ctrl+alt+s"
HOTKEY_MOVE       = "ctrl+alt+m"
HOTKEY_TOGGLE     = "ctrl+alt+t"
HOTKEY_EXIT       = "ctrl+alt+esc"
LOCK_INTERVAL_MS  = 15    # milliseconds between lock-loop cursor corrections
UI_POLL_MS        = 200   # milliseconds between UI refresh cycles
ICON_SIZE         = 64    # tray icon size in pixels


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
@dataclass
class AppState:
    saved_pos: tuple[int, int] | None
    lock_active: bool
    stop_event: threading.Event
    hotkey_errors: list[str]
    status_message: str
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
        """Toggle lock state. Returns the new value."""
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


def make_state() -> AppState:
    """Factory — creates a fresh AppState with sensible defaults."""
    return AppState(
        saved_pos=None,
        lock_active=False,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        _lock=threading.Lock(),
    )
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_app_state.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mouse_lock.py tests/test_app_state.py
git commit -m "feat: AppState with thread-safe getters/setters"
```

---

## Task 3: DPI Awareness

**Files:**
- Modify: `mouse_lock.py` — add `init_dpi_awareness()`
- Create: `tests/test_dpi.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_dpi.py
def test_init_dpi_awareness_does_not_crash():
    """DPI init must never raise, regardless of OS support."""
    from mouse_lock import init_dpi_awareness
    init_dpi_awareness()  # must not raise
```

- [ ] **Step 2: Run test — verify it fails**

Run: `pytest tests/test_dpi.py -v`
Expected: `ImportError` — `init_dpi_awareness` not defined

- [ ] **Step 3: Add init_dpi_awareness to mouse_lock.py** (after constants, before AppState)

```python
# ---------------------------------------------------------------------------
# DPI awareness
# ---------------------------------------------------------------------------
def init_dpi_awareness() -> None:
    """Best-effort DPI awareness. Tries modern API first, falls back, never crashes."""
    try:
        # Windows 8.1+: per-monitor DPI awareness
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Windows Vista+: system DPI awareness
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass  # silently continue; minor coordinate mismatch possible
```

- [ ] **Step 4: Run test — verify it passes**

Run: `pytest tests/test_dpi.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mouse_lock.py tests/test_dpi.py
git commit -m "feat: DPI awareness init with cascading fallback"
```

---

## Task 4: Tray Icon Generation

**Files:**
- Modify: `mouse_lock.py` — add `create_tray_icon()`
- Create: `tests/test_icon.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_icon.py
from PIL import Image


def test_create_tray_icon_returns_image():
    from mouse_lock import create_tray_icon
    img = create_tray_icon()
    assert isinstance(img, Image.Image)


def test_create_tray_icon_correct_size():
    from mouse_lock import create_tray_icon, ICON_SIZE
    img = create_tray_icon()
    assert img.size == (ICON_SIZE, ICON_SIZE)


def test_create_tray_icon_is_rgba():
    from mouse_lock import create_tray_icon
    img = create_tray_icon()
    assert img.mode == "RGBA"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_icon.py -v`
Expected: `ImportError` — `create_tray_icon` not defined

- [ ] **Step 3: Add create_tray_icon to mouse_lock.py** (after `make_state`)

```python
# ---------------------------------------------------------------------------
# Tray icon (generated at runtime — no image file required)
# ---------------------------------------------------------------------------
def create_tray_icon():
    """Draw a crosshair/target symbol on a dark background. Returns a PIL Image."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    r = ICON_SIZE // 2 - 4
    # Outer circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 100, 255), width=2)
    # Inner dot
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(0, 200, 100, 255))
    # Crosshair lines
    draw.line([(cx - r, cy), (cx - 6, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx + 6, cy), (cx + r, cy)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy - r), (cx, cy - 6)], fill=(0, 200, 100, 255), width=1)
    draw.line([(cx, cy + 6), (cx, cy + r)], fill=(0, 200, 100, 255), width=1)
    return img
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_icon.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mouse_lock.py tests/test_icon.py
git commit -m "feat: runtime tray icon generation with Pillow"
```

---

## Task 5: LockLoop

**Files:**
- Modify: `mouse_lock.py` — add `LockLoop` class
- Create: `tests/test_lock_loop.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lock_loop.py
import threading
import time
from unittest.mock import patch, call
from mouse_lock import AppState, LockLoop


def make_state(saved_pos=None, lock_active=False):
    return AppState(
        saved_pos=saved_pos,
        lock_active=lock_active,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        _lock=threading.Lock(),
    )


def test_lock_loop_exits_on_stop_event():
    state = make_state()
    loop = LockLoop(state)
    t = threading.Thread(target=loop.run, daemon=True)
    t.start()
    state.stop_event.set()
    t.join(timeout=0.5)
    assert not t.is_alive(), "LockLoop did not exit after stop_event was set"


def test_lock_loop_does_not_move_when_inactive():
    state = make_state(saved_pos=(100, 200), lock_active=False)
    with patch("mouse_lock.ctypes") as mock_ctypes:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ctypes.windll.user32.SetCursorPos.assert_not_called()


def test_lock_loop_moves_when_active():
    state = make_state(saved_pos=(100, 200), lock_active=True)
    calls = []

    def fake_set_cursor_pos(x, y):
        calls.append((x, y))

    with patch("mouse_lock.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.SetCursorPos.side_effect = fake_set_cursor_pos
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (100, 200)


def test_lock_loop_does_not_move_without_saved_pos():
    state = make_state(saved_pos=None, lock_active=True)
    with patch("mouse_lock.ctypes") as mock_ctypes:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ctypes.windll.user32.SetCursorPos.assert_not_called()
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_lock_loop.py -v`
Expected: `ImportError` — `LockLoop` not defined

- [ ] **Step 3: Add LockLoop to mouse_lock.py**

```python
# ---------------------------------------------------------------------------
# Lock loop — daemon thread that holds cursor at saved position
# ---------------------------------------------------------------------------
class LockLoop:
    """Continuously moves cursor to saved_pos while lock_active is True."""

    def __init__(self, state: AppState) -> None:
        self._state = state

    def run(self) -> None:
        """Thread entry point. Exits when stop_event is set."""
        while not self._state.stop_event.is_set():
            if self._state.get_lock_active():
                pos = self._state.get_saved_pos()
                if pos is not None:
                    try:
                        ctypes.windll.user32.SetCursorPos(pos[0], pos[1])
                    except Exception:
                        pass  # non-critical; next iteration will retry
            # Fast-exit sleep: wakes immediately when stop_event is set
            self._state.stop_event.wait(timeout=LOCK_INTERVAL_MS / 1000.0)

    def start(self) -> threading.Thread:
        """Spawn and return the daemon thread."""
        t = threading.Thread(target=self.run, name="LockLoop", daemon=True)
        t.start()
        return t
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_lock_loop.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mouse_lock.py tests/test_lock_loop.py
git commit -m "feat: LockLoop daemon thread with stop_event.wait sleep"
```

---

## Task 6: HotkeyManager

**Files:**
- Modify: `mouse_lock.py` — add `HotkeyManager` class
- Create: `tests/test_hotkey_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_hotkey_manager.py
import threading
from unittest.mock import patch, MagicMock
from mouse_lock import AppState, HotkeyManager


def make_state():
    return AppState(
        saved_pos=None,
        lock_active=False,
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        _lock=threading.Lock(),
    )


def test_failed_hotkey_registration_stored_in_state():
    state = make_state()
    root_mock = MagicMock()

    def bad_add_hotkey(combo, callback, **kwargs):
        raise Exception(f"Cannot register {combo}")

    with patch("keyboard.add_hotkey", side_effect=bad_add_hotkey):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    errors = state.get_hotkey_errors()
    assert len(errors) == 4  # all four hotkeys failed
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

    errors = state.get_hotkey_errors()
    assert len(errors) == 1  # only one failed


def test_unregister_all_ignores_errors():
    state = make_state()
    root_mock = MagicMock()

    with patch("keyboard.add_hotkey"):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    with patch("keyboard.remove_hotkey", side_effect=Exception("remove failed")):
        hm.unregister_all()  # must not raise


def test_on_save_captures_cursor_position():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    with patch.object(HotkeyManager, "_get_cursor_pos", return_value=(42, 99)):
        hm._on_save()

    assert state.get_saved_pos() == (42, 99)
    assert state.get_status_message() == "Position saved"


def test_get_cursor_pos_returns_none_on_failure():
    """_get_cursor_pos must return None rather than raise when Win32 fails."""
    with patch("mouse_lock.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.GetCursorPos.side_effect = Exception("win32 error")
        mock_ctypes.Structure = __import__("ctypes").Structure
        mock_ctypes.c_long = __import__("ctypes").c_long
        mock_ctypes.byref = __import__("ctypes").byref
        result = HotkeyManager._get_cursor_pos()
    assert result is None
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `pytest tests/test_hotkey_manager.py -v`
Expected: `ImportError` — `HotkeyManager` not defined

- [ ] **Step 3: Add HotkeyManager to mouse_lock.py**

```python
# ---------------------------------------------------------------------------
# Hotkey manager
# ---------------------------------------------------------------------------
class HotkeyManager:
    """Registers and manages global hotkeys. Failures are stored, not raised."""

    def __init__(self, state: AppState, root) -> None:
        self._state = state
        self._root = root          # Tkinter root — for root.after() calls
        self._registered: list[str] = []

    def register_all(self) -> None:
        """Register all four hotkeys. Each failure is stored in state."""
        import keyboard

        bindings = [
            (HOTKEY_SAVE,   self._on_save),
            (HOTKEY_MOVE,   self._on_move),
            (HOTKEY_TOGGLE, self._on_toggle),
            (HOTKEY_EXIT,   self._on_exit),
        ]
        for combo, callback in bindings:
            try:
                keyboard.add_hotkey(combo, callback, suppress=False)
                self._registered.append(combo)
            except Exception as exc:
                self._state.add_hotkey_error(f"{combo}: {exc}")

    def unregister_all(self) -> None:
        """Unregister all successfully registered hotkeys. Errors are ignored."""
        import keyboard
        for combo in self._registered:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._registered.clear()

    def start(self) -> threading.Thread:
        """Spawn daemon thread that keeps the keyboard hook alive."""
        import keyboard
        t = threading.Thread(target=keyboard.wait, name="HotkeyThread", daemon=True)
        t.start()
        return t

    # --- callbacks (run on hotkey thread) ---

    def _on_save(self) -> None:
        pos = self._get_cursor_pos()
        if pos:
            self._state.set_saved_pos(pos)
        # UI polling loop refreshes automatically every UI_POLL_MS; no extra call needed

    def _on_move(self) -> None:
        pos = self._state.get_saved_pos()
        if pos is None:
            self._state.set_status_message("No position saved")
            return
        try:
            ctypes.windll.user32.SetCursorPos(pos[0], pos[1])
        except Exception:
            self._state.set_status_message("Move failed")

    def _on_toggle(self) -> None:
        self._state.toggle_lock()

    def _on_exit(self) -> None:
        self._root.after(0, _shutdown_ref[0])  # _shutdown_ref set in main()

    @staticmethod
    def _get_cursor_pos() -> tuple[int, int] | None:
        """Read current cursor position via Win32 GetCursorPos."""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        try:
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return (pt.x, pt.y)
        except Exception:
            return None


# Mutable reference so HotkeyManager can call shutdown() without a circular import
_shutdown_ref: list = [lambda: None]
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/test_hotkey_manager.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mouse_lock.py tests/test_hotkey_manager.py
git commit -m "feat: HotkeyManager with per-hotkey error handling"
```

---

## Task 7: TrayManager

**Files:**
- Modify: `mouse_lock.py` — add `TrayManager` + `show_window`

No unit tests for TrayManager — it wraps `pystray` tightly and would require a headless display. Manual verification in Task 9.

- [ ] **Step 1: Add show_window and TrayManager to mouse_lock.py**

```python
# ---------------------------------------------------------------------------
# show_window helper (called on main thread via root.after)
# ---------------------------------------------------------------------------
def show_window(root) -> None:
    """Restore and bring the Tkinter window to the foreground."""
    root.deiconify()
    root.lift()
    root.focus_force()


# ---------------------------------------------------------------------------
# Tray manager
# ---------------------------------------------------------------------------
class TrayManager:
    """Manages the system tray icon and right-click menu."""

    def __init__(self, state: AppState, root) -> None:
        self._state = state
        self._root = root
        self._icon = None

    def start(self) -> bool:
        """
        Create and start the tray icon in its own thread.
        Returns True on success, False on failure.
        """
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
                name="MouseLock",
                icon=icon_image,
                title="Mouse Lock",
                menu=menu,
            )

            # Double-click restores window
            self._icon.default_action = lambda icon, item: self._root.after(
                0, lambda: show_window(self._root)
            )

            # Run tray in its own daemon thread
            t = threading.Thread(target=self._icon.run, name="TrayThread", daemon=True)
            t.start()
            return True

        except Exception:
            return False

    def stop(self) -> None:
        """Stop the tray icon. Errors ignored."""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

Run: `pytest tests/ -v`
Expected: All previous tests still PASS

- [ ] **Step 3: Commit**

```bash
git add mouse_lock.py
git commit -m "feat: TrayManager with pystray icon, menu, and double-click handler"
```

---

## Task 8: AppUI

**Files:**
- Modify: `mouse_lock.py` — add `AppUI` class

- [ ] **Step 1: Add AppUI to mouse_lock.py**

```python
# ---------------------------------------------------------------------------
# Application UI
# ---------------------------------------------------------------------------
class AppUI:
    """
    Tkinter window (~300x220px). Polls AppState every UI_POLL_MS ms.
    All state reads go through AppState getters (thread-safe).
    """

    def __init__(self, root, state: AppState, tray_available: bool) -> None:
        import tkinter as tk

        self._root = root
        self._state = state
        self._tray_available = tray_available

        root.title("Mouse Lock")
        root.resizable(False, False)
        root.geometry("300x220")

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
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save Position",  width=13, command=self._cmd_save).grid(row=0, column=0, padx=4)
        tk.Button(btn_frame, text="Move Now",       width=10, command=self._cmd_move).grid(row=0, column=1, padx=4)
        tk.Button(btn_frame, text="Toggle Lock",    width=11, command=self._cmd_toggle).grid(row=0, column=2, padx=4)

        # --- Hotkey error banner (hidden until needed) ---
        self._error_frame = tk.Frame(root, bg="#ffcccc")
        self._error_label = tk.Label(self._error_frame, text="", bg="#ffcccc", fg="#990000",
                                     anchor="w", justify="left", wraplength=280)
        self._error_label.pack(padx=6, pady=4, fill="x")

        # --- Close / delete window behaviour ---
        if tray_available:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)  # minimize to tray
        else:
            root.protocol("WM_DELETE_WINDOW", lambda: _shutdown_ref[0]())

        # Start polling
        root.after(UI_POLL_MS, self._poll)

    # --- Button commands (run on main thread) ---

    def _cmd_save(self) -> None:
        pos = HotkeyManager._get_cursor_pos()
        if pos:
            self._state.set_saved_pos(pos)

    def _cmd_move(self) -> None:
        pos = self._state.get_saved_pos()
        if pos is None:
            self._state.set_status_message("No position saved")
            return
        try:
            ctypes.windll.user32.SetCursorPos(pos[0], pos[1])
        except Exception:
            self._state.set_status_message("Move failed")

    def _cmd_toggle(self) -> None:
        self._state.toggle_lock()

    # --- Polling ---

    def _poll(self) -> None:
        """Refresh UI labels from AppState. Reschedules itself unless shutting down."""
        if self._state.stop_event.is_set():
            return  # do not reschedule after shutdown

        # Update position label
        pos = self._state.get_saved_pos()
        self._pos_label.config(
            text=f"X: {pos[0]},  Y: {pos[1]}" if pos else "Not set",
            fg="black" if pos else "gray",
        )

        # Update lock label
        active = self._state.get_lock_active()
        self._lock_label.config(
            text="Lock Active" if active else "Unlocked",
            fg="red" if active else "gray",
        )

        # Update transient status
        self._status_label.config(text=self._state.get_status_message())

        # Update error banner
        errors = self._state.get_hotkey_errors()
        if errors:
            self._error_label.config(text="\n".join(errors))
            self._error_frame.pack(fill="x", padx=10)
        else:
            self._error_frame.pack_forget()

        self._root.after(UI_POLL_MS, self._poll)
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS (AppUI has no unit tests — UI logic is thin)

- [ ] **Step 3: Commit**

```bash
git add mouse_lock.py
git commit -m "feat: AppUI with polling, buttons, status messages, error banner"
```

---

## Task 9: Wiring — shutdown() and main()

**Files:**
- Modify: `mouse_lock.py` — add `shutdown()` and `main()`

- [ ] **Step 1: Add shutdown() and main() to mouse_lock.py**

```python
# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------
def make_shutdown(state: AppState, hotkey_mgr: HotkeyManager,
                  tray_mgr: TrayManager | None, root) -> callable:
    """
    Factory that returns the shutdown function. Stored in _shutdown_ref so
    HotkeyManager and TrayManager can call it without circular references.
    """
    def shutdown() -> None:
        if state.stop_event.is_set():
            return  # already shutting down — no-op
        state.stop_event.set()
        hotkey_mgr.unregister_all()
        if tray_mgr is not None:
            tray_mgr.stop()
        root.after(0, root.destroy)

    return shutdown


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    import tkinter as tk

    # 1. DPI awareness — must be first
    init_dpi_awareness()

    # 2. Shared state
    state = make_state()

    # 3. Tkinter root (do NOT call mainloop yet)
    root = tk.Tk()

    # 4. Tray
    tray_mgr = TrayManager(state, root)
    tray_available = tray_mgr.start()
    if not tray_available:
        state.set_status_message("Tray unavailable")

    # 5. Build UI (must happen after tray_available is known)
    AppUI(root, state, tray_available)

    # 5b. Hide window only if tray is available
    if tray_available:
        root.withdraw()

    # 6. Lock loop — started before hotkeys so lock is ready if user hits CTRL+ALT+T immediately
    lock_loop = LockLoop(state)
    lock_loop.start()

    # 7. Wire shutdown BEFORE starting hotkey thread — prevents window where
    #    CTRL+ALT+ESC fires before _shutdown_ref is populated
    hotkey_mgr = HotkeyManager(state, root)
    hotkey_mgr.register_all()
    shutdown_fn = make_shutdown(state, hotkey_mgr, tray_mgr if tray_available else None, root)
    _shutdown_ref[0] = shutdown_fn
    hotkey_mgr.start()  # start AFTER _shutdown_ref is set

    # 8. Run — blocks until shutdown
    root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Manual smoke test — launch the app**

Run: `python mouse_lock.py`

Verify:
- App starts; tray icon appears in notification area
- Double-click tray icon → window appears
- "Save Position" button captures current position; status shows "Position saved"
- Move mouse, press CTRL+ALT+M → cursor snaps back
- "Toggle Lock" → cursor stays fixed; moving mouse returns it
- Tray right-click → menu has Show UI / Lock / Exit
- Window X button → window hides (does not close)
- Tray "Exit" → app closes cleanly
- CTRL+ALT+ESC → app closes cleanly

- [ ] **Step 4: Commit**

```bash
git add mouse_lock.py
git commit -m "feat: shutdown() and main() — full wiring of all components"
```

---

## Task 10: requirements.txt and README

**Files:**
- Modify: `requirements.txt` — pin or verify versions
- Create: `README.md`

- [ ] **Step 1: Verify final requirements.txt**

```
keyboard>=0.13.5
pystray>=0.19.4
Pillow>=9.0.0
pytest>=7.0.0
```

- [ ] **Step 2: Create README.md**

```markdown
# Mouse Lock Tool

A Windows desktop tray utility to save a mouse position and snap or lock the cursor to it.

## Setup

```bash
pip install keyboard pystray Pillow
```

## Run

```bash
python mouse_lock.py
```

The app starts minimized to the system tray (notification area, bottom-right).

## Usage

| Action | Hotkey | UI Button |
|---|---|---|
| Save current cursor position | CTRL+ALT+S | Save Position |
| Move cursor to saved position | CTRL+ALT+M | Move Now |
| Toggle cursor lock on/off | CTRL+ALT+T | Toggle Lock |
| Emergency exit | CTRL+ALT+ESC | Tray → Exit |

**Cursor Lock:** When active, the cursor is continuously forced back to the saved position (~15ms interval). Move the mouse freely to disable the effect — toggle lock off first.

**System Tray:**
- Double-click tray icon → open window
- Right-click → Show UI / Lock / Exit
- Closing the window minimizes to tray (does not exit)

## Run Tests

```bash
pytest tests/ -v
```

## Requirements

- Windows 10 or 11
- Python 3.10+
- Run as standard user (no admin rights needed for most hotkey registrations)
```

- [ ] **Step 3: Run full test suite one final time**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Final commit**

```bash
git add requirements.txt README.md
git commit -m "docs: README with setup, usage, and hotkey reference"
```

---

## Definition of Done

- [ ] `pytest tests/ -v` — all tests pass
- [ ] App launches; tray icon appears
- [ ] All 3 hotkeys work (save / move / toggle)
- [ ] CTRL+ALT+ESC exits cleanly
- [ ] Window close minimizes to tray
- [ ] Tray exit closes app
- [ ] Hotkey error banner appears if registration fails (test by running without admin on restricted system)
- [ ] Lock loop holds cursor without high CPU (verify in Task Manager)
