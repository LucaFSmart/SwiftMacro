# Phase 3 UI/UX Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish SwiftMacro's UI with theme centralization, a step-execution progress bar, empty-state onboarding, and combobox inputs for constrained fields.

**Architecture:** Theme tokens and helper functions live exclusively in `theme.py`; `AppState` grows a `chain_progress` dataclass field; `ActionRunner` calls `set_chain_progress` per step; `MainWindow` hides/shows the progress bar and empty-state frame in its existing `_poll()` loop; `StepBuilderDialog` replaces raw `ttk.Entry` with `ttk.Combobox` for `button`, `direction`, and `key` fields.

**Tech Stack:** Python 3.10+, Tkinter/ttk, `@dataclass`, `threading.Lock`, `pytest`

**Spec:** `docs/superpowers/specs/2026-03-31-phase3-ui-ux-overhaul.md`

---

## File Map

| File | What changes |
|------|-------------|
| `swiftmacro/ui/theme.py` | New `COLORS` tokens; `make_chip()` helper; scrollbar style; progress bar style |
| `swiftmacro/ui/main_window.py` | Replace hardcoded hex; use `make_chip()`; add progress bar + empty-state frame; update layout rows |
| `swiftmacro/ui/step_builder.py` | Update `_PARAM_FIELDS` type + 5 tuples; add `_COMBO_VALUES` + `COMMON_KEYS`; rewrite `_build_param_fields()` |
| `swiftmacro/state.py` | Add `chain_progress` field; `set/get_chain_progress()`; reset in `set_runner_busy()` |
| `swiftmacro/action_runner.py` | Call `set_chain_progress(i, n)` per step in `_run_pass()` |
| `tests/test_state.py` | New tests for `chain_progress` |
| `tests/test_action_runner.py` | New test for per-step progress calls |
| `tests/test_ui.py` | New tests for empty-state toggle, progress bar, combo widgets |

---

## Task 1: Theme centralization — new color tokens and helpers in `theme.py`

**Files:**
- Modify: `swiftmacro/ui/theme.py`

No new behavior, so we write a quick smoke test first, then add the tokens.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py` (after existing imports):

```python
def test_theme_color_tokens_present():
    from swiftmacro.ui.theme import COLORS
    required = [
        "chip_idle_bg", "chip_idle_fg", "chip_running_bg",
        "chip_online_bg", "chip_offline_bg",
        "error_bg", "error_border", "error_text",
    ]
    for key in required:
        assert key in COLORS, f"Missing COLORS token: {key!r}"


def test_make_chip_returns_label(tk_root):
    from swiftmacro.ui.theme import COLORS, make_chip
    chip = make_chip(tk_root, "Test", COLORS["chip_idle_bg"], COLORS["chip_idle_fg"])
    assert chip.cget("text") == "Test"
    assert chip.cget("padx") == 12
    assert chip.cget("pady") == 5
    chip.destroy()
```

- [ ] **Step 2: Run to confirm they fail**

```
py -m pytest tests/test_ui.py::test_theme_color_tokens_present tests/test_ui.py::test_make_chip_returns_label -v
```

Expected: FAIL — `chip_idle_bg` not in COLORS, `make_chip` not defined.

- [ ] **Step 3: Add color tokens to `COLORS` dict in `theme.py`**

In `swiftmacro/ui/theme.py`, add to the `COLORS` dict (after the existing `"selection"` entry):

```python
    # Status chips
    "chip_idle_bg":    "#17324c",
    "chip_idle_fg":    "#b7dbff",
    "chip_running_bg": "#1c5d53",
    "chip_online_bg":  "#173228",
    "chip_offline_bg": "#35221a",
    # Error frame
    "error_bg":     "#31121a",
    "error_border": "#6d2436",
    "error_text":   "#ffb2c1",
```

- [ ] **Step 4: Add `make_chip()` helper to `theme.py`**

Add after the `style_listbox` function:

```python
def make_chip(parent, text: str, bg: str, fg: str) -> tk.Label:
    """Create a styled status chip (raw tk.Label with fixed colors)."""
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=5,
    )
```

- [ ] **Step 5: Add scrollbar style to `configure_theme()`**

In `configure_theme()`, insert before `return style`:

```python
    style.configure(
        "App.Vertical.TScrollbar",
        troughcolor=COLORS["bg"],
        background=COLORS["border"],
        arrowcolor=COLORS["muted"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
    )
    style.map(
        "App.Vertical.TScrollbar",
        background=[("active", COLORS["surface_soft"])],
    )
    style.configure(
        "Teal.Horizontal.TProgressbar",
        troughcolor=COLORS["surface_alt"],
        background=COLORS["accent"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent"],
        thickness=5,
    )
```

- [ ] **Step 6: Run tests**

```
py -m pytest tests/test_ui.py::test_theme_color_tokens_present tests/test_ui.py::test_make_chip_returns_label -v
```

Expected: PASS.

- [ ] **Step 7: Run full suite to confirm nothing broke**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add swiftmacro/ui/theme.py tests/test_ui.py
git commit -m "feat: add theme color tokens, make_chip helper, scrollbar + progress bar styles"
```

---

## Task 2: Replace hardcoded hex in `main_window.py` and use `make_chip()`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`

This is a pure refactor — no new features. All existing tests must continue to pass.

- [ ] **Step 1: Update the import line**

In `swiftmacro/ui/main_window.py`, line 10, change:

```python
from swiftmacro.ui.theme import COLORS, HEADING_FONT, MONO_FONT, configure_theme, style_listbox
```

to:

```python
from swiftmacro.ui.theme import COLORS, HEADING_FONT, MONO_FONT, configure_theme, make_chip, style_listbox
```

- [ ] **Step 2: Replace `_runner_chip` construction in `_build_hero()`**

Lines 88–97: replace the raw `tk.Label` with `make_chip()`:

```python
self._runner_chip = make_chip(
    chip_row,
    text="Idle",
    bg=COLORS["chip_idle_bg"],
    fg=COLORS["chip_idle_fg"],
)
self._runner_chip.pack(side="left")
```

- [ ] **Step 3: Replace `_tray_chip` construction in `_build_hero()`**

Lines 98–107: replace with `make_chip()`:

```python
self._tray_chip = make_chip(
    chip_row,
    text="Tray Ready" if self._tray_available else "Tray Offline",
    bg=COLORS["chip_online_bg"] if self._tray_available else COLORS["chip_offline_bg"],
    fg=COLORS["success"] if self._tray_available else COLORS["warning"],
)
self._tray_chip.pack(side="left", padx=(10, 0))
```

- [ ] **Step 4: Replace hardcoded hex in `_poll()` runner chip update**

Lines 652–656 in `_poll()`:

```python
self._runner_chip.config(
    text="Running Chain" if runner_busy else "Idle",
    bg=COLORS["chip_running_bg"] if runner_busy else COLORS["chip_idle_bg"],
    fg=COLORS["success"] if runner_busy else COLORS["chip_idle_fg"],
)
```

- [ ] **Step 5: Replace hardcoded hex in `_build_sidebar()` error frame**

Lines 350–366: replace hardcoded hex with COLORS tokens:

```python
self._error_frame = tk.Frame(
    sidebar,
    bg=COLORS["error_bg"],
    highlightbackground=COLORS["error_border"],
    highlightthickness=1,
)
self._error_label = tk.Label(
    self._error_frame,
    text="",
    bg=COLORS["error_bg"],
    fg=COLORS["error_text"],
    anchor="w",
    justify="left",
    wraplength=280,
    padx=12,
    pady=12,
)
self._error_label.pack(fill="x")
```

- [ ] **Step 6: Apply `App.Vertical.TScrollbar` style to scrollbars**

In `_build_profiles_panel()`, find the `ttk.Scrollbar` construction (line 225) and add `style="App.Vertical.TScrollbar"`:

```python
profile_scroll = ttk.Scrollbar(
    list_shell, orient="vertical", command=self._profile_listbox.yview,
    style="App.Vertical.TScrollbar",
)
```

Also apply the same style to the scrollbar in `swiftmacro/ui/step_builder.py` — find any `ttk.Scrollbar` instantiation and add `style="App.Vertical.TScrollbar"`.

- [ ] **Step 7: Run full test suite**

```
py -m pytest tests/ -q
```

Expected: all pass. No behavior changed — only color tokens and chip helpers.

- [ ] **Step 8: Commit**

```bash
git add swiftmacro/ui/main_window.py swiftmacro/ui/step_builder.py
git commit -m "refactor: replace hardcoded hex literals with COLORS tokens and make_chip() in main_window"
```

---

## Task 3: AppState — `chain_progress` field and accessors

**Files:**
- Modify: `swiftmacro/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_state.py`:

```python
def test_chain_progress_initial():
    s = make_state()
    assert s.get_chain_progress() == (0, 0)


def test_set_chain_progress():
    s = make_state()
    s.set_chain_progress(3, 8)
    assert s.get_chain_progress() == (3, 8)


def test_set_runner_busy_true_resets_progress():
    s = make_state()
    s.set_chain_progress(5, 8)
    s.set_runner_busy(True)
    assert s.get_chain_progress() == (0, 0)


def test_set_runner_busy_false_resets_progress():
    s = make_state()
    s.set_chain_progress(8, 8)
    s.set_runner_busy(False)
    assert s.get_chain_progress() == (0, 0)
```

- [ ] **Step 2: Run to confirm they fail**

```
py -m pytest tests/test_state.py::test_chain_progress_initial tests/test_state.py::test_set_chain_progress tests/test_state.py::test_set_runner_busy_true_resets_progress tests/test_state.py::test_set_runner_busy_false_resets_progress -v
```

Expected: FAIL — `get_chain_progress` not defined.

- [ ] **Step 3: Add `chain_progress` field to `AppState` dataclass**

In `swiftmacro/state.py`, add the field to the `AppState` class body (after `chain_lock_pos`):

```python
chain_progress: tuple[int, int] = field(default=(0, 0))  # (current_step, total_steps)
```

Note: `field` is already imported from `dataclasses` at line 5.

- [ ] **Step 4: Add accessor methods to `AppState`**

After the `set_chain_lock` method, add:

```python
# --- chain progress ---
def set_chain_progress(self, current: int, total: int) -> None:
    with self._lock:
        self.chain_progress = (current, total)

def get_chain_progress(self) -> tuple[int, int]:
    with self._lock:
        return self.chain_progress
```

- [ ] **Step 5: Update `set_runner_busy()` to reset progress**

Replace the existing `set_runner_busy` method:

```python
def set_runner_busy(self, busy: bool) -> None:
    with self._lock:
        self.runner_busy = busy
        self.chain_progress = (0, 0)  # reset on both start and stop
```

- [ ] **Step 6: Update `make_state()` factory**

In `make_state()`, add `chain_progress=(0, 0)` as a new keyword argument to the existing `AppState(...)` call — do NOT replace the entire call body, just insert the one argument before `_lock=threading.Lock()`:

```python
    chain_progress=(0, 0),   # insert this line before _lock=
    _lock=threading.Lock(),
```

- [ ] **Step 7: Run the new tests**

```
py -m pytest tests/test_state.py -v
```

Expected: all pass.

- [ ] **Step 8: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add swiftmacro/state.py tests/test_state.py
git commit -m "feat: add chain_progress to AppState with set/get accessors and reset on runner busy toggle"
```

---

## Task 4: ActionRunner — report progress per step

**Files:**
- Modify: `swiftmacro/action_runner.py`
- Modify: `tests/test_action_runner.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_action_runner.py`:

```python
def test_progress_reported_per_step():
    """set_chain_progress is called once per step with the correct index."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [
        ActionStep(action="wait", params={"ms": 1}),
        ActionStep(action="wait", params={"ms": 1}),
        ActionStep(action="wait", params={"ms": 1}),
    ]
    profile = make_profile(steps)

    calls = []
    original = state.set_chain_progress

    def spy(current, total):
        calls.append((current, total))
        original(current, total)

    state.set_chain_progress = spy
    runner.run_profile(profile)
    time.sleep(0.3)

    # Should have been called with (0,3), (1,3), (2,3), (3,3) in order
    assert (0, 3) in calls
    assert (2, 3) in calls
    assert (3, 3) in calls
```

- [ ] **Step 2: Run to confirm it fails**

```
py -m pytest tests/test_action_runner.py::test_progress_reported_per_step -v
```

Expected: FAIL — `set_chain_progress` never called.

- [ ] **Step 3: Update `_run_pass()` in `action_runner.py`**

In `swiftmacro/action_runner.py`, find `_run_pass()`. After `n = len(profile.steps)`, update the loop to call `set_chain_progress` before each step and once after the loop:

```python
def _run_pass(self, profile: Profile) -> bool:
    """Run all steps once. Returns True if any step had an error."""
    had_error = False
    n = len(profile.steps)
    for i, step in enumerate(profile.steps):
        if self._stop_event.is_set():
            return had_error
        self._state.set_chain_progress(i, n)
        if not step.validate():
            self._state.set_status_message(f"Step {i+1}/{n}: invalid params")
            had_error = True
            continue
        self._state.set_status_message(f"Step {i+1}/{n}: {step.action}")
        if not self._execute_step(step):
            had_error = True
    if not self._stop_event.is_set() and not had_error:
        self._state.set_chain_progress(n, n)  # 100% — brief, reset by set_runner_busy(False)
    return had_error
```

- [ ] **Step 4: Run the test**

```
py -m pytest tests/test_action_runner.py::test_progress_reported_per_step -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add swiftmacro/action_runner.py tests/test_action_runner.py
git commit -m "feat: report chain_progress per step in ActionRunner._run_pass"
```

---

## Task 5: Progress bar UI in `main_window.py`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ui.py`:

```python
def test_progress_bar_hidden_when_idle(tk_root):
    """Progress bar should not be in the grid when runner is idle."""
    state = make_state()
    store = _Store([_make_profile()])
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=store)
    tk_root.update_idletasks()
    # grid_info() returns {} if widget is not currently gridded
    assert ui._progress_bar.grid_info() == {}
    for child in tk_root.winfo_children():
        child.destroy()


def test_progress_bar_shown_when_busy(tk_root):
    """Progress bar appears when runner is busy and total > 0."""
    state = make_state()
    store = _Store([_make_profile()])
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=store)
    tk_root.update_idletasks()

    state.set_runner_busy(True)
    state.set_chain_progress(2, 8)  # set after busy=True to bypass reset
    tk_root.update_idletasks()
    ui._poll()  # trigger one poll cycle
    tk_root.update_idletasks()

    assert ui._progress_bar.grid_info() != {}
    assert ui._progress_bar.cget("value") == 25  # int(2/8*100)
    for child in tk_root.winfo_children():
        child.destroy()
```

Note: `state.set_runner_busy(True)` resets `chain_progress` to (0,0), so we must call `set_chain_progress` *after* `set_runner_busy`. In the real app, `ActionRunner` calls `set_runner_busy(True)` first then `set_chain_progress` per step — same ordering.

- [ ] **Step 2: Run to confirm they fail**

```
py -m pytest tests/test_ui.py::test_progress_bar_hidden_when_idle tests/test_ui.py::test_progress_bar_shown_when_busy -v
```

Expected: FAIL — `ui._progress_bar` not defined.

- [ ] **Step 3: Update `_build_profiles_panel()` layout**

In `swiftmacro/ui/main_window.py`:

1. Change `panel.rowconfigure(2, weight=1)` to `panel.rowconfigure(3, weight=1)` (line 182).

2. After the `_status_label.grid(...)` call (line 208), create the progress bar (but do NOT grid it):

```python
self._progress_bar = ttk.Progressbar(
    panel,
    orient="horizontal",
    mode="determinate",
    style="Teal.Horizontal.TProgressbar",
    maximum=100,
    value=0,
)
# Do NOT grid here — _poll() shows/hides it
```

3. Change `list_shell.grid(row=2, ...)` to `row=3`:

```python
list_shell.grid(row=3, column=0, sticky="nsew")
```

Also add `self._list_shell = list_shell` right before or after this grid call.

4. Change `profile_btn_frame.grid(row=3, ...)` to `row=4`:

```python
profile_btn_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))
```

- [ ] **Step 4: Update `_poll()` to show/hide the progress bar**

In `_poll()`, add this block after `self._update_action_buttons()` and before `self._root.after(UI_POLL_MS, self._poll)`:

```python
current, total = self._state.get_chain_progress()
if self._state.get_runner_busy() and total > 0:
    pct = int(current / total * 100)
    self._progress_bar.config(value=pct)
    self._progress_bar.grid(row=2, column=0, sticky="ew")
else:
    self._progress_bar.grid_remove()
```

- [ ] **Step 5: Run the tests**

```
py -m pytest tests/test_ui.py::test_progress_bar_hidden_when_idle tests/test_ui.py::test_progress_bar_shown_when_busy -v
```

Expected: PASS.

- [ ] **Step 6: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: add step execution progress bar to profiles panel"
```

---

## Task 6: Empty-state onboarding in `main_window.py`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ui.py`:

```python
def test_empty_state_shown_when_no_profiles(tk_root):
    """Empty-state frame is visible when profile store has 0 profiles."""
    state = make_state()
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=_Store([]))
    tk_root.update_idletasks()
    ui._poll()
    tk_root.update_idletasks()
    assert ui._empty_state_frame.grid_info() != {}
    assert ui._list_shell.grid_info() == {}
    for child in tk_root.winfo_children():
        child.destroy()


def test_listbox_shown_when_profiles_exist(tk_root):
    """List shell is visible and empty-state is hidden when profiles exist."""
    state = make_state()
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=_Store([_make_profile()]))
    tk_root.update_idletasks()
    ui._poll()
    tk_root.update_idletasks()
    assert ui._list_shell.grid_info() != {}
    assert ui._empty_state_frame.grid_info() == {}
    for child in tk_root.winfo_children():
        child.destroy()
```

- [ ] **Step 2: Run to confirm they fail**

```
py -m pytest tests/test_ui.py::test_empty_state_shown_when_no_profiles tests/test_ui.py::test_listbox_shown_when_profiles_exist -v
```

Expected: FAIL — `ui._empty_state_frame` not defined.

- [ ] **Step 3: Build the empty-state frame in `_build_profiles_panel()`**

After the `list_shell.grid(...)` call (and after `self._list_shell = list_shell`), add:

```python
self._empty_state_frame = tk.Frame(panel, bg=COLORS["entry_bg"],
                                    highlightbackground=COLORS["border"],
                                    highlightthickness=1)
# Same grid slot as list_shell (row 3) — starts hidden, _poll() controls visibility
inner = tk.Frame(self._empty_state_frame, bg=COLORS["entry_bg"])
inner.place(relx=0.5, rely=0.5, anchor="center")
tk.Label(inner, text="⚡", bg=COLORS["entry_bg"], fg=COLORS["accent"],
         font=("Segoe UI", 28)).pack()
ttk.Label(inner, text="No profiles yet", style="SectionTitle.TLabel").pack(pady=(6, 0))
ttk.Label(inner, text="Build a reusable action chain to get started",
          style="Muted.TLabel").pack(pady=(4, 12))
ttk.Button(inner, text="＋ Add your first profile",
           style="Primary.TButton", command=self._cmd_add).pack()
```

- [ ] **Step 4: Update `_poll()` to toggle empty state**

In `_poll()`, after `self._update_action_buttons()` and before `self._root.after(UI_POLL_MS, self._poll)` (alongside the progress bar block), add:

```python
# Using _load_profiles() rather than _profile_store.load() directly — safer: handles profile_store=None
profiles = self._load_profiles()
if profiles:
    self._empty_state_frame.grid_remove()
    self._list_shell.grid()
else:
    self._list_shell.grid_remove()
    self._empty_state_frame.grid(row=3, column=0, sticky="nsew")
```

- [ ] **Step 5: Run the tests**

```
py -m pytest tests/test_ui.py::test_empty_state_shown_when_no_profiles tests/test_ui.py::test_listbox_shown_when_profiles_exist -v
```

Expected: PASS.

- [ ] **Step 6: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: add empty-state onboarding frame to profiles panel"
```

---

## Task 7: Constrained step-builder inputs (comboboxes)

**Files:**
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ui.py`:

```python
def test_combo_constants_defined():
    """_COMBO_VALUES and COMMON_KEYS exist with the expected entries."""
    from swiftmacro.ui.step_builder import _COMBO_VALUES, COMMON_KEYS
    assert "button" in _COMBO_VALUES
    assert "left" in _COMBO_VALUES["button"]
    assert "direction" in _COMBO_VALUES
    assert "down" in _COMBO_VALUES["direction"]
    assert "enter" in COMMON_KEYS
    assert "w" in COMMON_KEYS


def test_param_fields_widget_types(tk_root):
    """click/button → Combobox readonly; scroll/direction → Combobox readonly; keypress/key → Combobox normal."""
    from tkinter import ttk
    from swiftmacro.ui.step_builder import StepBuilderDialog
    from swiftmacro.models import Profile

    store = _Store([])
    dialog = StepBuilderDialog(tk_root, store)
    dialog._build_param_fields("click")
    tk_root.update_idletasks()

    button_widget = dialog._param_entries.get("button")
    assert isinstance(button_widget, ttk.Combobox)
    assert str(button_widget.cget("state")) == "readonly"

    dialog._build_param_fields("keypress")
    tk_root.update_idletasks()
    key_widget = dialog._param_entries.get("key")
    assert isinstance(key_widget, ttk.Combobox)
    assert str(key_widget.cget("state")) == "normal"

    dialog._build_param_fields("scroll")
    tk_root.update_idletasks()
    dir_widget = dialog._param_entries.get("direction")
    assert isinstance(dir_widget, ttk.Combobox)
    assert str(dir_widget.cget("state")) == "readonly"

    dialog.top.destroy()
```

- [ ] **Step 2: Run to confirm they fail**

```
py -m pytest tests/test_ui.py::test_combo_constants_defined tests/test_ui.py::test_param_fields_widget_types -v
```

Expected: FAIL — `_COMBO_VALUES` not defined / entries are `ttk.Entry`.

- [ ] **Step 3: Update type annotation and extend the 5 affected tuples in `_PARAM_FIELDS`**

In `swiftmacro/ui/step_builder.py`:

1. Change line 12 annotation from `dict[str, list[tuple[str, str, str]]]` to `dict[str, list[tuple[str, ...]]]`.

2. Add 4th element `"combo"` to `button` tuples in `click` and `repeat_click`:

```python
"click": [("button", "Button", "left", "combo"), ("x", "X", "0"), ("y", "Y", "0")],
"repeat_click": [
    ("button", "Button", "left", "combo"),
    ("x", "X", "0"),
    ("y", "Y", "0"),
    ("count", "Count", "5"),
    ("interval_ms", "Interval (ms)", "100"),
],
```

3. Add `"key_combo"` to `keypress` and `hold_key`:

```python
"keypress": [("key", "Key", "enter", "key_combo")],
"hold_key": [
    ("key", "Key", "w", "key_combo"),
    ("duration_ms", "Duration (ms, 0 = until stopped)", "500"),
],
```

4. Add `"combo"` to `direction` in `scroll`:

```python
"scroll": [
    ("x", "X", "0"),
    ("y", "Y", "0"),
    ("direction", "Direction", "down", "combo"),
    ("amount", "Amount (notches)", "3"),
],
```

All other actions (`move`, `wait`, `lock`, `random_delay`) remain unchanged.

- [ ] **Step 4: Add `_COMBO_VALUES` and `COMMON_KEYS` constants**

After `_INT_PARAMS` (line 46), add:

```python
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
```

- [ ] **Step 5: Rewrite `_build_param_fields()` to use widget type**

Replace the existing `_build_param_fields` method body with:

```python
def _build_param_fields(self, action: str) -> None:
    for child in self._param_frame.winfo_children():
        child.destroy()
    self._param_entries.clear()
    self._param_vars.clear()

    for row, field in enumerate(_PARAM_FIELDS.get(action, [])):
        name, label, default = field[0], field[1], field[2]
        widget_type = field[3] if len(field) > 3 else "entry"

        ttk.Label(self._param_frame, text=label, style="Panel.TLabel").grid(
            row=row, column=0, sticky="w", pady=(0, 6)
        )
        var = tk.StringVar(value=default)

        if widget_type == "combo":
            widget = ttk.Combobox(
                self._param_frame,
                textvariable=var,
                values=_COMBO_VALUES[name],
                state="readonly",
            )
        elif widget_type == "key_combo":
            widget = ttk.Combobox(
                self._param_frame,
                textvariable=var,
                values=COMMON_KEYS,
                state="normal",
            )
        else:
            widget = ttk.Entry(self._param_frame, textvariable=var)

        widget.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=(0, 6))
        self._param_entries[name] = widget
        self._param_vars[name] = var

    # Preserve these post-loop lines:
    self._param_frame.columnconfigure(1, weight=1)

    if action in _NEEDS_POSITION:
        self._pick_btn.pack(side="right")
    else:
        self._pick_btn.pack_forget()
```

- [ ] **Step 6: Run the tests**

```
py -m pytest tests/test_ui.py::test_combo_constants_defined tests/test_ui.py::test_param_fields_widget_types -v
```

Expected: PASS.

- [ ] **Step 7: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add swiftmacro/ui/step_builder.py tests/test_ui.py
git commit -m "feat: constrained step-builder inputs — comboboxes for button, direction, and key fields"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run the complete test suite**

```
py -m pytest tests/ -q
```

Expected: **0 failures**.

- [ ] **Step 2: Manual smoke check against success criteria**

Launch the app (`py swiftmacro.py`) and verify:
- All hardcoded hex literals in `main_window.py` are gone (grep confirms)
- Chips use `make_chip()`, scrollbars show styled appearance
- Create a profile with multiple steps, run it — progress bar appears below status label and fills step-by-step
- Delete all profiles — empty-state frame appears with ⚡ icon and teal CTA button
- Add a profile from the empty-state CTA — listbox switches back
- Open step builder for `click` — Button field is a dropdown with left/right/middle
- Open step builder for `keypress` — Key field is an editable combobox with dropdown suggestions

- [ ] **Step 3: Commit spec as approved**

Update spec status from Draft to Approved:

```bash
# Edit the spec file: change **Status:** Draft → **Status:** Approved
git add docs/superpowers/specs/2026-03-31-phase3-ui-ux-overhaul.md
git commit -m "docs: mark Phase 3 spec as approved"
```
