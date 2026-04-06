"""Application startup and shutdown wiring."""
from __future__ import annotations

import threading
import typing

from swiftmacro.action_runner import ActionRunner
from swiftmacro.constants import APP_ID, APP_MUTEX_NAME
from swiftmacro.dpi import init_dpi_awareness
from swiftmacro.hotkeys import HotkeyManager
from swiftmacro.icon import apply_window_icon, set_windows_app_id
from swiftmacro.lock_loop import LockLoop
from swiftmacro.profile_manager import ProfileManager
from swiftmacro.profile_store import ProfileStore
from swiftmacro.shutdown import ShutdownCoordinator
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
    profile_store = ProfileStore()
    action_runner = ActionRunner(state)
    shutdown_coordinator = ShutdownCoordinator()

    # Build the tray manager (but DON'T start it yet) so we can wire its
    # shutdown callback before the icon thread is spawned. This eliminates
    # the brief startup window where a tray "Quit" click would arrive at a
    # not-yet-registered coordinator and silently no-op.
    tray_mgr = TrayManager(state, root, shutdown_fn=shutdown_coordinator.trigger)

    hotkey_mgr = HotkeyManager(
        state, root, action_runner, profile_store, shutdown=shutdown_coordinator
    )
    profile_manager = ProfileManager(profile_store, hotkey_mgr)
    action_runner.set_on_run_complete(
        lambda profile: profile_manager.record_run(profile.id)
    )

    lock_loop = LockLoop(state)

    # Build the shutdown callback BEFORE starting any background services so
    # any of them firing immediately (tray, hotkey, hotkey thread, etc.) is
    # routed cleanly through the coordinator.
    def _build_shutdown(tray_active: bool):
        return make_shutdown(
            state,
            hotkey_mgr,
            action_runner,
            lock_loop,
            tray_mgr if tray_active else None,
            instance_guard,
            root,
        )

    # Provisional callback (no tray yet) — overwritten once we know tray state.
    shutdown_coordinator.set_callback(_build_shutdown(tray_active=False))

    tray_available = tray_mgr.start()
    if not tray_available:
        state.set_status_message("Tray unavailable")
    else:
        shutdown_coordinator.set_callback(_build_shutdown(tray_active=True))

    MainWindow(
        root,
        state,
        tray_available,
        profile_store=profile_store,
        hotkey_mgr=hotkey_mgr,
        action_runner=action_runner,
        profile_manager=profile_manager,
        shutdown=shutdown_coordinator,
    )

    threading.Thread(target=_check_update_bg, args=(state,), daemon=True).start()

    lock_loop.start()

    hotkey_mgr.register_all()
    hotkey_mgr.refresh_profile_hotkeys(profile_store.load())

    log.info("Startup complete")
    try:
        root.mainloop()
    finally:
        shutdown_coordinator.trigger()
        log.info("SwiftMacro shut down")
