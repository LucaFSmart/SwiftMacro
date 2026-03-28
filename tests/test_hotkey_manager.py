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
