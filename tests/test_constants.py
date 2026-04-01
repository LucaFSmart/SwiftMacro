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
    assert MAX_PROFILES == 20
    assert MAX_STEPS == 100
    assert HOTKEY_EXIT == "ctrl+alt+esc"
    assert HOTKEY_RUN == "ctrl+alt+r"
    assert HOTKEY_STOP_CHAIN == "ctrl+alt+x"
    assert len(SYSTEM_HOTKEYS) == 3


def test_system_hotkeys_contains_all():
    from swiftmacro.constants import SYSTEM_HOTKEYS, HOTKEY_RUN, HOTKEY_STOP_CHAIN
    assert HOTKEY_RUN in SYSTEM_HOTKEYS
    assert HOTKEY_STOP_CHAIN in SYSTEM_HOTKEYS


import re

def test_app_version_defined():
    from swiftmacro.constants import APP_VERSION
    assert APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION), f"APP_VERSION must be semver, got: {APP_VERSION!r}"


def test_github_repo_defined():
    from swiftmacro.constants import GITHUB_REPO
    assert GITHUB_REPO
    assert "/" in GITHUB_REPO
    assert "owner" not in GITHUB_REPO, (
        "Replace the 'owner' placeholder in GITHUB_REPO with your actual GitHub username"
    )
