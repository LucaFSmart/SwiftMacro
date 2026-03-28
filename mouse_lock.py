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


# ---------------------------------------------------------------------------
# Tray icon (generated at runtime — no image file required)
# ---------------------------------------------------------------------------
def create_tray_icon() -> "Image.Image":
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
