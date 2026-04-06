"""Form metadata used by the step editor — purely data, no widgets.

These tables drive the dynamic ``_build_param_fields()`` method on
:class:`StepBuilderDialog`. Keeping them in a separate module makes adding
new action types a one-file change and keeps the dialog focused on UI glue.
"""
from __future__ import annotations

from swiftmacro.models import ActionStep

# 4-tuple form: (name, label, default, widget_type). widget_type omitted → entry.
_PARAM_FIELDS: dict[str, list[tuple[str, ...]]] = {
    "move": [("x", "X", "0"), ("y", "Y", "0")],
    "click": [("button", "Button", "left", "combo"), ("x", "X", "0"), ("y", "Y", "0")],
    "repeat_click": [
        ("button", "Button", "left", "combo"),
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("count", "Count", "5"),
        ("interval_ms", "Interval (ms)", "100"),
    ],
    "keypress": [("key", "Key", "enter", "key_combo")],
    "wait": [("ms", "Duration (ms)", "100")],
    "lock": [
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("duration_ms", "Duration (ms, 0 = forever)", "0"),
    ],
    "scroll": [
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("direction", "Direction", "down", "combo"),
        ("amount", "Amount (notches)", "3"),
    ],
    "hold_key": [
        ("key", "Key", "w", "key_combo"),
        ("duration_ms", "Duration (ms, 0 = until stopped)", "500"),
    ],
    "random_delay": [
        ("min_ms", "Min delay (ms)", "50"),
        ("max_ms", "Max delay (ms)", "200"),
    ],
    "text_input": [
        ("text", "Text to type", ""),
    ],
    "mouse_drag": [
        ("button",      "Button",        "left", "combo"),
        ("x1",          "From X",        "0"),
        ("y1",          "From Y",        "0"),
        ("x2",          "To X",          "100"),
        ("y2",          "To Y",          "100"),
        ("duration_ms", "Duration (ms)", "300"),
    ],
}

_NEEDS_POSITION = {"move", "click", "repeat_click", "lock", "scroll"}
_INT_PARAMS = {
    "x", "y", "x1", "y1", "x2", "y2",
    "count", "interval_ms", "ms",
    "duration_ms", "amount", "min_ms", "max_ms",
}

_COMBO_VALUES: dict[str, list[str]] = {
    "button":    ["left", "right", "middle"],
    "direction": ["up", "down", "left", "right"],
}

COMMON_KEYS: list[str] = [
    "enter", "space", "tab", "backspace", "delete", "escape",
    "shift", "ctrl", "alt", "win",
    "up", "down", "left", "right",
    "home", "end", "page up", "page down",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
]

_ACTION_HINTS = {
    "move": "Move the cursor to an exact screen coordinate without clicking.",
    "click": "Trigger a single mouse click at a fixed position.",
    "repeat_click": "Spam the same mouse click multiple times with a configurable delay.",
    "keypress": "Send one keyboard key or named key like enter, tab or space.",
    "wait": "Pause the chain for a short or long delay in milliseconds.",
    "lock": "Temporarily or permanently keep the cursor pinned to one coordinate.",
    "scroll": "Scroll the mouse wheel at a position. Direction: up, down, left, right.",
    "hold_key": "Hold a key down for a duration in milliseconds. 0 = hold until chain stops.",
    "random_delay": (
        "Pause for a random duration between min and max milliseconds — "
        "adds human-like timing."
    ),
    "text_input": (
        "Type a string of characters at the current focus. Supports unicode "
        "via clipboard fallback."
    ),
    "mouse_drag": (
        "Press at the start point, smoothly move to the end point, then "
        "release. Duration controls the move speed."
    ),
}


def format_step_label(step: ActionStep) -> str:
    """Backwards-compat alias — delegates to ``ActionStep.format_label()``."""
    return step.format_label()
