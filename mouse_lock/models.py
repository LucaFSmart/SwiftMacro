"""Profile and ActionStep data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


VALID_ACTIONS = {"move", "click", "repeat_click", "keypress", "wait", "lock"}

REQUIRED_PARAMS: dict[str, set[str]] = {
    "move": {"x", "y"},
    "click": {"button", "x", "y"},
    "repeat_click": {"button", "x", "y", "count", "interval_ms"},
    "keypress": {"key"},
    "wait": {"ms"},
    "lock": {"x", "y", "duration_ms"},
}


@dataclass
class ActionStep:
    action: str
    params: dict

    def validate(self) -> bool:
        if self.action not in VALID_ACTIONS:
            return False
        required = REQUIRED_PARAMS.get(self.action, set())
        return required.issubset(self.params.keys())

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
