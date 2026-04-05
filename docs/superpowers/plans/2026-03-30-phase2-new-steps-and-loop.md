# SwiftMacro Phase 2: New Step Types & Profile Repeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three new action step types (`scroll`, `hold_key`, `random_delay`), a profile-level repeat/loop feature, and raise the profile cap from 5 to 20.

**Architecture:** New step types extend `models.py` (validation), `cursor.py` (scroll Win32 call), `action_runner.py` (execution), and `ui/step_builder.py` (editor UI). Profile repeat adds a `repeat: int` field to `Profile` and wraps the chain loop in `ActionRunner`. All changes follow TDD: write failing test → implement → verify pass → commit.

**Tech Stack:** Python 3.10+, ctypes/Win32, keyboard library, Tkinter, pytest

---

## File Map

| File | Change |
|------|--------|
| `swiftmacro/constants.py` | `MAX_PROFILES`: 5 → 20 |
| `swiftmacro/models.py` | Add `scroll`, `hold_key`, `random_delay` to `VALID_ACTIONS` + `REQUIRED_PARAMS` + `validate()`; add `repeat: int = 1` to `Profile` |
| `swiftmacro/cursor.py` | Add `scroll()` Win32 function |
| `swiftmacro/action_runner.py` | Add handlers for 3 new steps; wrap chain execution in repeat loop |
| `swiftmacro/ui/step_builder.py` | Add param fields, hints, format strings for 3 new steps; update `_INT_PARAMS`; add repeat UI to profile form |
| `tests/test_models.py` | Update `test_valid_actions_complete` + `test_required_params_defined`; add new step validation tests + `Profile.repeat` |
| `tests/test_cursor.py` | Add tests for `scroll()` |
| `tests/test_action_runner.py` | Add tests for new step execution + repeat loop |
| `tests/test_profile_store.py` | Update `test_max_profiles` for new limit of 20 |
| `tests/test_ui.py` | Add tests for repeat field in step builder |

---

## Task 1: Raise Profile Limit to 20

**Files:**
- Modify: `swiftmacro/constants.py`
- Modify: `tests/test_profile_store.py`

- [ ] **Step 1: Update the failing test**

In `tests/test_profile_store.py`, update `test_max_profiles`:

```python
def test_max_profiles(store):
    for i in range(20):
        p = Profile.create_new(name=f"P{i}", hotkey=None, steps=[])
        store.add_profile(p)
    with pytest.raises(ValueError, match="Max"):
        store.add_profile(Profile.create_new(name="P21", hotkey=None, steps=[]))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
py -m pytest tests/test_profile_store.py::test_max_profiles -v
```

Expected: FAIL (ValueError raised too early at profile 6)

- [ ] **Step 3: Update constant**

In `swiftmacro/constants.py`, change:

```python
MAX_PROFILES = 20
```

- [ ] **Step 4: Run test to verify it passes**

```bash
py -m pytest tests/test_profile_store.py::test_max_profiles -v
```

Expected: PASS

- [ ] **Step 5: Run full suite to check no regressions**

```bash
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add swiftmacro/constants.py tests/test_profile_store.py
git commit -m "feat: raise MAX_PROFILES from 5 to 20"
```

---

## Task 2: `scroll` Step Type

**Files:**
- Modify: `swiftmacro/models.py`
- Modify: `swiftmacro/cursor.py`
- Modify: `swiftmacro/action_runner.py`
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_cursor.py`
- Modify: `tests/test_action_runner.py`

### Step type spec

| Field | Type | Constraint |
|---|---|---|
| `x` | int | any |
| `y` | int | any |
| `direction` | str | one of: `"up"`, `"down"`, `"left"`, `"right"` |
| `amount` | int | > 0 |

### 2a. Model

This task also registers `hold_key` and `random_delay` in `VALID_ACTIONS` and `REQUIRED_PARAMS` (all three are added together so `test_valid_actions_complete` only needs one update). Validation logic for those types is added in Tasks 3 and 4.

- [ ] **Step 1: Update test_valid_actions_complete and test_required_params_defined, then write failing scroll tests**

In `tests/test_models.py`, update the two existing registry tests to include all three new action types:

```python
def test_valid_actions_complete():
    assert VALID_ACTIONS == {
        "move", "click", "repeat_click", "keypress", "wait", "lock",
        "scroll", "hold_key", "random_delay",
    }


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
```

Then add the scroll validation tests:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
py -m pytest tests/test_models.py -k "valid_actions_complete or required_params or scroll" -v
```

Expected: FAIL for all (VALID_ACTIONS still has 6 items, scroll not validated yet)

- [ ] **Step 3: Implement in models.py**

Add to `VALID_ACTIONS`:

```python
VALID_ACTIONS = {"move", "click", "repeat_click", "keypress", "wait", "lock", "scroll", "hold_key", "random_delay"}
```

Add constant for scroll directions:

```python
VALID_SCROLL_DIRECTIONS = {"up", "down", "left", "right"}
```

Add to `REQUIRED_PARAMS`:

```python
"scroll": {"x", "y", "direction", "amount"},
"hold_key": {"key", "duration_ms"},
"random_delay": {"min_ms", "max_ms"},
```

Add in `ActionStep.validate()` before the final `return False`:

```python
if self.action == "scroll":
    return (
        _has_ints(self.params, "x", "y", "amount")
        and self.params["amount"] > 0
        and self.params.get("direction") in VALID_SCROLL_DIRECTIONS
    )

# hold_key and random_delay: validation added in Tasks 3 and 4
```

- [ ] **Step 4: Verify model tests pass**

```bash
py -m pytest tests/test_models.py -k "valid_actions_complete or required_params or scroll" -v
```

Expected: PASS for all

### 2b. cursor.py

- [ ] **Step 5: Write failing cursor tests**

Add to `tests/test_cursor.py` (import at file top):

```python
from swiftmacro.cursor import (
    get_cursor_pos, set_cursor_pos, click, repeat_click, scroll
)
```

Note: `scroll` does not exist yet — running tests at this point will raise `ImportError`. That is the expected "red" state.

```python
def test_scroll_vertical_calls_mouse_event():
    with patch("swiftmacro.cursor.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.SetCursorPos.return_value = True
        mock_ctypes.windll.user32.mouse_event.return_value = None
        result = scroll(100, 200, "down", 3)
    assert result is True
    mock_ctypes.windll.user32.mouse_event.assert_called_once()

def test_scroll_horizontal_calls_mouse_event():
    with patch("swiftmacro.cursor.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.SetCursorPos.return_value = True
        mock_ctypes.windll.user32.mouse_event.return_value = None
        result = scroll(0, 0, "left", 2)
    assert result is True
    mock_ctypes.windll.user32.mouse_event.assert_called_once()

def test_scroll_returns_false_on_exception():
    with patch("swiftmacro.cursor.ctypes") as mock_ctypes:
        mock_ctypes.windll.user32.SetCursorPos.side_effect = Exception("fail")
        result = scroll(0, 0, "up", 1)
    assert result is False
```

Check the existing import pattern in `test_cursor.py` — if it imports from `swiftmacro.cursor` at the top already, add `scroll` to that import line.

- [ ] **Step 6: Verify cursor tests fail**

```bash
py -m pytest tests/test_cursor.py -k "scroll" -v
```

Expected: FAIL (ImportError or AttributeError: no `scroll` function)

- [ ] **Step 7: Implement scroll() in cursor.py**

Add constants and function at the bottom of `cursor.py`:

```python
MOUSEEVENTF_WHEEL = 0x0800   # vertical scroll
MOUSEEVENTF_HWHEEL = 0x1000  # horizontal scroll
WHEEL_DELTA = 120             # standard notch size


def scroll(x: int, y: int, direction: str, amount: int) -> bool:
    """Scroll at (x, y). direction: up/down/left/right. amount: notch count."""
    try:
        ctypes.windll.user32.SetCursorPos(x, y)
        if direction in ("up", "down"):
            delta = WHEEL_DELTA * amount * (1 if direction == "up" else -1)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        else:
            delta = WHEEL_DELTA * amount * (1 if direction == "right" else -1)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, delta, 0)
        return True
    except Exception:
        return False
```

- [ ] **Step 8: Verify cursor tests pass**

```bash
py -m pytest tests/test_cursor.py -k "scroll" -v
```

Expected: PASS

### 2c. action_runner.py

- [ ] **Step 9: Write failing runner test**

Add to `tests/test_action_runner.py`:

```python
def test_run_scroll_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="scroll", params={"x": 100, "y": 200, "direction": "down", "amount": 3})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.cursor") as mock_cursor:
        mock_cursor.scroll.return_value = True
        runner.run_profile(profile)
        time.sleep(0.2)
    mock_cursor.scroll.assert_called_once_with(100, 200, "down", 3)
```

- [ ] **Step 10: Verify runner test fails**

```bash
py -m pytest tests/test_action_runner.py::test_run_scroll_step -v
```

Expected: FAIL

- [ ] **Step 11: Add scroll handler in action_runner.py**

In `_execute_step`, add after the `repeat_click` elif:

```python
elif step.action == "scroll":
    cursor.scroll(p["x"], p["y"], p["direction"], p["amount"])
```

- [ ] **Step 12: Verify runner test passes**

```bash
py -m pytest tests/test_action_runner.py::test_run_scroll_step -v
```

Expected: PASS

### 2d. step_builder.py

- [ ] **Step 13: Add scroll to UI constants in step_builder.py**

In `_PARAM_FIELDS`, add:

```python
"scroll": [
    ("x", "X", "0"),
    ("y", "Y", "0"),
    ("direction", "Direction", "down"),
    ("amount", "Amount (notches)", "3"),
],
```

In `_NEEDS_POSITION`, add `"scroll"`:

```python
_NEEDS_POSITION = {"move", "click", "repeat_click", "lock", "scroll"}
```

In `_ACTION_HINTS`, add:

```python
"scroll": "Scroll the mouse wheel at a position. Direction: up, down, left, right.",
```

In `_format_step()`, add:

```python
if step.action == "scroll":
    return f"scroll {params.get('direction', '?')} x{params.get('amount', '?')} @ ({params.get('x', '?')}, {params.get('y', '?')})"
```

In `_INT_PARAMS`, add `"amount"` — `direction` must NOT be added (it is a string):

```python
_INT_PARAMS = {"x", "y", "count", "interval_ms", "ms", "duration_ms", "amount"}
```

- [ ] **Step 14: Run full test suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 15: Commit**

```bash
git add swiftmacro/models.py swiftmacro/cursor.py swiftmacro/action_runner.py swiftmacro/ui/step_builder.py tests/test_models.py tests/test_cursor.py tests/test_action_runner.py
git commit -m "feat: add scroll step type"
```

---

## Task 3: `hold_key` Step Type

**Files:**
- Modify: `swiftmacro/models.py` (validation logic only — VALID_ACTIONS/REQUIRED_PARAMS already updated in Task 2)
- Modify: `swiftmacro/action_runner.py`
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_action_runner.py`

### Step type spec

| Field | Type | Constraint |
|---|---|---|
| `key` | str | non-empty |
| `duration_ms` | int | >= 0 (0 = hold until stopped) |

- [ ] **Step 1: Write failing model tests**

Add to `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
py -m pytest tests/test_models.py -k "hold_key" -v
```

Expected: FAIL (`validate()` returns False for unknown-branched action → `test_hold_key_step_valid` fails)

- [ ] **Step 3: Add hold_key validation in models.py**

In `ActionStep.validate()`, add before the final `return False`:

```python
if self.action == "hold_key":
    key = self.params.get("key")
    return (
        isinstance(key, str) and key.strip() != ""
        and _has_ints(self.params, "duration_ms")
        and self.params["duration_ms"] >= 0
    )
```

- [ ] **Step 4: Verify model tests pass**

```bash
py -m pytest tests/test_models.py -k "hold_key" -v
```

Expected: PASS

- [ ] **Step 5: Write failing runner tests**

Add to `tests/test_action_runner.py`:

```python
def test_run_hold_key_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="hold_key", params={"key": "w", "duration_ms": 50})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.3)
    mock_kb.press.assert_called_once_with("w")
    mock_kb.release.assert_called_once_with("w")


def test_hold_key_releases_on_stop():
    """key must be released even when the chain is stopped mid-hold."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="hold_key", params={"key": "shift", "duration_ms": 5000})]
    profile = make_profile(steps)
    with patch("swiftmacro.action_runner.keyboard") as mock_kb:
        runner.run_profile(profile)
        time.sleep(0.05)
        runner.stop()  # blocking — waits up to 2s for thread to finish
        # After stop() returns the thread has exited; assert inside the patch context
        mock_kb.press.assert_called_once_with("shift")
        mock_kb.release.assert_called_once_with("shift")
```

- [ ] **Step 6: Verify runner tests fail**

```bash
py -m pytest tests/test_action_runner.py -k "hold_key" -v
```

Expected: FAIL

- [ ] **Step 7: Add hold_key handler in action_runner.py**

```python
elif step.action == "hold_key":
    keyboard.press(p["key"])
    try:
        duration_ms = p["duration_ms"]
        if duration_ms == 0:
            self._stop_event.wait()
        else:
            self._stop_event.wait(timeout=duration_ms / 1000.0)
    finally:
        keyboard.release(p["key"])
```

The `finally` block guarantees `keyboard.release` is called even when `stop()` sets the stop event mid-hold.

- [ ] **Step 8: Verify runner tests pass**

```bash
py -m pytest tests/test_action_runner.py -k "hold_key" -v
```

Expected: PASS

- [ ] **Step 9: Add hold_key to step_builder.py**

In `_PARAM_FIELDS`:

```python
"hold_key": [
    ("key", "Key", "w"),
    ("duration_ms", "Duration (ms, 0 = until stopped)", "500"),
],
```

`duration_ms` is already in `_INT_PARAMS` (used by `lock`). No change needed.

In `_ACTION_HINTS`:

```python
"hold_key": "Hold a key down for a duration in milliseconds. 0 = hold until chain stops.",
```

In `_format_step()`:

```python
if step.action == "hold_key":
    duration = params.get("duration_ms", 0)
    duration_label = "until stopped" if duration == 0 else f"{duration}ms"
    return f"hold_key '{params.get('key', '?')}' {duration_label}"
```

- [ ] **Step 10: Run full suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 11: Commit**

```bash
git add swiftmacro/models.py swiftmacro/action_runner.py swiftmacro/ui/step_builder.py tests/test_models.py tests/test_action_runner.py
git commit -m "feat: add hold_key step type"
```

---

## Task 4: `random_delay` Step Type

**Files:**
- Modify: `swiftmacro/models.py`
- Modify: `swiftmacro/action_runner.py`
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_action_runner.py`

### Step type spec

| Field | Type | Constraint |
|---|---|---|
| `min_ms` | int | >= 0 |
| `max_ms` | int | >= `min_ms` |

- [ ] **Step 1: Write failing model tests**

Add to `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
py -m pytest tests/test_models.py -k "random_delay" -v
```

Expected: FAIL

- [ ] **Step 3: Add random_delay validation in models.py**

In `ActionStep.validate()`, add before the final `return False`:

```python
if self.action == "random_delay":
    return (
        _has_ints(self.params, "min_ms", "max_ms")
        and self.params["min_ms"] >= 0
        and self.params["max_ms"] >= self.params["min_ms"]
    )
```

- [ ] **Step 4: Verify model tests pass**

```bash
py -m pytest tests/test_models.py -k "random_delay" -v
```

Expected: PASS

- [ ] **Step 5: Write failing runner test**

Add to `tests/test_action_runner.py`:

```python
def test_run_random_delay_step():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="random_delay", params={"min_ms": 10, "max_ms": 30})]
    profile = make_profile(steps)
    runner.run_profile(profile)
    time.sleep(0.3)
    assert not runner.is_running()
```

- [ ] **Step 6: Verify runner test fails**

```bash
py -m pytest tests/test_action_runner.py::test_run_random_delay_step -v
```

Expected: FAIL

- [ ] **Step 7: Add random_delay handler in action_runner.py**

At the top of `action_runner.py`, add `import random`.

In `_execute_step`:

```python
elif step.action == "random_delay":
    ms = random.randint(p["min_ms"], p["max_ms"])
    self._stop_event.wait(timeout=ms / 1000.0)
```

- [ ] **Step 8: Verify runner test passes**

```bash
py -m pytest tests/test_action_runner.py::test_run_random_delay_step -v
```

Expected: PASS

- [ ] **Step 9: Add random_delay to step_builder.py**

In `_PARAM_FIELDS`:

```python
"random_delay": [
    ("min_ms", "Min delay (ms)", "50"),
    ("max_ms", "Max delay (ms)", "200"),
],
```

In `_ACTION_HINTS`:

```python
"random_delay": "Pause for a random duration between min and max milliseconds — adds human-like timing.",
```

In `_format_step()`:

```python
if step.action == "random_delay":
    return f"random_delay {params.get('min_ms', '?')}–{params.get('max_ms', '?')}ms"
```

In `_INT_PARAMS`, add `"min_ms"` and `"max_ms"`:

```python
_INT_PARAMS = {"x", "y", "count", "interval_ms", "ms", "duration_ms", "amount", "min_ms", "max_ms"}
```

- [ ] **Step 10: Run full suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 11: Commit**

```bash
git add swiftmacro/models.py swiftmacro/action_runner.py swiftmacro/ui/step_builder.py tests/test_models.py tests/test_action_runner.py
git commit -m "feat: add random_delay step type"
```

---

## Task 5: Profile Repeat / Loop

**Files:**
- Modify: `swiftmacro/models.py`
- Modify: `swiftmacro/action_runner.py`
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_action_runner.py`
- Modify: `tests/test_ui.py`

### Spec

`Profile` gains a `repeat: int` field (default `1`).

| Value | Meaning |
|---|---|
| 1 | run once (existing behavior) |
| N > 1 | run the chain N times |
| 0 | loop forever until stopped |

Backward compatibility: `from_dict` uses `d.get("repeat", 1)` so existing saved profiles without the field default to run-once.

### 5a. Model

- [ ] **Step 1: Write failing model tests**

Add to `tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Verify tests fail**

```bash
py -m pytest tests/test_models.py -k "profile_default_repeat or repeat_serialization or without_repeat" -v
```

Expected: FAIL (Profile has no `repeat` attribute)

- [ ] **Step 3: Add repeat to Profile in models.py**

```python
@dataclass
class Profile:
    id: str
    name: str
    hotkey: str | None
    steps: list[ActionStep]
    repeat: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "hotkey": self.hotkey,
            "steps": [s.to_dict() for s in self.steps],
            "repeat": self.repeat,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        steps = [ActionStep.from_dict(s) for s in d["steps"]]
        return cls(
            id=d["id"],
            name=d["name"],
            hotkey=d.get("hotkey"),
            steps=steps,
            repeat=d.get("repeat", 1),
        )
```

- [ ] **Step 4: Verify model tests pass**

```bash
py -m pytest tests/test_models.py -k "profile_default_repeat or repeat_serialization or without_repeat" -v
```

Expected: PASS

### 5b. ActionRunner loop

- [ ] **Step 5: Write failing runner tests**

Add to `tests/test_action_runner.py`:

```python
def test_profile_repeat_runs_chain_n_times():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 10})]
    profile = make_profile(steps)
    profile.repeat = 3
    call_count = []
    original = runner._execute_step
    def counting_execute(step):
        call_count.append(1)
        return original(step)
    runner._execute_step = counting_execute
    runner.run_profile(profile)
    time.sleep(0.5)
    assert len(call_count) == 3, f"Expected 3 executions, got {len(call_count)}"


def test_profile_repeat_zero_loops_until_stopped():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 10})]
    profile = make_profile(steps)
    profile.repeat = 0
    runner.run_profile(profile)
    time.sleep(0.05)
    assert runner.is_running()
    runner.stop()
    time.sleep(0.2)
    assert not runner.is_running()
```

- [ ] **Step 6: Verify tests fail**

```bash
py -m pytest tests/test_action_runner.py -k "repeat" -v
```

Expected: FAIL

- [ ] **Step 7: Refactor _execute_chain to loop**

Replace `_execute_chain` in `action_runner.py` with the following two methods. The key invariant preserved for existing tests: when `profile.repeat == 1` and no error, status is set to `"Done"` — exactly as before. When there is an error, `_run_pass` returns `True` and sets the error status message; the outer loop then breaks without overwriting it with `"Done"`. This preserves `test_failed_step_status_is_not_overwritten_by_done` and `test_semantically_invalid_step_does_not_finish_as_done`.

```python
def _execute_chain(self, profile: Profile) -> None:
    _log.info("Chain started: %s (%d steps, repeat=%s)", profile.name, len(profile.steps), profile.repeat)
    iteration = 0
    try:
        self._state.set_status_message(f"Running: {profile.name}")
        while True:
            if self._stop_event.is_set():
                break
            had_error = self._run_pass(profile)
            iteration += 1
            if had_error:
                break
            if profile.repeat != 0 and iteration >= profile.repeat:
                # Ran the requested number of times, no errors
                if profile.repeat == 1:
                    self._state.set_status_message("Done")
                else:
                    self._state.set_status_message(f"Done ({iteration}x)")
                _log.info("Chain completed: %s (%d iterations)", profile.name, iteration)
                break

        if self._stop_event.is_set():
            _log.info("Chain stopped: %s", profile.name)
    finally:
        self._state.set_chain_lock(False)
        self._state.set_runner_busy(False)
        with self._lock:
            self._running = False


def _run_pass(self, profile: Profile) -> bool:
    """Run all steps once. Returns True if any step had an error."""
    had_error = False
    n = len(profile.steps)
    for i, step in enumerate(profile.steps):
        if self._stop_event.is_set():
            return had_error
        if not step.validate():
            self._state.set_status_message(f"Step {i+1}/{n}: invalid params")
            had_error = True
            continue
        self._state.set_status_message(f"Step {i+1}/{n}: {step.action}")
        if not self._execute_step(step):
            had_error = True
    return had_error
```

Note: `_execute_step` already sets the error status message `"Step failed: <action>"` on exception. When `_run_pass` returns `True`, `_execute_chain` breaks the loop without touching the status message — so the failure message is preserved.

- [ ] **Step 8: Verify runner tests pass — including existing tests**

```bash
py -m pytest tests/test_action_runner.py -v
```

Expected: ALL pass, including `test_failed_step_status_is_not_overwritten_by_done` and `test_semantically_invalid_step_does_not_finish_as_done`. If those two fail, the status-message preservation logic in `_execute_chain` needs adjustment.

### 5c. UI — repeat field in StepBuilderDialog

The existing `test_ui.py` uses fixture `tk_root` (not `root`) and a helper class `_Store`. There is no `profile_store` fixture — tests create `_Store([])` inline. Add the repeat tests following this same pattern.

- [ ] **Step 9: Write failing UI tests**

Add to `tests/test_ui.py`:

```python
def test_step_builder_has_repeat_field(tk_root):
    """StepBuilderDialog must expose _repeat_var."""
    dlg = StepBuilderDialog(tk_root, _Store([]))
    assert hasattr(dlg, "_repeat_var"), "StepBuilderDialog must have _repeat_var"
    dlg.top.destroy()


def test_step_builder_repeat_defaults_to_1(tk_root):
    dlg = StepBuilderDialog(tk_root, _Store([]))
    assert dlg._repeat_var.get() == "1"
    dlg.top.destroy()


def test_step_builder_repeat_loaded_from_existing_profile(tk_root):
    profile = Profile(
        id="p1", name="Test", hotkey=None,
        steps=[ActionStep(action="move", params={"x": 0, "y": 0})],
        repeat=7,
    )
    dlg = StepBuilderDialog(tk_root, _Store([profile]), profile=profile)
    assert dlg._repeat_var.get() == "7"
    dlg.top.destroy()
```

- [ ] **Step 10: Verify UI tests fail**

```bash
py -m pytest tests/test_ui.py -k "repeat" -v
```

Expected: FAIL (no `_repeat_var` attribute)

- [ ] **Step 11: Add repeat UI to StepBuilderDialog**

In the `details` frame section of `StepBuilderDialog.__init__` (the grid containing Name and Hotkey entries), add a third column for Repeat.

The existing grid uses `column=0` for Name and `column=1` for Hotkey. Add `column=2` for Repeat:

```python
ttk.Label(details, text="Repeat (0 = loop forever)", style="SectionTitle.TLabel").grid(
    row=0, column=2, sticky="w", padx=(12, 0)
)
initial_repeat = str(profile.repeat) if profile else "1"
self._repeat_var = tk.StringVar(value=initial_repeat)
ttk.Entry(details, textvariable=self._repeat_var, width=8).grid(
    row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0)
)
```

In `_save()`, parse and validate repeat before building the Profile:

```python
repeat_raw = self._repeat_var.get().strip()
try:
    repeat = int(repeat_raw)
    if repeat < 0:
        raise ValueError
except ValueError:
    messagebox.showwarning("Invalid", "Repeat must be a whole number \u2265 0")
    return
```

Then pass `repeat` when creating/updating the profile:

```python
if self._editing is not None:
    self._editing.name = name
    self._editing.hotkey = hotkey
    self._editing.steps = list(self._steps)
    self._editing.repeat = repeat
    self.result = self._editing
else:
    p = Profile.create_new(name=name, hotkey=hotkey, steps=list(self._steps))
    p.repeat = repeat
    self.result = p
```

- [ ] **Step 12: Verify UI tests pass**

```bash
py -m pytest tests/test_ui.py -k "repeat" -v
```

Expected: PASS

- [ ] **Step 13: Run full suite**

```bash
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 14: Commit**

```bash
git add swiftmacro/models.py swiftmacro/action_runner.py swiftmacro/ui/step_builder.py tests/test_models.py tests/test_action_runner.py tests/test_ui.py
git commit -m "feat: add profile repeat/loop support"
```

---

## Success Criteria

- [ ] `MAX_PROFILES` is 20; `test_max_profiles` creates 20 profiles without error
- [ ] `scroll`, `hold_key`, `random_delay` appear in `VALID_ACTIONS` and in the step builder dropdown
- [ ] All new step types validate correctly (good + bad params tested)
- [ ] All new step types execute correctly (mock-verified in runner tests)
- [ ] `hold_key` releases the key even when the chain is stopped mid-hold
- [ ] `random_delay` rejects `min_ms > max_ms`
- [ ] `Profile.repeat` defaults to 1, serializes to/from JSON, backward-compatible with old saved profiles
- [ ] `ActionRunner` runs the chain `repeat` times; repeat=0 loops until stopped
- [ ] Existing tests `test_failed_step_status_is_not_overwritten_by_done` and `test_semantically_invalid_step_does_not_finish_as_done` continue to pass after the repeat refactor
- [ ] StepBuilderDialog shows a Repeat field; value loads from an existing profile
- [ ] `py -m pytest tests/ -q` passes with 0 failures
