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
