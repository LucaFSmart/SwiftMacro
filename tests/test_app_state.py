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
