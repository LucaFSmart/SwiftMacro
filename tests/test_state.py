from mouse_lock.state import make_state


def test_initial_state():
    s = make_state()
    assert s.get_saved_pos() is None
    assert s.get_lock_active() is False
    assert s.get_status_message() == ""
    assert s.get_hotkey_errors() == []
    assert s.get_active_profile_id() is None
    assert s.get_runner_busy() is False
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None


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


def test_active_profile_id():
    s = make_state()
    s.set_active_profile_id("abc-123")
    assert s.get_active_profile_id() == "abc-123"


def test_runner_busy():
    s = make_state()
    s.set_runner_busy(True)
    assert s.get_runner_busy() is True
    s.set_runner_busy(False)
    assert s.get_runner_busy() is False


def test_chain_lock():
    s = make_state()
    s.set_chain_lock(True, (500, 300))
    active, pos = s.get_chain_lock()
    assert active is True
    assert pos == (500, 300)


def test_chain_lock_reset():
    s = make_state()
    s.set_chain_lock(True, (500, 300))
    s.set_chain_lock(False)
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None
