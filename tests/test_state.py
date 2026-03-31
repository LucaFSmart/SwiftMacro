import threading
import time

from swiftmacro.state import make_state


def test_initial_state():
    s = make_state()
    assert s.get_status_message() == ""
    assert s.get_hotkey_errors() == []
    assert s.get_active_profile_id() is None
    assert s.get_runner_busy() is False
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None


def test_set_status_message():
    s = make_state()
    s.set_status_message("hello")
    assert s.get_status_message() == "hello"


def test_add_hotkey_error():
    s = make_state()
    s.add_hotkey_error("ctrl+alt+r failed")
    assert "ctrl+alt+r failed" in s.get_hotkey_errors()


def test_add_multiple_hotkey_errors():
    s = make_state()
    s.add_hotkey_error("err1")
    s.add_hotkey_error("err2")
    assert len(s.get_hotkey_errors()) == 2


def test_set_hotkey_errors_replaces_existing_list():
    s = make_state()
    s.add_hotkey_error("old")
    s.set_hotkey_errors(["new1", "new2"])
    assert s.get_hotkey_errors() == ["new1", "new2"]


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


def test_set_chain_lock_atomic():
    """Both fields must be readable together consistently after set_chain_lock."""
    s = make_state()
    s.set_chain_lock(True, (123, 456))
    active, pos = s.get_chain_lock()
    assert active is True
    assert pos == (123, 456)
    # Reset — pass pos explicitly (pos has a default of None in state.py but be explicit)
    s.set_chain_lock(False, None)
    active, pos = s.get_chain_lock()
    assert active is False
    assert pos is None


def test_concurrent_state_access():
    """10 threads reading and writing simultaneously must not deadlock within 5s."""
    s = make_state()
    errors = []

    def worker(i):
        try:
            for _ in range(50):
                s.set_status_message(f"thread-{i}")
                _ = s.get_status_message()
                s.set_chain_lock(i % 2 == 0, (i, i))
                _ = s.get_chain_lock()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    alive = [t for t in threads if t.is_alive()]
    assert alive == [], f"{len(alive)} threads still running — possible deadlock"
    assert errors == [], f"Errors during concurrent access: {errors}"


def test_stop_event_propagates():
    """stop_event.set() in one thread must be observed from another thread."""
    s = make_state()
    observed = []

    def waiter():
        # wait up to 1s for the event
        s.stop_event.wait(timeout=1.0)
        observed.append(s.stop_event.is_set())

    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.05)
    s.stop_event.set()
    t.join(timeout=2.0)

    assert observed == [True]


def test_chain_progress_initial():
    s = make_state()
    assert s.get_chain_progress() == (0, 0)


def test_set_chain_progress():
    s = make_state()
    s.set_chain_progress(3, 8)
    assert s.get_chain_progress() == (3, 8)


def test_set_runner_busy_true_resets_progress():
    s = make_state()
    s.set_chain_progress(5, 8)
    s.set_runner_busy(True)
    assert s.get_chain_progress() == (0, 0)


def test_set_runner_busy_false_resets_progress():
    s = make_state()
    s.set_chain_progress(8, 8)
    s.set_runner_busy(False)
    assert s.get_chain_progress() == (0, 0)
