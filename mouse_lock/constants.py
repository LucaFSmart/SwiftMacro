"""All application constants."""

# System hotkeys
HOTKEY_SAVE = "ctrl+alt+s"
HOTKEY_MOVE = "ctrl+alt+m"
HOTKEY_TOGGLE = "ctrl+alt+t"
HOTKEY_EXIT = "ctrl+alt+esc"

# Profile hotkeys
HOTKEY_RUN = "ctrl+alt+r"
HOTKEY_STOP_CHAIN = "ctrl+alt+x"

# Intervals
LOCK_INTERVAL_MS = 15
UI_POLL_MS = 200
ICON_SIZE = 64

# Limits
MAX_PROFILES = 5
MAX_STEPS = 50

# File paths (expanded at runtime via os.path.expanduser)
PROFILES_DIR = "~/.mouse_lock"
PROFILES_FILE = "~/.mouse_lock/profiles.json"

# All system hotkeys for conflict detection
SYSTEM_HOTKEYS = frozenset({
    HOTKEY_SAVE, HOTKEY_MOVE, HOTKEY_TOGGLE, HOTKEY_EXIT,
    HOTKEY_RUN, HOTKEY_STOP_CHAIN,
})
