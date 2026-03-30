from unittest.mock import MagicMock

from swiftmacro.app import make_shutdown
from swiftmacro.state import make_state


def test_ui_modules_import():
    from swiftmacro.app import main
    from swiftmacro.tray import TrayManager
    from swiftmacro.ui.main_window import MainWindow
    from swiftmacro.ui.step_builder import StepBuilderDialog

    assert main is not None
    assert TrayManager is not None
    assert MainWindow is not None
    assert StepBuilderDialog is not None


def test_make_shutdown_is_idempotent():
    state = make_state()
    hotkey_mgr = MagicMock()
    action_runner = MagicMock()
    lock_loop = MagicMock()
    tray_mgr = MagicMock()
    instance_guard = MagicMock()
    root = MagicMock()

    shutdown = make_shutdown(
        state, hotkey_mgr, action_runner, lock_loop, tray_mgr, instance_guard, root
    )
    shutdown()
    shutdown()

    assert state.stop_event.is_set() is True
    action_runner.stop.assert_called_once()
    hotkey_mgr.unregister_all.assert_called_once()
    lock_loop.stop.assert_called_once()
    tray_mgr.stop.assert_called_once()
    instance_guard.release.assert_called()
    root.after.assert_called_once()
