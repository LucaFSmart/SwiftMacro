"""Profile and ActionStep data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


VALID_ACTIONS = {
    "move", "click", "repeat_click", "keypress", "wait", "lock", "scroll",
    "hold_key", "random_delay", "text_input", "mouse_drag",
}
VALID_BUTTONS = {"left", "right", "middle"}
VALID_SCROLL_DIRECTIONS = {"up", "down", "left", "right"}

REQUIRED_PARAMS: dict[str, set[str]] = {
    "move": {"x", "y"},
    "click": {"button", "x", "y"},
    "repeat_click": {"button", "x", "y", "count", "interval_ms"},
    "keypress": {"key"},
    "wait": {"ms"},
    "lock": {"x", "y", "duration_ms"},
    "scroll": {"x", "y", "direction", "amount"},
    "hold_key": {"key", "duration_ms"},
    "random_delay": {"min_ms", "max_ms"},
    "text_input": {"text"},
    "mouse_drag": {"button", "x1", "y1", "x2", "y2", "duration_ms"},
}


@dataclass
class ActionStep:
    action: str
    params: dict

    def validate(self) -> bool:
        if self.action not in VALID_ACTIONS:
            return False
        required = REQUIRED_PARAMS.get(self.action, set())
        if not required.issubset(self.params.keys()):
            return False

        if self.action == "move":
            return _has_ints(self.params, "x", "y")

        if self.action == "click":
            return _has_valid_button(self.params) and _has_ints(self.params, "x", "y")

        if self.action == "repeat_click":
            return (
                _has_valid_button(self.params)
                and _has_ints(self.params, "x", "y", "count", "interval_ms")
                and self.params["count"] > 0
                and self.params["interval_ms"] >= 0
            )

        if self.action == "keypress":
            key = self.params.get("key")
            return isinstance(key, str) and key.strip() != ""

        if self.action == "wait":
            return _has_ints(self.params, "ms") and self.params["ms"] >= 0

        if self.action == "lock":
            return (
                _has_ints(self.params, "x", "y", "duration_ms")
                and self.params["duration_ms"] >= 0
            )

        if self.action == "scroll":
            return (
                _has_ints(self.params, "x", "y", "amount")
                and self.params["amount"] > 0
                and self.params.get("direction") in VALID_SCROLL_DIRECTIONS
            )

        if self.action == "hold_key":
            key = self.params.get("key")
            return (
                isinstance(key, str) and key.strip() != ""
                and _has_ints(self.params, "duration_ms")
                and self.params["duration_ms"] >= 0
            )

        if self.action == "random_delay":
            return (
                _has_ints(self.params, "min_ms", "max_ms")
                and self.params["min_ms"] >= 0
                and self.params["max_ms"] >= self.params["min_ms"]
            )

        if self.action == "text_input":
            text = self.params.get("text")
            return isinstance(text, str) and text != ""

        if self.action == "mouse_drag":
            return (
                _has_valid_button(self.params)
                and _has_ints(self.params, "x1", "y1", "x2", "y2", "duration_ms")
                and self.params["duration_ms"] >= 0
            )

        return False

    def to_dict(self) -> dict:
        return {"action": self.action, "params": dict(self.params)}

    def format_label(self) -> str:
        """One-line user-facing description with a STEP_ICONS prefix.

        Single source of truth — both the main window and the step builder
        render steps via this method, so the wording stays consistent.
        """
        # Imported lazily to keep models.py free of UI/constants coupling at
        # import time (constants.py is tiny, but this also keeps a clean layer).
        from swiftmacro.constants import STEP_ICONS

        icon = STEP_ICONS.get(self.action, "·")
        p = self.params
        if self.action == "move":
            return f"{icon}  Move to {p.get('x', '?')}, {p.get('y', '?')}"
        if self.action == "click":
            return (
                f"{icon}  {str(p.get('button', 'left')).title()} click "
                f"at {p.get('x', '?')}, {p.get('y', '?')}"
            )
        if self.action == "repeat_click":
            return (
                f"{icon}  {str(p.get('button', 'left')).title()} click "
                f"×{p.get('count', '?')} at {p.get('x', '?')}, {p.get('y', '?')}"
            )
        if self.action == "keypress":
            return f"{icon}  Press '{p.get('key', '?')}'"
        if self.action == "wait":
            return f"{icon}  Wait {p.get('ms', '?')} ms"
        if self.action == "lock":
            duration = p.get("duration_ms", 0)
            suffix = "forever" if duration == 0 else f"{duration} ms"
            return f"{icon}  Lock at {p.get('x', '?')}, {p.get('y', '?')} for {suffix}"
        if self.action == "scroll":
            return (
                f"{icon}  Scroll {p.get('direction', '?')} ×{p.get('amount', '?')} "
                f"at {p.get('x', '?')}, {p.get('y', '?')}"
            )
        if self.action == "hold_key":
            duration = p.get("duration_ms", 0)
            suffix = "until stopped" if duration == 0 else f"{duration} ms"
            return f"{icon}  Hold '{p.get('key', '?')}' {suffix}"
        if self.action == "random_delay":
            return (
                f"{icon}  Random delay "
                f"{p.get('min_ms', '?')}–{p.get('max_ms', '?')} ms"
            )
        if self.action == "text_input":
            text = str(p.get("text", ""))
            preview = text if len(text) <= 24 else text[:21] + "..."
            return f"{icon}  Type \"{preview}\""
        if self.action == "mouse_drag":
            return (
                f"{icon}  {str(p.get('button', 'left')).title()} drag "
                f"{p.get('x1', '?')},{p.get('y1', '?')} → "
                f"{p.get('x2', '?')},{p.get('y2', '?')}"
            )
        return f"{icon}  {self.action}"

    @classmethod
    def from_dict(cls, d: dict) -> ActionStep:
        if not isinstance(d, dict):
            raise ValueError("ActionStep entry must be an object")
        action = d.get("action")
        if not isinstance(action, str):
            raise ValueError("ActionStep is missing a string 'action'")
        params = d.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"ActionStep '{action}' params must be an object")
        return cls(action=action, params=dict(params))


@dataclass
class Profile:
    id: str
    name: str
    hotkey: str | None
    steps: list[ActionStep]
    repeat: int = 1
    # --- run history (backwards compatible — older JSON omits these) ---
    run_count: int = 0
    last_run_at: float | None = None  # Unix epoch seconds

    @classmethod
    def create_new(cls, name: str, hotkey: str | None, steps: list[ActionStep]) -> Profile:
        return cls(id=str(uuid.uuid4()), name=name, hotkey=hotkey, steps=steps)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "steps": [s.to_dict() for s in self.steps],
            "repeat": self.repeat,
            "run_count": self.run_count,
            "last_run_at": self.last_run_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        if not isinstance(d, dict):
            raise ValueError("Profile entry must be an object")
        pid = d.get("id")
        name = d.get("name")
        if not isinstance(pid, str) or not isinstance(name, str):
            raise ValueError("Profile entry is missing 'id' or 'name'")
        raw_steps = d.get("steps", [])
        if not isinstance(raw_steps, list):
            raise ValueError(f"Profile '{name}' steps must be a list")
        steps = [ActionStep.from_dict(s) for s in raw_steps]
        hotkey = d.get("hotkey")
        if hotkey is not None and not isinstance(hotkey, str):
            raise ValueError(f"Profile '{name}' hotkey must be a string or null")
        repeat = d.get("repeat", 1)
        if not isinstance(repeat, int):
            raise ValueError(f"Profile '{name}' repeat must be an integer")
        # Optional history fields — silently coerced/ignored if malformed so
        # legacy profiles always load.
        run_count = d.get("run_count", 0)
        if not isinstance(run_count, int) or run_count < 0:
            run_count = 0
        last_run_at = d.get("last_run_at")
        if last_run_at is not None and not isinstance(last_run_at, (int, float)):
            last_run_at = None
        return cls(
            id=pid, name=name, hotkey=hotkey, steps=steps, repeat=repeat,
            run_count=run_count, last_run_at=last_run_at,
        )

    def has_blocking_lock_before_end(self) -> bool:
        """A `lock` step with duration_ms == 0 blocks the chain forever; if it
        appears anywhere except the very last step, the steps after it can
        never be reached."""
        for i, step in enumerate(self.steps):
            if (
                step.action == "lock"
                and step.params.get("duration_ms") == 0
                and i != len(self.steps) - 1
            ):
                return True
        return False


def _has_ints(params: dict, *keys: str) -> bool:
    return all(isinstance(params.get(key), int) for key in keys)


def _has_valid_button(params: dict) -> bool:
    return params.get("button") in VALID_BUTTONS
