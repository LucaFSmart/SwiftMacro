import uuid
from swiftmacro.models import ActionStep, Profile, VALID_ACTIONS, REQUIRED_PARAMS


def test_action_step_creation():
    step = ActionStep(action="move", params={"x": 100, "y": 200})
    assert step.action == "move"
    assert step.params == {"x": 100, "y": 200}


def test_action_step_to_dict():
    step = ActionStep(action="click", params={"button": "left", "x": 50, "y": 60})
    d = step.to_dict()
    assert d == {"action": "click", "params": {"button": "left", "x": 50, "y": 60}}


def test_action_step_from_dict():
    d = {"action": "wait", "params": {"ms": 500}}
    step = ActionStep.from_dict(d)
    assert step.action == "wait"
    assert step.params["ms"] == 500


def test_profile_creation():
    p = Profile(id="abc-123", name="Test", hotkey="ctrl+alt+1", steps=[])
    assert p.id == "abc-123"
    assert p.name == "Test"
    assert p.hotkey == "ctrl+alt+1"
    assert p.steps == []


def test_profile_to_dict_and_back():
    steps = [
        ActionStep(action="move", params={"x": 10, "y": 20}),
        ActionStep(action="wait", params={"ms": 100}),
    ]
    p = Profile(id="test-id", name="My Profile", hotkey=None, steps=steps)
    d = p.to_dict()
    p2 = Profile.from_dict(d)
    assert p2.id == p.id
    assert p2.name == p.name
    assert p2.hotkey is None
    assert len(p2.steps) == 2
    assert p2.steps[0].action == "move"


def test_profile_create_new_generates_uuid():
    p = Profile.create_new(name="Fresh", hotkey=None, steps=[])
    uuid.UUID(p.id)  # raises if not valid UUID


def test_valid_actions_complete():
    assert VALID_ACTIONS == {
        "move", "click", "repeat_click", "keypress", "wait", "lock",
        "scroll", "hold_key", "random_delay", "text_input", "mouse_drag",
    }


def test_text_input_validation():
    assert ActionStep(action="text_input", params={"text": "hello"}).validate() is True
    assert ActionStep(action="text_input", params={"text": ""}).validate() is False
    assert ActionStep(action="text_input", params={}).validate() is False
    assert ActionStep(action="text_input", params={"text": 42}).validate() is False


def test_mouse_drag_validation():
    valid = {"button": "left", "x1": 10, "y1": 20, "x2": 30, "y2": 40, "duration_ms": 200}
    assert ActionStep(action="mouse_drag", params=valid).validate() is True
    bad_button = dict(valid, button="purple")
    assert ActionStep(action="mouse_drag", params=bad_button).validate() is False
    bad_dur = dict(valid, duration_ms=-1)
    assert ActionStep(action="mouse_drag", params=bad_dur).validate() is False
    missing = {k: v for k, v in valid.items() if k != "x2"}
    assert ActionStep(action="mouse_drag", params=missing).validate() is False


def test_profile_run_history_defaults_and_roundtrip():
    p = Profile.create_new(name="N", hotkey=None, steps=[])
    assert p.run_count == 0
    assert p.last_run_at is None
    p.run_count = 5
    p.last_run_at = 1700000000.0
    p2 = Profile.from_dict(p.to_dict())
    assert p2.run_count == 5
    assert p2.last_run_at == 1700000000.0


def test_profile_from_dict_legacy_without_run_history():
    legacy = {"id": "x", "name": "L", "hotkey": None, "steps": []}
    p = Profile.from_dict(legacy)
    assert p.run_count == 0
    assert p.last_run_at is None


def test_profile_from_dict_coerces_bad_run_history():
    bad = {
        "id": "x", "name": "L", "hotkey": None, "steps": [],
        "run_count": -3, "last_run_at": "not-a-number",
    }
    p = Profile.from_dict(bad)
    assert p.run_count == 0
    assert p.last_run_at is None


def test_required_params_defined():
    assert "x" in REQUIRED_PARAMS["move"]
    assert "y" in REQUIRED_PARAMS["move"]
    assert "button" in REQUIRED_PARAMS["click"]
    assert "ms" in REQUIRED_PARAMS["wait"]
    assert "count" in REQUIRED_PARAMS["repeat_click"]
    assert "duration_ms" in REQUIRED_PARAMS["lock"]
    assert "key" in REQUIRED_PARAMS["keypress"]
    assert "direction" in REQUIRED_PARAMS["scroll"]
    assert "amount" in REQUIRED_PARAMS["scroll"]
    assert "key" in REQUIRED_PARAMS["hold_key"]
    assert "duration_ms" in REQUIRED_PARAMS["hold_key"]
    assert "min_ms" in REQUIRED_PARAMS["random_delay"]
    assert "max_ms" in REQUIRED_PARAMS["random_delay"]


def test_action_step_validate_valid():
    step = ActionStep(action="move", params={"x": 100, "y": 200})
    assert step.validate() is True


def test_action_step_validate_missing_param():
    step = ActionStep(action="move", params={"x": 100})
    assert step.validate() is False


def test_action_step_validate_unknown_action():
    step = ActionStep(action="explode", params={})
    assert step.validate() is False


def test_action_step_validate_rejects_negative_wait():
    step = ActionStep(action="wait", params={"ms": -1})
    assert step.validate() is False


def test_action_step_validate_rejects_negative_lock_duration():
    step = ActionStep(action="lock", params={"x": 10, "y": 20, "duration_ms": -5})
    assert step.validate() is False


def test_action_step_validate_rejects_invalid_repeat_click_values():
    step = ActionStep(
        action="repeat_click",
        params={"button": "left", "x": 1, "y": 2, "count": 0, "interval_ms": -1},
    )
    assert step.validate() is False


def test_action_step_validate_rejects_invalid_button():
    step = ActionStep(action="click", params={"button": "bad", "x": 1, "y": 2})
    assert step.validate() is False


def test_scroll_step_valid():
    step = ActionStep(action="scroll", params={"x": 0, "y": 0, "direction": "down", "amount": 3})
    assert step.validate() is True


def test_scroll_step_invalid_direction():
    step = ActionStep(action="scroll", params={"x": 0, "y": 0, "direction": "diagonal", "amount": 3})
    assert step.validate() is False


def test_scroll_step_invalid_amount():
    step = ActionStep(action="scroll", params={"x": 0, "y": 0, "direction": "up", "amount": 0})
    assert step.validate() is False


def test_scroll_step_missing_param():
    step = ActionStep(action="scroll", params={"x": 0, "y": 0, "direction": "up"})
    assert step.validate() is False


def test_hold_key_step_valid():
    step = ActionStep(action="hold_key", params={"key": "w", "duration_ms": 500})
    assert step.validate() is True


def test_hold_key_step_zero_duration_valid():
    step = ActionStep(action="hold_key", params={"key": "space", "duration_ms": 0})
    assert step.validate() is True


def test_hold_key_step_negative_duration_invalid():
    step = ActionStep(action="hold_key", params={"key": "w", "duration_ms": -1})
    assert step.validate() is False


def test_hold_key_step_empty_key_invalid():
    step = ActionStep(action="hold_key", params={"key": "", "duration_ms": 100})
    assert step.validate() is False


def test_random_delay_step_valid():
    step = ActionStep(action="random_delay", params={"min_ms": 100, "max_ms": 300})
    assert step.validate() is True


def test_random_delay_step_equal_bounds_valid():
    step = ActionStep(action="random_delay", params={"min_ms": 200, "max_ms": 200})
    assert step.validate() is True


def test_random_delay_step_min_greater_than_max_invalid():
    step = ActionStep(action="random_delay", params={"min_ms": 300, "max_ms": 100})
    assert step.validate() is False


def test_random_delay_step_negative_min_invalid():
    step = ActionStep(action="random_delay", params={"min_ms": -1, "max_ms": 100})
    assert step.validate() is False


def test_profile_default_repeat():
    p = Profile.create_new(name="P", hotkey=None, steps=[])
    assert p.repeat == 1


def test_profile_repeat_serialization():
    p = Profile.create_new(name="P", hotkey=None, steps=[])
    p.repeat = 5
    d = p.to_dict()
    assert d["repeat"] == 5
    p2 = Profile.from_dict(d)
    assert p2.repeat == 5


def test_profile_from_dict_without_repeat_defaults_to_1():
    d = {"id": "abc", "name": "OldProfile", "hotkey": None, "steps": []}
    p = Profile.from_dict(d)
    assert p.repeat == 1


# --- Defensive deserialisation ---

import pytest


def test_action_step_from_dict_rejects_non_dict():
    with pytest.raises(ValueError):
        ActionStep.from_dict("nope")  # type: ignore[arg-type]


def test_action_step_from_dict_rejects_missing_action():
    with pytest.raises(ValueError, match="action"):
        ActionStep.from_dict({"params": {}})


def test_action_step_from_dict_rejects_non_dict_params():
    with pytest.raises(ValueError, match="params"):
        ActionStep.from_dict({"action": "move", "params": "x=1"})


def test_action_step_from_dict_defaults_missing_params_to_empty():
    step = ActionStep.from_dict({"action": "wait"})
    assert step.params == {}


def test_profile_from_dict_rejects_missing_id_or_name():
    with pytest.raises(ValueError):
        Profile.from_dict({"name": "X", "steps": []})
    with pytest.raises(ValueError):
        Profile.from_dict({"id": "x", "steps": []})


def test_profile_from_dict_rejects_non_list_steps():
    with pytest.raises(ValueError, match="steps"):
        Profile.from_dict({"id": "a", "name": "B", "steps": "wait"})


def test_profile_from_dict_rejects_non_string_hotkey():
    with pytest.raises(ValueError, match="hotkey"):
        Profile.from_dict({"id": "a", "name": "B", "steps": [], "hotkey": 42})


def test_profile_has_blocking_lock_before_end_true():
    steps = [
        ActionStep(action="lock", params={"x": 0, "y": 0, "duration_ms": 0}),
        ActionStep(action="wait", params={"ms": 10}),
    ]
    p = Profile(id="x", name="X", hotkey=None, steps=steps)
    assert p.has_blocking_lock_before_end() is True


def test_profile_has_blocking_lock_before_end_false_when_last():
    steps = [
        ActionStep(action="wait", params={"ms": 10}),
        ActionStep(action="lock", params={"x": 0, "y": 0, "duration_ms": 0}),
    ]
    p = Profile(id="x", name="X", hotkey=None, steps=steps)
    assert p.has_blocking_lock_before_end() is False


def test_profile_has_blocking_lock_before_end_false_when_timed():
    steps = [
        ActionStep(action="lock", params={"x": 0, "y": 0, "duration_ms": 100}),
        ActionStep(action="wait", params={"ms": 10}),
    ]
    p = Profile(id="x", name="X", hotkey=None, steps=steps)
    assert p.has_blocking_lock_before_end() is False
