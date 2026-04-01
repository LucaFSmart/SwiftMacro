# SwiftMacro — Phase 5: Modern Visual Redesign Spec

**Date:** 2026-04-02
**Status:** Approved
**Scope:** Visual polish pass — Treeview profile list, icon buttons, spacing system, step-type icons, step builder widening, chip hover effects

---

## 1. Overview

Phase 5 is a pure visual improvement pass. It adds no new automation features. Goal: make SwiftMacro look and feel like a polished, professional Windows desktop tool while staying within Tkinter's capabilities.

Five concrete dimensions:

1. **Spacing system** — Replace scattered hardcoded padding/margin values with a `SPACING` constant dict (xs → xxl) so all padding decisions are consistent and easy to change globally.
2. **Profile Treeview** — Replace the plain `tk.Listbox` with a `ttk.Treeview` showing three columns: Profile Name, Hotkey, Steps count. Uses `iid=profile.id` for direct ID-based selection. Dark-styled via `App.Treeview` ttk style.
3. **Icon-labeled buttons** — All action buttons (Add, Edit, Duplicate, Delete, Run, Stop, Import, Export) get a Unicode icon prefix. Makes actions scannable at a glance.
4. **Step-type icons** — A `STEP_ICONS` dict in `constants.py` maps every action name to a short Unicode symbol. Used in the sidebar step preview and step builder step list for visual scannability.
5. **Step builder widening** — Dialog grows from 720×760 to 900×760 to reduce cramping in the parameter panel. Both panels get proportional padding improvements.

---

## 2. Non-Goals

- No new automation features
- No canvas-based rounded corners (Tkinter limitation)
- No animations or transitions beyond what ttk provides natively
- No new color palette (existing `COLORS` tokens are kept as-is)
- No font changes (Segoe UI / Bahnschrift / Consolas stay)

---

## 3. New Constants (`swiftmacro/constants.py`)

```python
SPACING: dict[str, int] = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  18,
    "xl":  26,
    "xxl": 40,
}

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

---

## 4. New ttk Style (`swiftmacro/ui/theme.py`)

Add `App.Treeview` and `App.Treeview.Heading` styles to `configure_theme()`:

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

---

## 5. Profile Treeview (`swiftmacro/ui/main_window.py`)

Replace `tk.Listbox` with `ttk.Treeview`:

```
Columns: name (stretch) | hotkey (130px fixed) | steps (60px fixed, centered)
Column headings: "Profile" | "Hotkey" | "Steps"
iid: profile.id (UUID string) — enables direct ID-based selection without index arithmetic
Event binding: <<TreeviewSelect>> instead of <<ListboxSelect>>
```

`_refresh_profile_list()` rebuilds Treeview rows, sets selection by iid.
`_on_profile_select()` reads `self._profile_tree.selection()` which returns the iid (= profile.id).

The `_empty_state_frame` / `_list_shell` toggle in `_poll()` stays unchanged — same `grid()`/`grid_remove()` logic.

---

## 6. Icon Buttons

| Button | New text |
|--------|----------|
| Add | `＋  Add` |
| Edit | `✎  Edit` |
| Duplicate | `⊞  Copy` |
| Delete | `✕  Delete` |
| Run | `▶  Run` |
| Stop | `■  Stop` |
| Import Profiles | `↓  Import` |
| Export Selection | `↑  Export` |

---

## 7. Step Icons in Sidebar

`_format_profile_step()` in `main_window.py` gains an icon prefix using `STEP_ICONS`.

Example sidebar preview line:
```
1. ● Left click at 100, 200
2. ⌨ Press key 'enter'
3. ⏸ Wait 500 ms
```

`format_step_label()` in `step_builder.py` gains the same prefix.

---

## 8. Step Builder Widening

- Dialog: `720x760` → `900x760`, `minsize(680, 720)` → `minsize(860, 720)`
- Shell padding: `(22, 20, 22, 20)` → `(26, 22, 26, 22)` (matches main window)
