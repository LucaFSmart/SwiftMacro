"""All application constants."""

APP_NAME = "SwiftMacro"
APP_ID = "SwiftMacro.Desktop"
APP_MUTEX_NAME = "Local\\SwiftMacro.Desktop"

# System hotkeys
HOTKEY_EXIT = "ctrl+alt+esc"

# Profile hotkeys
HOTKEY_RUN = "ctrl+alt+r"
HOTKEY_STOP_CHAIN = "ctrl+alt+x"

# Intervals
LOCK_INTERVAL_MS = 15
UI_POLL_MS = 200
ICON_SIZE = 64

# Limits
MAX_PROFILES = 20
MAX_STEPS = 100

# UI spacing system (pixels)
SPACING: dict[str, int] = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  18,
    "xl":  26,
    "xxl": 40,
}

# Step-type icons (Unicode symbols safe for Segoe UI on Windows)
STEP_ICONS: dict[str, str] = {
    "move":         "→",
    "click":        "●",
    "repeat_click": "◎",
    "keypress":     "⌨",
    "wait":         "⏸",
    "lock":         "⊕",
    "scroll":       "↕",
    "hold_key":     "⌨",
    "random_delay": "~",
}

# File paths (expanded at runtime via os.path.expanduser)
PROFILES_DIR = "~/.swiftmacro"
PROFILES_FILE = "~/.swiftmacro/profiles.json"

# Legacy path for migration
PROFILES_DIR_LEGACY = "~/.mouse_lock"
PROFILES_FILE_LEGACY = "~/.mouse_lock/profiles.json"

# All system hotkeys for conflict detection
SYSTEM_HOTKEYS = frozenset({
    HOTKEY_EXIT, HOTKEY_RUN, HOTKEY_STOP_CHAIN,
})

# Version and update
APP_VERSION = "1.0.0"
GITHUB_REPO = "swiftmacro-app/SwiftMacro"
