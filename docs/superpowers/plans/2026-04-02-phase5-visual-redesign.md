# Phase 5 – Modern Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish SwiftMacro's visual appearance with a Treeview profile list, icon-labeled buttons, step-type icons, a spacing constant system, and a wider step builder dialog — all within Tkinter.

**Architecture:** Two new constant dicts (`SPACING`, `STEP_ICONS`) live in `constants.py`. One new ttk style (`App.Treeview`) is added to `theme.py`. `main_window.py` replaces the `tk.Listbox` with `ttk.Treeview` (using `iid=profile.id` for ID-based selection), adds icon prefixes to all buttons, and uses `STEP_ICONS` in the step preview. `step_builder.py` widens the dialog and adds icon prefixes to its buttons and step list labels. All existing behavior is preserved — only visual presentation changes.

**Tech Stack:** Python 3.10+, Tkinter/ttk, pytest

**Spec:** `docs/superpowers/specs/2026-04-02-phase5-visual-redesign.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `swiftmacro/constants.py` | Add `SPACING` dict, `STEP_ICONS` dict |
| Modify | `swiftmacro/ui/theme.py` | Add `App.Treeview` + `App.Treeview.Heading` styles |
| Modify | `swiftmacro/ui/main_window.py` | Treeview, icon buttons, step preview icons, hero cleanup |
| Modify | `swiftmacro/ui/step_builder.py` | Wider dialog, icon buttons, icon-prefixed step labels |
| Modify | `tests/test_constants.py` | Assert SPACING + STEP_ICONS |
| Modify | `tests/test_ui.py` | Assert Treeview columns, icon texts, step icons |

---

## Task 1: `SPACING` and `STEP_ICONS` constants

**Files:**
- Modify: `swiftmacro/constants.py`
- Modify: `tests/test_constants.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_constants.py`:

```python
def test_spacing_dict_present():
    from swiftmacro.constants import SPACING
    for key in ("xs", "sm", "md", "lg", "xl", "xxl"):
        assert key in SPACING, f"Missing SPACING key: {key!r}"
        assert isinstance(SPACING[key], int) and SPACING[key] > 0


def test_step_icons_covers_all_valid_actions():
    from swiftmacro.constants import STEP_ICONS
    from swiftmacro.models import VALID_ACTIONS
    for action in VALID_ACTIONS:
        assert action in STEP_ICONS, f"Missing STEP_ICONS entry for action: {action!r}"
        assert STEP_ICONS[action], f"Empty icon for action: {action!r}"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
py -m pytest tests/test_constants.py::test_spacing_dict_present tests/test_constants.py::test_step_icons_covers_all_valid_actions -v
```

Expected: FAIL — `cannot import name 'SPACING'`

- [ ] **Step 3: Add constants to `swiftmacro/constants.py`**

Add after the existing `LOCK_INTERVAL_MS` block (before the Version and update section):

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```
py -m pytest tests/test_constants.py::test_spacing_dict_present tests/test_constants.py::test_step_icons_covers_all_valid_actions -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```
git add swiftmacro/constants.py tests/test_constants.py
git commit -m "feat: add SPACING and STEP_ICONS constants for visual redesign"
```

---

## Task 2: `App.Treeview` style in `theme.py`

**Files:**
- Modify: `swiftmacro/ui/theme.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui.py`:

```python
def test_treeview_style_configured(tk_root):
    """App.Treeview style must be registered after configure_theme()."""
    from swiftmacro.ui.theme import configure_theme
    style = configure_theme(tk_root)
    # If the style is not registered, layout() returns an empty list
    assert style.layout("App.Treeview") != []
```

- [ ] **Step 2: Run test to confirm it fails**

```
py -m pytest tests/test_ui.py::test_treeview_style_configured -v
```

Expected: FAIL — `App.Treeview` layout is empty (not registered)

- [ ] **Step 3: Add Treeview styles to `configure_theme()` in `swiftmacro/ui/theme.py`**

Insert before `return style` (after the `Teal.Horizontal.TProgressbar` block):

```python
    style.configure(
        "App.Treeview",
        background=COLORS["entry_bg"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["entry_bg"],
        borderwidth=0,
        rowheight=36,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "App.Treeview.Heading",
        background=COLORS["surface_soft"],
        foreground=COLORS["muted"],
        relief="flat",
        font=(FONT_FAMILY, 9, "bold"),
        padding=(8, 6),
    )
    style.map(
        "App.Treeview",
        background=[("selected", COLORS["selection"])],
        foreground=[("selected", COLORS["text"])],
    )
```

- [ ] **Step 4: Run test to confirm it passes**

```
py -m pytest tests/test_ui.py::test_treeview_style_configured -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```
git add swiftmacro/ui/theme.py tests/test_ui.py
git commit -m "feat: add App.Treeview dark style to configure_theme"
```

---

## Task 3: Profile Treeview — replace `tk.Listbox` in `main_window.py`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

This is the largest single task. Read `main_window.py` in full before starting.

The old `tk.Listbox` (`self._profile_listbox`) is replaced by `ttk.Treeview` (`self._profile_tree`). The Treeview uses `iid=profile.id` so selection handling no longer needs index-to-profile mapping.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:

```python
def test_profile_tree_has_correct_columns(tk_root):
    """Profile panel must use a Treeview with name/hotkey/steps columns."""
    from tkinter import ttk
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    for child in tk_root.winfo_children():
        child.destroy()
    win = MainWindow(tk_root, make_state(), tray_available=False)
    tk_root.update_idletasks()
    assert hasattr(win, "_profile_tree")
    assert isinstance(win._profile_tree, ttk.Treeview)
    assert "hotkey" in win._profile_tree["columns"]
    assert "steps" in win._profile_tree["columns"]


def test_profile_tree_populated_from_store(tk_root):
    """Treeview rows must match the profiles in the store."""
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    for child in tk_root.winfo_children():
        child.destroy()
    p = _make_profile()
    win = MainWindow(tk_root, make_state(), tray_available=False, profile_store=_Store([p]))
    tk_root.update_idletasks()
    items = win._profile_tree.get_children()
    assert len(items) == 1
    assert items[0] == p.id  # iid == profile.id
```

- [ ] **Step 2: Run tests to confirm they fail**

```
py -m pytest tests/test_ui.py::test_profile_tree_has_correct_columns tests/test_ui.py::test_profile_tree_populated_from_store -v
```

Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute '_profile_tree'`

- [ ] **Step 3: Replace Listbox with Treeview in `_build_profiles_panel()`**

In `swiftmacro/ui/main_window.py`, inside `_build_profiles_panel()`:

**3a — Replace the `tk.Listbox` block** (currently builds `self._profile_listbox` + `profile_scroll`) with:

```python
        self._profile_tree = ttk.Treeview(
            list_shell,
            columns=("name", "hotkey", "steps"),
            show="headings",
            selectmode="browse",
            style="App.Treeview",
        )
        self._profile_tree.heading("name",   text="Profile", anchor="w")
        self._profile_tree.heading("hotkey", text="Hotkey",  anchor="w")
        self._profile_tree.heading("steps",  text="Steps",   anchor="center")
        self._profile_tree.column("name",   stretch=True,  minwidth=150, anchor="w")
        self._profile_tree.column("hotkey", stretch=False, width=130,    anchor="w")
        self._profile_tree.column("steps",  stretch=False, width=60,     anchor="center")
        self._profile_tree.grid(row=0, column=0, sticky="nsew")
        self._profile_tree.bind("<<TreeviewSelect>>", self._on_profile_select)

        profile_scroll = ttk.Scrollbar(
            list_shell, orient="vertical", command=self._profile_tree.yview,
            style="App.Vertical.TScrollbar",
        )
        profile_scroll.grid(row=0, column=1, sticky="ns")
        self._profile_tree.configure(yscrollcommand=profile_scroll.set)
```

- [ ] **Step 4: Update `_refresh_profile_list()`**

Replace the entire method body with:

```python
    def _refresh_profile_list(self) -> None:
        for item in self._profile_tree.get_children():
            self._profile_tree.delete(item)
        profiles = self._load_profiles()
        active_id = self._state.get_active_profile_id()

        for profile in profiles:
            hotkey_str = profile.hotkey or "—"
            self._profile_tree.insert(
                "", "end",
                iid=profile.id,
                values=(profile.name, hotkey_str, str(len(profile.steps))),
            )

        if active_id and self._profile_tree.exists(active_id):
            self._profile_tree.selection_set(active_id)
            self._profile_tree.see(active_id)

        self._profile_count_label.config(text=f"{len(profiles)}/{MAX_PROFILES} profiles")
        self._update_profile_details()
        self._add_btn.config(state="disabled" if len(profiles) >= MAX_PROFILES else "normal")
        self._update_action_buttons()
```

- [ ] **Step 5: Update `_on_profile_select()`**

Replace with:

```python
    def _on_profile_select(self, event) -> None:
        selection = self._profile_tree.selection()
        if not selection:
            return
        # selection[0] is the iid, which equals profile.id
        self._state.set_active_profile_id(selection[0])
        self._update_profile_details()
        self._update_action_buttons()
```

> **Note:** Do NOT call `_refresh_profile_list()` here — that would delete and recreate all rows on every click, causing flicker and losing the selection. Just update the detail panel and buttons directly.

- [ ] **Step 6: Run new tests to confirm they pass**

```
py -m pytest tests/test_ui.py::test_profile_tree_has_correct_columns tests/test_ui.py::test_profile_tree_populated_from_store -v
```

Expected: PASS

- [ ] **Step 7: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass. Run `grep -n "_profile_listbox" tests/test_ui.py` — this will return **zero results** (no existing test directly references `_profile_listbox`), which is expected and correct. All tests pass without modification.

- [ ] **Step 8: Commit**

```
git add swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: replace profile Listbox with Treeview (name/hotkey/steps columns)"
```

---

## Task 4: Icon buttons + hero cleanup in `main_window.py`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:

```python
def test_action_buttons_have_icons(tk_root):
    """Run and Stop buttons must have icon prefixes."""
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    for child in tk_root.winfo_children():
        child.destroy()
    win = MainWindow(tk_root, make_state(), tray_available=False)
    tk_root.update_idletasks()
    assert "▶" in win._run_btn.cget("text")
    assert "■" in win._stop_btn.cget("text")
    assert "＋" in win._add_btn.cget("text")
    assert "✕" in win._delete_btn.cget("text")
```

- [ ] **Step 2: Run test to confirm it fails**

```
py -m pytest tests/test_ui.py::test_action_buttons_have_icons -v
```

Expected: FAIL — button texts don't contain icons yet

- [ ] **Step 3: Update button texts in `_build_profiles_panel()`**

Change the `text=` argument on each profile action button:

```python
self._add_btn       → text="＋  Add"
self._edit_btn      → text="✎  Edit"
self._duplicate_btn → text="⊞  Copy"
self._delete_btn    → text="✕  Delete"
self._run_btn       → text="▶  Run"
self._stop_btn      → text="■  Stop"
```

- [ ] **Step 4: Update sidebar button texts in `_build_sidebar()`**

```python
self._import_btn → text="↓  Import"
self._export_btn → text="↑  Export"
```

- [ ] **Step 5: Remove the redundant helper paragraph from `_build_hero()`**

The following `tk.Label` is visual noise — it repeats what is already obvious from the layout:

```python
        tk.Label(
            left,
            text="Create a profile, preview its steps on the right, then run it directly or via hotkey.",
            ...
        ).pack(anchor="w", pady=(18, 0))
```

Delete this label entirely. The hero title + body text above it already conveys the same message.

- [ ] **Step 6: Run tests to confirm they pass**

```
py -m pytest tests/test_ui.py::test_action_buttons_have_icons -v
```

Expected: PASS

- [ ] **Step 7: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 8: Commit**

```
git add swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: add icon prefixes to all action buttons, remove redundant hero paragraph"
```

---

## Task 5: Step-type icons in sidebar preview + `_format_profile_step()`

**Files:**
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui.py`:

```python
def test_format_profile_step_includes_icon():
    """_format_profile_step must prefix the line with the STEP_ICONS symbol."""
    from swiftmacro.constants import STEP_ICONS
    from swiftmacro.models import ActionStep

    # We test this via a minimal MainWindow-free call — the method is pure.
    # Instantiate a temporary object to call the method.
    import tkinter as tk
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    root = tk.Tk()
    root.withdraw()
    try:
        win = MainWindow(root, make_state(), tray_available=False)
        step = ActionStep(action="wait", params={"ms": 500})
        result = win._format_profile_step(step)
        assert STEP_ICONS["wait"] in result, f"Expected icon in: {result!r}"
        step2 = ActionStep(action="click", params={"button": "left", "x": 0, "y": 0})
        result2 = win._format_profile_step(step2)
        assert STEP_ICONS["click"] in result2
    finally:
        root.destroy()
```

- [ ] **Step 2: Run test to confirm it fails**

```
py -m pytest tests/test_ui.py::test_format_profile_step_includes_icon -v
```

Expected: FAIL — icons not in output yet

- [ ] **Step 3: Update `_format_profile_step()` in `main_window.py`**

Add the import at the top of the method (or add `STEP_ICONS` to the module-level import from `swiftmacro.constants`):

First, update the import line at the top of `main_window.py`:

```python
from swiftmacro.constants import APP_NAME, MAX_PROFILES, STEP_ICONS, UI_POLL_MS
```

Then prepend `STEP_ICONS.get(step.action, "·")` to each return value in `_format_profile_step()`. The simplest approach: add a prefix variable at the top of the method and use it in every return:

```python
    def _format_profile_step(self, step) -> str:
        icon = STEP_ICONS.get(step.action, "·")
        params = step.params
        if step.action == "move":
            return f"{icon}  Move to {params.get('x')}, {params.get('y')}"
        if step.action == "click":
            return f"{icon}  {params.get('button', 'left').title()} click at {params.get('x')}, {params.get('y')}"
        if step.action == "repeat_click":
            return (
                f"{icon}  {params.get('button', 'left').title()} click "
                f"×{params.get('count')} at {params.get('x')}, {params.get('y')}"
            )
        if step.action == "keypress":
            return f"{icon}  Press '{params.get('key')}'"
        if step.action == "wait":
            return f"{icon}  Wait {params.get('ms')} ms"
        if step.action == "lock":
            duration = params.get("duration_ms", 0)
            suffix = "forever" if duration == 0 else f"{duration} ms"
            return f"{icon}  Lock at {params.get('x')}, {params.get('y')} for {suffix}"
        if step.action == "scroll":
            return f"{icon}  Scroll {params.get('direction')} ×{params.get('amount')} at {params.get('x')}, {params.get('y')}"
        if step.action == "hold_key":
            duration = params.get("duration_ms", 0)
            suffix = "until stopped" if duration == 0 else f"{duration} ms"
            return f"{icon}  Hold '{params.get('key')}' {suffix}"
        if step.action == "random_delay":
            return f"{icon}  Random delay {params.get('min_ms')}–{params.get('max_ms')} ms"
        return f"{icon}  {step.action}"
```

- [ ] **Step 4: Run test to confirm it passes**

```
py -m pytest tests/test_ui.py::test_format_profile_step_includes_icon -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```
git add swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: add step-type icons to sidebar preview via STEP_ICONS"
```

---

## Task 6: Step builder — wider dialog + icon buttons + step label icons

**Files:**
- Modify: `swiftmacro/ui/step_builder.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:

```python
def test_step_builder_dialog_is_wider(tk_root):
    """Step builder dialog must be at least 900px wide."""
    from swiftmacro.ui.step_builder import StepBuilderDialog
    dialog = StepBuilderDialog(tk_root, _Store([]))
    min_w, _ = dialog.top.minsize()
    dialog.top.destroy()
    assert min_w >= 860, f"Step builder minwidth should be >= 860, got {min_w}"


def test_step_builder_format_label_has_icons():
    """format_step_label() in step_builder must use STEP_ICONS."""
    from swiftmacro.constants import STEP_ICONS
    from swiftmacro.models import ActionStep
    from swiftmacro.ui.step_builder import format_step_label
    step = ActionStep(action="keypress", params={"key": "enter"})
    result = format_step_label(step)
    assert STEP_ICONS["keypress"] in result
```

- [ ] **Step 2: Run tests to confirm they fail**

```
py -m pytest tests/test_ui.py::test_step_builder_dialog_is_wider tests/test_ui.py::test_step_builder_format_label_has_icons -v
```

Expected: FAIL — minwidth is 680, icons not in label

- [ ] **Step 3: Widen the dialog in `StepBuilderDialog.__init__()`**

In `swiftmacro/ui/step_builder.py`, change:

```python
        self.top.geometry("720x760")
        self.top.minsize(680, 720)
```

to:

```python
        self.top.geometry("900x760")
        self.top.minsize(860, 720)
```

Change shell padding:

```python
        shell = ttk.Frame(self.top, style="App.TFrame", padding=(22, 20, 22, 20))
```

to:

```python
        shell = ttk.Frame(self.top, style="App.TFrame", padding=(26, 22, 26, 22))
```

- [ ] **Step 4: Rename `_format_step` → `format_step_label` and add icons**

The existing private function in `step_builder.py` is named `_format_step` (line 78). It must be **renamed** to `format_step_label` (making it public so the test can import it) AND updated to include icons.

First, update the import at the top of `step_builder.py`:

```python
from swiftmacro.constants import MAX_STEPS, STEP_ICONS, SYSTEM_HOTKEYS
```

Then **replace** the existing `_format_step` function (lines 78–105) with the renamed, icon-prefixed version:

```python
def format_step_label(step: ActionStep) -> str:
    """One-line human-readable description of a step, with type icon prefix."""
    icon = STEP_ICONS.get(step.action, "·")
    params = step.params
    if step.action == "move":
        return f"{icon}  move → ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "click":
        return f"{icon}  click {params.get('button', '?')} → ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "repeat_click":
        return (
            f"{icon}  repeat {params.get('button', '?')} ×{params.get('count', '?')} "
            f"→ ({params.get('x', '?')}, {params.get('y', '?')})"
        )
    if step.action == "keypress":
        return f"{icon}  keypress '{params.get('key', '?')}'"
    if step.action == "wait":
        return f"{icon}  wait {params.get('ms', '?')} ms"
    if step.action == "lock":
        duration = params.get("duration_ms", 0)
        duration_label = "forever" if duration == 0 else f"{duration} ms"
        return f"{icon}  lock ({params.get('x', '?')}, {params.get('y', '?')}) {duration_label}"
    if step.action == "scroll":
        return f"{icon}  scroll {params.get('direction', '?')} ×{params.get('amount', '?')} @ ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "hold_key":
        duration = params.get("duration_ms", 0)
        duration_label = "until stopped" if duration == 0 else f"{duration} ms"
        return f"{icon}  hold '{params.get('key', '?')}' {duration_label}"
    if step.action == "random_delay":
        return f"{icon}  random delay {params.get('min_ms', '?')}–{params.get('max_ms', '?')} ms"
    return f"{icon}  {step.action}"
```

- [ ] **Step 5: Update the call site and button texts**

**5a — Update `_refresh_steps_list()`** (line 394 in `step_builder.py`). Change `_format_step(step)` to `format_step_label(step)`:

```python
# Before:
self._steps_listbox.insert(tk.END, f"{index}. {_format_step(step)}")
# After:
self._steps_listbox.insert(tk.END, f"{index}. {format_step_label(step)}")
```

**5b — Update `_reset_step_form()`** (line 387 in `step_builder.py`). Change the button text to use the new icon prefix so it stays consistent:

```python
# Before:
self._add_step_btn.config(text="+ Add Step")
# After:
self._add_step_btn.config(text="＋  Add Step")
```

**5c — Update `_build_steps_panel()`** where `_add_step_btn` is initially created (line 300):

```python
# Before:
self._add_step_btn = ttk.Button(editor_panel, text="+ Add Step", ...)
# After:
self._add_step_btn = ttk.Button(editor_panel, text="＋  Add Step", ...)
```

**5d — Update the other step action buttons in `_build_steps_panel()`:**

```python
"Up"     → "↑  Up"
"Down"   → "↓  Down"
"Remove" → "✕  Remove"
```

**5e — Update the Save button in `__init__()` (line 321):**

```python
# Before:
ttk.Button(bottom_frame, text="Save Profile", style="Primary.TButton", command=self._save).grid(
# After:
ttk.Button(bottom_frame, text="✓  Save", style="Primary.TButton", command=self._save).grid(
```

**5f — Update the existing test assertion in `tests/test_ui.py`** (line 125):

```python
# Before:
assert dialog._add_step_btn.cget("text") == "+ Add Step"
# After:
assert dialog._add_step_btn.cget("text") == "＋  Add Step"
```

- [ ] **Step 6: Run tests to confirm they pass**

```
py -m pytest tests/test_ui.py::test_step_builder_dialog_is_wider tests/test_ui.py::test_step_builder_format_label_has_icons -v
```

Expected: PASS

- [ ] **Step 7: Run full suite**

```
py -m pytest tests/ -q
```

Expected: all pass

- [ ] **Step 8: Commit**

```
git add swiftmacro/ui/step_builder.py tests/test_ui.py
git commit -m "feat: widen step builder dialog, add step-type icons to step labels and buttons"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run complete test suite**

```
py -m pytest tests/ -q
```

Expected: 0 failures

- [ ] **Step 2: Bare hex audit**

```
py -c "
import re, sys
files = ['swiftmacro/ui/main_window.py', 'swiftmacro/ui/step_builder.py']
for f in files:
    text = open(f).read()
    hits = re.findall(r'\"#[0-9a-fA-F]{3,8}\"', text)
    if hits:
        print(f'FAIL {f}: bare hex {hits}')
        sys.exit(1)
print('OK: no bare hex strings in UI files')
"
```

Expected: `OK: no bare hex strings in UI files`

- [ ] **Step 3: Manual smoke check**

Launch `py swiftmacro.py` and verify:
- Profile list shows three columns: Profile | Hotkey | Steps
- Buttons all have icon prefixes (＋ Add, ▶ Run, ■ Stop, etc.)
- Sidebar step preview lines start with icons (●, ⌨, ⏸, etc.)
- Opening step builder: dialog is ~900px wide, step list lines have icons
- Empty-state frame still appears when zero profiles exist
- Progress bar still appears during chain execution
- Update chip still appears when a newer version is detected

- [ ] **Step 4: Confirm git log**

```
git log --oneline -8
```

Confirm all Phase 5 commits are present on master.
