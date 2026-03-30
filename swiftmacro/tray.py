"""System tray icon manager."""
from __future__ import annotations

import threading

from swiftmacro.hotkeys import _shutdown_ref
from swiftmacro.icon import create_tray_icon
from swiftmacro.state import AppState


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
        self._thread: threading.Thread | None = None

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
                    lambda icon, item: self._root.after(0, _shutdown_ref[0]),
                ),
            )
            self._icon = pystray.Icon(
                name="MouseLock",
                icon=icon_image,
                title="Mouse Lock",
                menu=menu,
            )
            self._icon.default_action = lambda icon, item: self._root.after(
                0, lambda: show_window(self._root)
            )
            self._thread = threading.Thread(target=self._icon.run, name="TrayThread", daemon=True)
            self._thread.start()
            return True
        except Exception:
            return False

    def stop(self, timeout: float = 2.0) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
