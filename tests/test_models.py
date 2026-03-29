import uuid
from mouse_lock.models import ActionStep, Profile, VALID_ACTIONS, REQUIRED_PARAMS


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
    assert VALID_ACTIONS == {"move", "click", "repeat_click", "keypress", "wait", "lock"}


def test_required_params_defined():
    assert "x" in REQUIRED_PARAMS["move"]
    assert "y" in REQUIRED_PARAMS["move"]
    assert "button" in REQUIRED_PARAMS["click"]
    assert "ms" in REQUIRED_PARAMS["wait"]
    assert "count" in REQUIRED_PARAMS["repeat_click"]
    assert "duration_ms" in REQUIRED_PARAMS["lock"]
    assert "key" in REQUIRED_PARAMS["keypress"]


def test_action_step_validate_valid():
    step = ActionStep(action="move", params={"x": 100, "y": 200})
    assert step.validate() is True


def test_action_step_validate_missing_param():
    step = ActionStep(action="move", params={"x": 100})
    assert step.validate() is False


def test_action_step_validate_unknown_action():
    step = ActionStep(action="explode", params={})
    assert step.validate() is False
