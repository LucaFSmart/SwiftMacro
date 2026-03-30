"""Profile and ActionStep data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


VALID_ACTIONS = {"move", "click", "repeat_click", "keypress", "wait", "lock", "scroll", "hold_key", "random_delay"}
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

        return False

    def to_dict(self) -> dict:
        return {"action": self.action, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> ActionStep:
        return cls(action=d["action"], params=dict(d["params"]))


@dataclass
class Profile:
    id: str
    name: str
    hotkey: str | None
    steps: list[ActionStep]

    @classmethod
    def create_new(cls, name: str, hotkey: str | None, steps: list[ActionStep]) -> Profile:
        return cls(id=str(uuid.uuid4()), name=name, hotkey=hotkey, steps=steps)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        steps = [ActionStep.from_dict(s) for s in d["steps"]]
        return cls(id=d["id"], name=d["name"], hotkey=d.get("hotkey"), steps=steps)


def _has_ints(params: dict, *keys: str) -> bool:
    return all(isinstance(params.get(key), int) for key in keys)


def _has_valid_button(params: dict) -> bool:
    return params.get("button") in VALID_BUTTONS
