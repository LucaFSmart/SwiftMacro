# SwiftMacro — Phase 3: UI/UX Overhaul Design Spec

**Date:** 2026-03-31
**Status:** Approved
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
"chip_idle_fg":    "#b7dbff",
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
        padx=12,
        pady=5,
    )
    return label
```

### 2.4 Update `main_window.py`

Update the import line in `main_window.py` to include `make_chip`:

```python
from swiftmacro.ui.theme import COLORS, HEADING_FONT, MONO_FONT, configure_theme, make_chip, style_listbox
```

Replace all hardcoded hex literals in `_build_profiles_panel()` and `_poll()` with `COLORS[token]` references:

- `#17324c` → `COLORS["chip_idle_bg"]` (idle chip bg — appears in both construction and `_poll()`)
- `#b7dbff` → `COLORS["chip_idle_fg"]` (idle chip fg — appears in both construction and `_poll()`)
- `#1c5d53` → `COLORS["chip_running_bg"]`
- `#173228` → `COLORS["chip_online_bg"]`
- `#35221a` → `COLORS["chip_offline_bg"]`
- `#31121a` → `COLORS["error_bg"]`
- `#6d2436` → `COLORS["error_border"]`
- `#ffb2c1` → `COLORS["error_text"]`

Replace the two raw chip `tk.Label` constructions with `make_chip()` calls.

**No behavior changes.** All existing tests continue to pass.

---

## 3. Step Execution Progress Bar

### 3.1 AppState changes (`swiftmacro/state.py`)

`AppState` is a `@dataclass` — add a new field at the class body level (matching the existing pattern) and update `make_state()`:

```python
# New class-level field in AppState (alongside runner_busy etc.):
chain_progress: tuple[int, int] = field(default=(0, 0))  # (current_step, total_steps)

# New accessor methods on AppState:
def set_chain_progress(self, current: int, total: int) -> None:
    with self._lock:
        self.chain_progress = (current, total)

def get_chain_progress(self) -> tuple[int, int]:
    with self._lock:
        return self.chain_progress
```

In `make_state()`, add `chain_progress=(0, 0)` to the `AppState(...)` call.

In `set_runner_busy()`, reset progress on both transitions:

```python
def set_runner_busy(self, busy: bool) -> None:
    with self._lock:
        self.runner_busy = busy
        self.chain_progress = (0, 0)  # reset on both start and stop
```

This prevents a stale 100% bar flash when a second run begins.

### 3.2 ActionRunner changes (`swiftmacro/action_runner.py`)

In `_run_pass()`, call `set_chain_progress` before executing each step:

```python
for i, step in enumerate(profile.steps):
    self._state.set_chain_progress(i, n)
    # ... existing step execution logic
```

`i` is zero-based, so the bar shows 0% at step 1, `int(1/n*100)` at step 2, etc. — this is intentional. The bar represents "steps completed so far", not "step currently executing".

After the loop completes (all steps done, no stop), call:

```python
self._state.set_chain_progress(n, n)  # 100%
```

**Note:** `_execute_chain()` calls `set_runner_busy(False)` in its `finally` block, which immediately resets `chain_progress` to `(0, 0)`. The `(n, n)` state is therefore very brief. Tests should NOT assert `chain_progress == (n, n)` after the runner finishes — instead test that `set_chain_progress` was called with `(n, n)` via a mock/spy, or test the in-progress values during execution.

### 3.3 MainWindow UI changes (`swiftmacro/ui/main_window.py`)

In `_build_profiles_panel()`, insert the progress bar between `_status_label` (row 1) and `list_shell`. The current row layout is:

| Row | Widget | Weight |
|-----|--------|--------|
| 0 | header | 0 |
| 1 | `_status_label` | 0 |
| 2 | `list_shell` | 1 |
| 3 | `profile_btn_frame` | 0 |

After inserting `_progress_bar` at row 2, shift everything down:

| Row | Widget | Weight |
|-----|--------|--------|
| 0 | header | 0 |
| 1 | `_status_label` | 0 |
| 2 | `_progress_bar` | 0 |
| 3 | `list_shell` / `_empty_state_frame` | 1 |
| 4 | `profile_btn_frame` | 0 |

Update `panel.rowconfigure(3, weight=1)` (was `rowconfigure(2, weight=1)`). `_empty_state_frame` also goes at row 3 (same slot as `list_shell`) and toggles visibility via `grid_remove()`/`grid()`.

Also update `profile_btn_frame`'s grid call from row 3 to row 4:

```python
profile_btn_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))  # was row=3
```

```python
self._progress_bar = ttk.Progressbar(
    panel,
    orient="horizontal",
    mode="determinate",
    style="Teal.Horizontal.TProgressbar",
    maximum=100,
    value=0,
)
# Do NOT grid it here — starts hidden; shown by _poll() when running
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
    self._progress_bar.grid(row=2, column=0, sticky="ew")  # show
else:
    self._progress_bar.grid_remove()  # hide when idle
```

The bar is hidden (`grid_remove()`) when idle and appears automatically when a chain starts.

---

## 4. Empty-State Onboarding

### 4.1 MainWindow changes (`swiftmacro/ui/main_window.py`)

In `_build_profiles_panel()`, the listbox area becomes a switchable container. During construction, store the `list_shell` frame as `self._list_shell = list_shell` so it can be shown/hidden from `_poll()`.

- The **listbox + scrollbar** are built as before inside `list_shell` (now also `self._list_shell`). Change its construction-time grid call from `row=2` to **`row=3`** (due to the progress bar insertion):

  ```python
  self._list_shell = list_shell
  list_shell.grid(row=3, column=0, sticky="nsew")  # was row=2
  ```

- An **empty-state frame** (`self._empty_state_frame`) is built at the same grid slot (row 3, column 0) but starts hidden (do not call `.grid()` on it during construction — `_poll()` will show it when needed):

```
_empty_state_frame contents (centered vertically):
  ⚡ (unicode lightning, 28pt, accent color)
  "No profiles yet"  (SectionTitle.TLabel)
  "Build a reusable action chain to get started"  (Muted.TLabel)
  ttk.Button "＋ Add your first profile"  (Primary.TButton, calls _cmd_add)
```

### 4.2 Toggle logic

In `_poll()`, after refreshing the profile list:

```python
profiles = self._profile_store.load()
if profiles:
    self._empty_state_frame.grid_remove()
    self._list_shell.grid()          # show listbox container
else:
    self._list_shell.grid_remove()   # hide listbox container
    self._empty_state_frame.grid()
```

The empty-state button calls the same `_cmd_add()` handler as the regular Add button — no duplication of logic.

---

## 5. Constrained Step-Builder Inputs

### 5.1 `_PARAM_FIELDS` structure change (`swiftmacro/ui/step_builder.py`)

Extend each field tuple from 3 elements to 4. Update the type annotation from `dict[str, list[tuple[str, str, str]]]` to `dict[str, list[tuple[str, ...]]]`:

Change the type annotation at the top of the dict from `dict[str, list[tuple[str, str, str]]]` to `dict[str, list[tuple[str, ...]]]`.

**Do NOT replace the entire dict.** Only add a 4th element to these specific tuples (leave all others untouched):

| Action | Field | Change |
|--------|-------|--------|
| `click` | `button` | `("button", "Button", "left")` → `("button", "Button", "left", "combo")` |
| `repeat_click` | `button` | same change |
| `keypress` | `key` | `("key", "Key", "enter")` → `("key", "Key", "enter", "key_combo")` |
| `hold_key` | `key` | `("key", "Key", "w")` → `("key", "Key", "w", "key_combo")` |
| `scroll` | `direction` | `("direction", "Direction", "down")` → `("direction", "Direction", "down", "combo")` |

All tuples in `move`, `wait`, `lock`, and `random_delay` remain unchanged as 3-tuples.

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

    # Preserve these two existing post-loop lines — do not remove them:
    self._param_frame.columnconfigure(1, weight=1)

    if action in _NEEDS_POSITION:
        self._pick_btn.pack(side="right")
    else:
        self._pick_btn.pack_forget()
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
| `swiftmacro/state.py` | Add `chain_progress` dataclass field + `make_state()` init; add `set_chain_progress()`, `get_chain_progress()`; reset in `set_runner_busy()` on both `True` and `False` |
| `swiftmacro/action_runner.py` | Call `set_chain_progress(i, n)` per step and `(n, n)` on completion |
| `tests/test_state.py` | Tests for `set_chain_progress`, `get_chain_progress`, reset on `set_runner_busy(True)` and `set_runner_busy(False)` |
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
