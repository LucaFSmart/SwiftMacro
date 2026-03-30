from unittest.mock import patch, MagicMock
from swiftmacro.state import make_state
from swiftmacro.hotkeys import HotkeyManager
from swiftmacro.models import Profile


def test_failed_hotkey_registration_stored_in_state():
    state = make_state()
    root_mock = MagicMock()

    with patch("keyboard.add_hotkey", side_effect=Exception("Cannot register")):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    errors = state.get_hotkey_errors()
    assert len(errors) == 3
    assert any("ctrl+alt+r" in e for e in errors)


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

    assert len(state.get_hotkey_errors()) == 1


def test_unregister_all_ignores_errors():
    state = make_state()
    root_mock = MagicMock()

    with patch("keyboard.add_hotkey"):
        hm = HotkeyManager(state, root_mock)
        hm.register_all()

    with patch("keyboard.remove_hotkey", side_effect=Exception("fail")), patch(
        "keyboard.unhook_all_hotkeys"
    ), patch("keyboard.unhook_all"):
        hm.unregister_all()


def test_unregister_all_clears_errors_from_state():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)
    state.set_hotkey_errors(["old error"])

    with patch("keyboard.remove_hotkey"), patch("keyboard.unhook_all_hotkeys"), patch(
        "keyboard.unhook_all"
    ):
        hm.unregister_all()

    assert state.get_hotkey_errors() == []


def test_on_run_no_profile_selected():
    state = make_state()
    root_mock = MagicMock()
    runner = MagicMock()
    store = MagicMock()
    hm = HotkeyManager(state, root_mock, runner, store)
    hm._on_run()
    assert "No profile selected" in state.get_status_message()


def test_on_run_with_profile():
    state = make_state()
    state.set_active_profile_id("test-id")
    root_mock = MagicMock()
    runner = MagicMock()
    profile = Profile(id="test-id", name="Test", hotkey=None, steps=[])
    store = MagicMock()
    store.get_by_id.return_value = profile
    hm = HotkeyManager(state, root_mock, runner, store)
    hm._on_run()
    runner.run_profile.assert_called_once_with(profile)


def test_on_stop_chain():
    state = make_state()
    root_mock = MagicMock()
    runner = MagicMock()
    hm = HotkeyManager(state, root_mock, runner)
    hm._on_stop_chain()
    runner.stop.assert_called_once()


def test_refresh_profile_hotkeys_conflict_detection():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+r", steps=[]),
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(profiles)

    errors = state.get_hotkey_errors()
    assert any("conflicts" in e for e in errors)


def test_refresh_profile_hotkeys_duplicate_detection():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+1", steps=[]),
        Profile(id="2", name="P2", hotkey="ctrl+alt+1", steps=[]),  # duplicate
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(profiles)

    errors = state.get_hotkey_errors()
    assert any("conflicts" in e for e in errors)


def test_refresh_profile_hotkeys_clears_stale_profile_errors():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    bad_profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+r", steps=[]),
    ]
    good_profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+1", steps=[]),
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(bad_profiles)
        assert any("conflicts" in e for e in state.get_hotkey_errors())
        hm.refresh_profile_hotkeys(good_profiles)

    assert state.get_hotkey_errors() == []


def test_refresh_profile_hotkeys_preserves_system_errors():
    state = make_state()
    root_mock = MagicMock()
    hm = HotkeyManager(state, root_mock)

    def fail_second_system_hotkey(combo, callback, **kwargs):
        if combo == "ctrl+alt+x":
            raise Exception("blocked")

    with patch("keyboard.add_hotkey", side_effect=fail_second_system_hotkey):
        hm.register_all()

    profiles = [
        Profile(id="1", name="P1", hotkey="ctrl+alt+1", steps=[]),
    ]
    with patch("keyboard.add_hotkey"), patch("keyboard.remove_hotkey"):
        hm.refresh_profile_hotkeys(profiles)

    errors = state.get_hotkey_errors()
    assert len(errors) == 1
    assert "ctrl+alt+x" in errors[0]
