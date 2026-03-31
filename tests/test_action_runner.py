import logging
import threading
import time
from unittest.mock import patch, MagicMock
from swiftmacro.state import make_state
from swiftmacro.models import ActionStep, Profile
from swiftmacro.action_runner import ActionRunner


def make_profile(steps, name="Test"):
    return Profile(id="test-id", name=name, hotkey=None, steps=steps)


def test_run_empty_profile():
    state = make_state()
    runner = ActionRunner(state)
    profile = make_profile([])
    runner.run_profile(profile)
    time.sleep(0.1)
    assert not runner.is_running()


def test_run_move_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="move", params={"x": 100, "y": 200})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        mock_cursor.set_cursor_pos.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.set_cursor_pos.assert_called_with(100, 200)


def test_run_click_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="click", params={"button": "left", "x": 50, "y": 60})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        mock_cursor.click.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.click.assert_called_with("left", 50, 60)


def test_run_wait_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 50})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.2)
    assert not runner.is_running()


def test_run_keypress_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="keypress", params={"key": "enter"})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_kb.press_and_release.assert_called_with("enter")


def test_stop_interrupts_chain():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 5000})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.05)
    assert runner.is_running()
    runner.stop()
    time.sleep(0.1)
    assert not runner.is_running()


def test_ignore_while_running():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 5000})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.05)
    runner.run_profile(profile)  # should be ignored
    assert "Already running" in state.get_status_message()
    runner.stop()
    time.sleep(0.1)


def test_invalid_params_skipped():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="move", params={"x": 100})]  # missing y
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.set_cursor_pos.assert_not_called()


def test_chain_lock_step_sets_state():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="lock", params={"x": 500, "y": 300, "duration_ms": 100})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.02)
    active, pos = state.get_chain_lock()
    assert active is True
    assert pos == (500, 300)
    time.sleep(0.3)
    active, _ = state.get_chain_lock()
    assert active is False


def test_repeat_click_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="repeat_click", params={
        "button": "left", "x": 100, "y": 200, "count": 3, "interval_ms": 10
    })]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        mock_cursor.repeat_click.return_value = 3
        runner.run_profile(profile)
        time.sleep(0.3)
    mock_cursor.repeat_click.assert_called_once()


def test_status_messages_during_run():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 50})]
    profile = make_profile(steps, name="Farm Spot")
    runner.run_profile(profile)
    time.sleep(0.01)
    msg = state.get_status_message()
    assert "Farm Spot" in msg or "Step" in msg or "Running" in msg
    time.sleep(0.2)


def test_failed_step_status_is_not_overwritten_by_done():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="keypress", params={"key": "enter"})]
    profile = make_profile(steps, name="Broken")
    with patch("swiftmacro.action_runner.keyboard.press_and_release", side_effect=RuntimeError("boom")):
        runner.run_profile(profile)
        time.sleep(0.2)
    assert state.get_status_message() == "Step failed: keypress"


def test_semantically_invalid_step_does_not_finish_as_done():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": -10})]
    profile = make_profile(steps, name="Invalid")
    runner.run_profile(profile)
    time.sleep(0.2)
    assert "invalid params" in state.get_status_message()


def test_execute_step_exception_logs_warning(caplog):
    """When a step raises an exception, a WARNING must be logged."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="keypress", params={"key": "enter"})]
    profile = make_profile(steps)

    with caplog.at_level(logging.WARNING, logger="swiftmacro.action_runner"):
        with patch("swiftmacro.action_runner.keyboard.press_and_release",
                   side_effect=RuntimeError("boom")):
            runner.run_profile(profile)
            time.sleep(0.3)

    assert any(r.levelno >= logging.WARNING for r in caplog.records), \
        f"Expected WARNING log, got: {[(r.levelname, r.message) for r in caplog.records]}"


def test_run_profile_sets_and_clears_runner_busy():
    """runner_busy must be True during execution and False when done.
    Note: get_runner_busy() already exists on AppState (state.py).
    """
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 100})]
    profile = make_profile(steps)

    runner.run_profile(profile)
    time.sleep(0.02)
    assert state.get_runner_busy() is True, "runner_busy should be True during execution"

    time.sleep(0.3)
    assert state.get_runner_busy() is False, "runner_busy should be False after completion"


def test_run_scroll_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="scroll", params={"x": 100, "y": 200, "direction": "down", "amount": 3})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        mock_cursor.scroll.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.scroll.assert_called_once_with(100, 200, "down", 3)


def test_run_hold_key_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="hold_key", params={"key": "w", "duration_ms": 50})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.3)
    mock_kb.press.assert_called_once_with("w")
    mock_kb.release.assert_called_once_with("w")


def test_hold_key_releases_on_stop():
    """key must be released even when the chain is stopped mid-hold."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="hold_key", params={"key": "shift", "duration_ms": 5000})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.05)
        runner.stop()  # blocking — waits up to 2s for thread to finish
        mock_kb.press.assert_called_once_with("shift")
        mock_kb.release.assert_called_once_with("shift")


def test_run_random_delay_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="random_delay", params={"min_ms": 10, "max_ms": 30})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.3)
    assert not runner.is_running()
    assert "Done" in state.get_status_message()


def test_profile_repeat_runs_chain_n_times():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 10})]
    profile = make_profile(steps)
    profile.repeat = 3
    call_count = []
    original = runner._execute_step
    def counting_execute(step):
        call_count.append(1)
        return original(step)
    runner._execute_step = counting_execute
    runner.run_profile(profile)
    time.sleep(0.5)
    assert len(call_count) == 3, f"Expected 3 executions, got {len(call_count)}"


def test_profile_repeat_zero_loops_until_stopped():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 10})]
    profile = make_profile(steps)
    profile.repeat = 0
    runner.run_profile(profile)
    time.sleep(0.05)
    assert runner.is_running()
    runner.stop()
    time.sleep(0.2)
    assert not runner.is_running()


def test_progress_reported_per_step():
    """set_chain_progress is called once per step with the correct index."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [
        ActionStep(action="wait", params={"ms": 1}),
        ActionStep(action="wait", params={"ms": 1}),
        ActionStep(action="wait", params={"ms": 1}),
    ]
    profile = make_profile(steps)

    calls = []
    original = state.set_chain_progress

    def spy(current, total):
        calls.append((current, total))
        original(current, total)

    state.set_chain_progress = spy
    runner.run_profile(profile)
    time.sleep(0.3)

    # Should have been called with (0,3), (1,3), (2,3), (3,3) in order
    assert (0, 3) in calls
    assert (2, 3) in calls
    assert (3, 3) in calls
