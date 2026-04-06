"""System tray icon manager."""
from __future__ import annotations

import threading
from typing import Callable

from swiftmacro.constants import TRAY_STOP_JOIN_TIMEOUT
from swiftmacro.icon import create_tray_icon
from swiftmacro.log import get_logger
from swiftmacro.state import AppState

_log = get_logger("tray")


def show_window(root) -> None:
    """Restore and bring the Tkinter window to the foreground."""
    root.deiconify()
    root.lift()
    root.focus_force()


class TrayManager:
    def __init__(
        self,
        state: AppState,
        root,
        shutdown_fn: Callable[[], None] | None = None,
    ) -> None:
        self._state = state
        self._root = root
        self._icon = None
        self._thread: threading.Thread | None = None
        self._zombie_threads: list[threading.Thread] = []
        self._shutdown_fn: Callable[[], None] = shutdown_fn or (lambda: None)

    def set_shutdown_fn(self, shutdown_fn: Callable[[], None]) -> None:
        """Late-bind the shutdown callback (used by app.py wiring)."""
        self._shutdown_fn = shutdown_fn

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        try:
            import pystray

            icon_image = create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Show UI",
                    lambda icon, item: self._root.after(0, lambda: show_window(self._root)),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Exit",
                    lambda icon, item: self._root.after(0, self._shutdown_fn),
                ),
            )
            self._icon = pystray.Icon(
                name="SwiftMacro",
                icon=icon_image,
                title="SwiftMacro",
                menu=menu,
            )
            self._icon.default_action = lambda icon, item: self._root.after(
                0, lambda: show_window(self._root)
            )
            self._thread = threading.Thread(target=self._icon.run, name="TrayThread", daemon=True)
            self._thread.start()
            return True
        except Exception as exc:
            _log.warning("Failed to start tray icon: %s", exc)
            return False

    def stop(self, timeout: float = TRAY_STOP_JOIN_TIMEOUT) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as exc:
                _log.debug("pystray.Icon.stop() raised: %s", exc)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                _log.warning(
                    "Tray thread did not exit within %.1fs — daemon thread will be terminated on process exit",
                    timeout,
                )
                # Track for diagnostics; do NOT clear the reference so a
                # subsequent start() can detect the lingering thread.
                self._zombie_threads.append(self._thread)
            else:
                self._thread = None
