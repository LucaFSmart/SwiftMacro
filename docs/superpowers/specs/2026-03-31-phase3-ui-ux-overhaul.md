# SwiftMacro — Phase 3: UI/UX Overhaul Design Spec

**Date:** 2026-03-31
**Status:** Draft
**Scope:** Theme centralization, step execution progress bar, empty-state onboarding, constrained step-builder inputs

---

## 1. Overview

Phase 3 improves the user experience across three dimensions without adding new automation features:

1. **Theme centralization** — move all hardcoded hex colors and raw `tk.Label` widget patterns into `theme.py`, add a styled scrollbar, and introduce a `make_chip()` helper. Establishes a consistent token system before adding new UI elements.
2. **Step execution progress bar** — a thin teal `ttk.Progressbar` appears below the status label while a chain is running, showing how many steps have completed. Powered by a new `set_chain_progress(current, total)` method on `AppState`.
3. **Empty-state onboarding** — when zero profiles exist, the listbox area is replaced by a centered prompt (icon + headline + body + teal CTA button) pointing users toward adding their first profile.
4. **Constrained step-builder inputs** — `button` and `direction` fields become readonly `ttk.Combobox` dropdowns; `key` fields become editable comboboxes with a common-key list, eliminating silent invalid input.

---

## 2. Theme Centralization (`swiftmacro/ui/theme.py`)

### 2.1 New color tokens

Add to the `COLORS` dict:

```python
# Status chips
"chip_idle_bg":    "#17324c",
"chip_running_bg": "#1c5d53",
"chip_online_bg":  "#173228",
"chip_offline_bg": "#35221a",

# Error frame
"error_bg":     "#31121a",
"error_border": "#6d2436",
"error_text":   "#ffb2c1",
```

### 2.2 Styled scrollbar

In `configure_theme()`, add:

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
```

All `ttk.Scrollbar` instances in `main_window.py` and `step_builder.py` get `style="App.Vertical.TScrollbar"`.

### 2.3 `make_chip()` helper

Add to `theme.py`:

```python
def make_chip(parent, text: str, bg: str, fg: str) -> tk.Label:
    """Create a styled status chip (raw tk.Label with fixed colors)."""
    label = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
    )
    return label
```

### 2.4 Update `main_window.py`

Replace all hardcoded hex literals in `_build_layout()` and `_poll()` with `COLORS[token]` references. Replace the two raw chip `tk.Label` constructions with `make_chip()` calls. Replace the error frame hardcoded hex values with `COLORS["error_bg"]`, `COLORS["error_border"]`, `COLORS["error_text"]`.

**No behavior changes.** All existing tests continue to pass.

---

## 3. Step Execution Progress Bar

### 3.1 AppState changes (`swiftmacro/state.py`)

Add two new fields and accessor methods:

```python
# In AppState.__init__:
self._chain_progress: tuple[int, int] = (0, 0)  # (current_step, total_steps)

def set_chain_progress(self, current: int, total: int) -> None:
    with self._lock:
        self._chain_progress = (current, total)

def get_chain_progress(self) -> tuple[int, int]:
    with self._lock:
        return self._chain_progress
```

Reset to `(0, 0)` inside `set_runner_busy(False)` so progress clears automatically when the chain finishes or is stopped.

### 3.2 ActionRunner changes (`swiftmacro/action_runner.py`)

In `_run_pass()`, call `set_chain_progress` before executing each step:

```python
for i, step in enumerate(profile.steps):
    self._state.set_chain_progress(i, n)
    # ... existing step execution logic
```

After the loop completes (all steps done, no stop), call:

```python
self._state.set_chain_progress(n, n)  # 100%
```

### 3.3 MainWindow UI changes (`swiftmacro/ui/main_window.py`)

In `_build_layout()`, after `_status_label`, add:

```python
self._progress_bar = ttk.Progressbar(
    profiles_panel,
    orient="horizontal",
    mode="determinate",
    style="Teal.Horizontal.TProgressbar",
    maximum=100,
    value=0,
)
# Initially hidden — only shown during a running chain
```

Add a ttk style to `configure_theme()`:

```python
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

In `_poll()`, update progress bar visibility and value:

```python
current, total = self._state.get_chain_progress()
if self._state.get_runner_busy() and total > 0:
    pct = int(current / total * 100)
    self._progress_bar.config(value=pct)
    self._progress_bar.grid(...)  # show
else:
    self._progress_bar.grid_remove()  # hide when idle
```

The bar is hidden (`grid_remove()`) when idle and appears automatically when a chain starts.

---

## 4. Empty-State Onboarding

### 4.1 MainWindow changes (`swiftmacro/ui/main_window.py`)

In `_build_layout()`, the profiles listbox area becomes a switchable container:

- A `tk.Frame` container (`_list_container`) holds either the listbox or the empty-state widget, both sized to fill the same grid cell.
- The **listbox + scrollbar** are built as before, placed inside `_list_container`.
- An **empty-state frame** (`_empty_state_frame`) is also built inside `_list_container` but starts hidden:

```
_empty_state_frame contents (centered vertically):
  ⚡ (unicode lightning, 28pt, accent color)
  "No profiles yet"  (SectionTitle.TLabel)
  "Build a reusable action chain to get started"  (Muted.TLabel)
  ttk.Button "＋ Add your first profile"  (Primary.TButton, calls _on_add)
```

### 4.2 Toggle logic

In `_poll()`, after refreshing the profile list:

```python
profiles = self._profile_store.load()
if profiles:
    self._empty_state_frame.grid_remove()
    self._profiles_listbox.master.grid()  # show listbox shell
else:
    self._profiles_listbox.master.grid_remove()
    self._empty_state_frame.grid()
```

The empty-state button calls the same `_on_add()` handler as the regular Add button — no duplication of logic.

---

## 5. Constrained Step-Builder Inputs

### 5.1 `_PARAM_FIELDS` structure change (`swiftmacro/ui/step_builder.py`)

Extend each field tuple from 3 elements to 4:

```python
# (name, label, default, widget_type)
# widget_type: "entry" | "combo" | "key_combo"
```

Updated entries:

```python
"click": [
    ("button", "Button", "left", "combo"),   # was "entry"
    ("x", "X", "0", "entry"),
    ("y", "Y", "0", "entry"),
],
"repeat_click": [
    ("button", "Button", "left", "combo"),
    ("x", "X", "0", "entry"),
    ("y", "Y", "0", "entry"),
    ("count", "Count", "5", "entry"),
    ("interval_ms", "Interval (ms)", "100", "entry"),
],
"keypress": [("key", "Key", "enter", "key_combo")],
"hold_key": [
    ("key", "Key", "w", "key_combo"),
    ("duration_ms", "Duration (ms, 0 = until stopped)", "500", "entry"),
],
"scroll": [
    ("x", "X", "0", "entry"),
    ("y", "Y", "0", "entry"),
    ("direction", "Direction", "down", "combo"),  # was "entry"
    ("amount", "Amount (notches)", "3", "entry"),
],
# All other fields keep widget_type "entry"
```

Fields without a 4th element default to `"entry"` (backward-compatible — no change for `move`, `wait`, `lock`, `random_delay`).

### 5.2 Combo values

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

### 5.3 `_build_param_fields()` changes

```python
def _build_param_fields(self, action: str) -> None:
    for child in self._param_frame.winfo_children():
        child.destroy()
    self._param_entries.clear()
    self._param_vars.clear()

    for row, field in enumerate(_PARAM_FIELDS.get(action, [])):
        name, label, default = field[0], field[1], field[2]
        widget_type = field[3] if len(field) > 3 else "entry"

        ttk.Label(...).grid(...)
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
                state="normal",   # allows free text
            )
        else:
            widget = ttk.Entry(self._param_frame, textvariable=var)

        widget.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=(0, 6))
        self._param_entries[name] = widget
        self._param_vars[name] = var
```

### 5.4 `_add_step()` — no changes needed

`var.get()` works identically on `ttk.Combobox` and `ttk.Entry`. Validation logic in `models.py` is unchanged.

---

## 6. Files Changed

| File | Change |
|------|--------|
| `swiftmacro/ui/theme.py` | New color tokens, `make_chip()` helper, scrollbar style, progress bar style |
| `swiftmacro/ui/main_window.py` | Use `COLORS` tokens + `make_chip()`; add progress bar; add empty-state frame |
| `swiftmacro/ui/step_builder.py` | Extend `_PARAM_FIELDS` tuples; add `_COMBO_VALUES` + `COMMON_KEYS`; update `_build_param_fields()` |
| `swiftmacro/state.py` | Add `_chain_progress`, `set_chain_progress()`, `get_chain_progress()`; reset in `set_runner_busy(False)` |
| `swiftmacro/action_runner.py` | Call `set_chain_progress(i, n)` per step and `(n, n)` on completion |
| `tests/test_state.py` | Tests for `set_chain_progress`, `get_chain_progress`, reset-on-busy-false |
| `tests/test_action_runner.py` | Test that progress is reported per step |
| `tests/test_ui.py` | Tests for empty-state visibility toggle; progress bar shown/hidden; combo widgets in step builder |

---

## 7. Out of Scope for Phase 3

- Settings / About panel (Phase 4+)
- Drag-to-reorder steps
- Sidebar step preview scrolling
- Hotkeys card pulling from constants (low risk, deferred)

---

## 8. Success Criteria

- [ ] All hardcoded hex literals in `main_window.py` reference `COLORS[token]`
- [ ] `make_chip()` used for both status chips
- [ ] Scrollbars in both windows use `App.Vertical.TScrollbar` style
- [ ] Progress bar hidden when idle, appears and fills during chain execution, resets on stop/done
- [ ] Empty-state frame shown when 0 profiles; listbox shown when ≥ 1 profile
- [ ] Empty-state "Add" button opens the step builder dialog
- [ ] `button` and `direction` fields in step builder are readonly comboboxes
- [ ] `key` fields are editable comboboxes with common keys listed
- [ ] `py -m pytest tests/ -q` passes with 0 failures
