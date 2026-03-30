def test_constants_importable():
    from swiftmacro.constants import (
        HOTKEY_EXIT,
        HOTKEY_RUN, HOTKEY_STOP_CHAIN,
        LOCK_INTERVAL_MS, UI_POLL_MS, ICON_SIZE,
        MAX_PROFILES, MAX_STEPS,
        PROFILES_DIR, PROFILES_FILE,
        SYSTEM_HOTKEYS,
    )
    assert LOCK_INTERVAL_MS == 15
    assert MAX_PROFILES == 5
    assert MAX_STEPS == 50
    assert HOTKEY_EXIT == "ctrl+alt+esc"
    assert HOTKEY_RUN == "ctrl+alt+r"
    assert HOTKEY_STOP_CHAIN == "ctrl+alt+x"
    assert len(SYSTEM_HOTKEYS) == 3


def test_system_hotkeys_contains_all():
    from swiftmacro.constants import SYSTEM_HOTKEYS, HOTKEY_RUN, HOTKEY_STOP_CHAIN
    assert HOTKEY_RUN in SYSTEM_HOTKEYS
    assert HOTKEY_STOP_CHAIN in SYSTEM_HOTKEYS
