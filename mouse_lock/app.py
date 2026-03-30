"""Application startup and shutdown wiring."""
from __future__ import annotations

from mouse_lock.action_runner import ActionRunner
from mouse_lock.constants import APP_ID, APP_MUTEX_NAME
from mouse_lock.dpi import init_dpi_awareness
from mouse_lock.hotkeys import HotkeyManager, _shutdown_ref
from mouse_lock.icon import apply_window_icon, set_windows_app_id
from mouse_lock.lock_loop import LockLoop
from mouse_lock.profile_store import ProfileStore
from mouse_lock.single_instance import SingleInstanceGuard, acquire_single_instance
from mouse_lock.state import AppState, make_state
from mouse_lock.tray import TrayManager
from mouse_lock.ui.main_window import MainWindow


def make_shutdown(
    state: AppState,
    hotkey_mgr: HotkeyManager,
    action_runner: ActionRunner,
    lock_loop: LockLoop,
    tray_mgr: TrayManager | None,
    instance_guard: SingleInstanceGuard,
    root,
) -> callable:
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


def main() -> None:
    init_dpi_awareness()
    set_windows_app_id(APP_ID)
    instance_guard = acquire_single_instance(APP_MUTEX_NAME)
    if instance_guard.already_running:
        instance_guard.release()
        return

    import tkinter as tk

    state = make_state()
    root = tk.Tk()
    apply_window_icon(root)
    profile_store = ProfileStore()
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
    try:
        root.mainloop()
    finally:
        shutdown_fn()
