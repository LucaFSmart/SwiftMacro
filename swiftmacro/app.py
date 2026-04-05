"""Application startup and shutdown wiring."""
from __future__ import annotations

import threading
import typing

from swiftmacro.action_runner import ActionRunner
from swiftmacro.constants import APP_ID, APP_MUTEX_NAME
from swiftmacro.dpi import init_dpi_awareness
from swiftmacro.hotkeys import HotkeyManager, _shutdown_ref
from swiftmacro.icon import apply_window_icon, set_windows_app_id
from swiftmacro.lock_loop import LockLoop
from swiftmacro.profile_store import ProfileStore
from swiftmacro.single_instance import SingleInstanceGuard, acquire_single_instance
from swiftmacro.state import AppState, make_state
from swiftmacro.tray import TrayManager
from swiftmacro.ui.main_window import MainWindow


def make_shutdown(
    state: AppState,
    hotkey_mgr: HotkeyManager,
    action_runner: ActionRunner,
    lock_loop: LockLoop,
    tray_mgr: TrayManager | None,
    instance_guard: SingleInstanceGuard,
    root,
) -> typing.Callable[[], None]:
    def destroy_root() -> None:
        try:
            root.quit()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    def shutdown() -> None:
        if state.stop_event.is_set():
            instance_guard.release()
            return
        state.stop_event.set()
        action_runner.stop()
        hotkey_mgr.unregister_all()
        lock_loop.stop()
        if tray_mgr is not None:
            tray_mgr.stop()
        instance_guard.release()
        try:
            root.after(0, destroy_root)
        except Exception:
            destroy_root()

    return shutdown


def _check_update_bg(state: AppState) -> None:
    """Background thread: check GitHub for a newer release and update AppState."""
    from swiftmacro import updater
    from swiftmacro.constants import APP_VERSION, GITHUB_REPO
    available, url = updater.check_for_update(GITHUB_REPO, APP_VERSION)
    if available:
        state.set_update_available(url)


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
    profile_store = ProfileStore()  # migration runs here in Task 6
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

    threading.Thread(target=_check_update_bg, args=(state,), daemon=True).start()

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
