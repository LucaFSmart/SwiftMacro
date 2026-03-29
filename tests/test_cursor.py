import threading
from unittest.mock import patch, MagicMock
from mouse_lock.cursor import get_cursor_pos, set_cursor_pos, click, repeat_click


def test_get_cursor_pos_success():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.Structure = __import__("ctypes").Structure
        mock_ct.c_long = __import__("ctypes").c_long
        mock_ct.byref = __import__("ctypes").byref

        def fake_get(pt_ref):
            pt = pt_ref._obj if hasattr(pt_ref, '_obj') else pt_ref
            pt.x = 42
            pt.y = 99

        mock_ct.windll.user32.GetCursorPos.side_effect = fake_get
        result = get_cursor_pos()
    assert result == (42, 99)


def test_get_cursor_pos_returns_none_on_failure():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.Structure = __import__("ctypes").Structure
        mock_ct.c_long = __import__("ctypes").c_long
        mock_ct.byref = __import__("ctypes").byref
        mock_ct.windll.user32.GetCursorPos.side_effect = Exception("fail")
        result = get_cursor_pos()
    assert result is None


def test_set_cursor_pos_success():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        assert set_cursor_pos(100, 200) is True
        mock_ct.windll.user32.SetCursorPos.assert_called_once_with(100, 200)


def test_set_cursor_pos_failure():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = Exception("fail")
        assert set_cursor_pos(100, 200) is False


def test_click_calls_mouse_event():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        result = click("left", 100, 200)
    assert result is True
    assert mock_ct.windll.user32.SetCursorPos.called
    assert mock_ct.windll.user32.mouse_event.call_count == 2  # down + up


def test_click_right_button():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        result = click("right", 50, 60)
    assert result is True


def test_click_failure_returns_false():
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.side_effect = Exception("fail")
        result = click("left", 100, 200)
    assert result is False


def test_repeat_click_counts():
    stop = threading.Event()
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        completed = repeat_click("left", 100, 200, count=3, interval_ms=10, stop_event=stop)
    assert completed == 3


def test_repeat_click_interrupted():
    stop = threading.Event()
    stop.set()  # pre-set: should stop immediately
    with patch("mouse_lock.cursor.ctypes") as mock_ct:
        mock_ct.windll.user32.SetCursorPos.return_value = 1
        mock_ct.windll.user32.mouse_event.return_value = None
        completed = repeat_click("left", 100, 200, count=100, interval_ms=10, stop_event=stop)
    assert completed < 100
