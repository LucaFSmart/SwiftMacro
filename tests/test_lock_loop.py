import threading
import time
from unittest.mock import patch
from mouse_lock.state import make_state
from mouse_lock.lock_loop import LockLoop


def test_lock_loop_exits_on_stop_event():
    state = make_state()
    loop = LockLoop(state)
    t = threading.Thread(target=loop.run, daemon=True)
    t.start()
    state.stop_event.set()
    t.join(timeout=0.5)
    assert not t.is_alive()


def test_lock_loop_does_not_move_when_inactive():
    state = make_state()
    state.saved_pos = (100, 200)
    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ct.windll.user32.SetCursorPos.assert_not_called()


def test_lock_loop_moves_when_active():
    state = make_state()
    state.saved_pos = (100, 200)
    state.lock_active = True
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (100, 200)


def test_lock_loop_does_not_move_without_saved_pos():
    state = make_state()
    state.lock_active = True
    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)
        mock_ct.windll.user32.SetCursorPos.assert_not_called()


def test_chain_lock_takes_precedence():
    """When chain_lock_active, LockLoop uses chain_lock_pos, not saved_pos."""
    state = make_state()
    state.saved_pos = (100, 200)
    state.lock_active = True
    state.set_chain_lock(True, (500, 300))
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (500, 300)


def test_chain_lock_overrides_inactive_lock():
    """chain_lock works even if lock_active is False."""
    state = make_state()
    state.lock_active = False
    state.set_chain_lock(True, (300, 400))
    calls = []

    with patch("mouse_lock.lock_loop.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = lambda x, y: calls.append((x, y))
        loop = LockLoop(state)
        t = threading.Thread(target=loop.run, daemon=True)
        t.start()
        time.sleep(0.05)
        state.stop_event.set()
        t.join(timeout=0.5)

    assert len(calls) >= 1
    assert calls[0] == (300, 400)
