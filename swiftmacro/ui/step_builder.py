"""Profile editor for building action chains."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from swiftmacro.constants import MAX_STEPS, SYSTEM_HOTKEYS
from swiftmacro.cursor import get_cursor_pos
from swiftmacro.models import ActionStep, Profile, VALID_ACTIONS
from swiftmacro.ui.theme import COLORS, MONO_FONT, configure_theme, style_listbox

_PARAM_FIELDS: dict[str, list[tuple[str, ...]]] = {
    "move": [("x", "X", "0"), ("y", "Y", "0")],
    "click": [("button", "Button", "left", "combo"), ("x", "X", "0"), ("y", "Y", "0")],
    "repeat_click": [
        ("button", "Button", "left", "combo"),
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("count", "Count", "5"),
        ("interval_ms", "Interval (ms)", "100"),
    ],
    "keypress": [("key", "Key", "enter", "key_combo")],
    "wait": [("ms", "Duration (ms)", "100")],
    "lock": [
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("duration_ms", "Duration (ms, 0 = forever)", "0"),
    ],
    "scroll": [
        ("x", "X", "0"),
        ("y", "Y", "0"),
        ("direction", "Direction", "down", "combo"),
        ("amount", "Amount (notches)", "3"),
    ],
    "hold_key": [
        ("key", "Key", "w", "key_combo"),
        ("duration_ms", "Duration (ms, 0 = until stopped)", "500"),
    ],
    "random_delay": [
        ("min_ms", "Min delay (ms)", "50"),
        ("max_ms", "Max delay (ms)", "200"),
    ],
}

_NEEDS_POSITION = {"move", "click", "repeat_click", "lock", "scroll"}
_INT_PARAMS = {"x", "y", "count", "interval_ms", "ms", "duration_ms", "amount", "min_ms", "max_ms"}

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

_ACTION_HINTS = {
    "move": "Move the cursor to an exact screen coordinate without clicking.",
    "click": "Trigger a single mouse click at a fixed position.",
    "repeat_click": "Spam the same mouse click multiple times with a configurable delay.",
    "keypress": "Send one keyboard key or named key like enter, tab or space.",
    "wait": "Pause the chain for a short or long delay in milliseconds.",
    "lock": "Temporarily or permanently keep the cursor pinned to one coordinate.",
    "scroll": "Scroll the mouse wheel at a position. Direction: up, down, left, right.",
    "hold_key": "Hold a key down for a duration in milliseconds. 0 = hold until chain stops.",
    "random_delay": "Pause for a random duration between min and max milliseconds — adds human-like timing.",
}


def _format_step(step: ActionStep) -> str:
    params = step.params
    if step.action == "move":
        return f"move -> ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "click":
        return f"click {params.get('button', '?')} -> ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "repeat_click":
        return (
            f"repeat_click {params.get('button', '?')} x{params.get('count', '?')} "
            f"-> ({params.get('x', '?')}, {params.get('y', '?')})"
        )
    if step.action == "keypress":
        return f"keypress '{params.get('key', '?')}'"
    if step.action == "wait":
        return f"wait {params.get('ms', '?')}ms"
    if step.action == "lock":
        duration = params.get("duration_ms", 0)
        duration_label = "forever" if duration == 0 else f"{duration}ms"
        return f"lock ({params.get('x', '?')}, {params.get('y', '?')}) {duration_label}"
    if step.action == "scroll":
        return f"scroll {params.get('direction', '?')} x{params.get('amount', '?')} @ ({params.get('x', '?')}, {params.get('y', '?')})"
    if step.action == "hold_key":
        duration = params.get("duration_ms", 0)
        duration_label = "until stopped" if duration == 0 else f"{duration}ms"
        return f"hold_key '{params.get('key', '?')}' {duration_label}"
    if step.action == "random_delay":
        return f"random_delay {params.get('min_ms', '?')}–{params.get('max_ms', '?')}ms"
    return step.action


class StepBuilderDialog:
    def __init__(self, parent: tk.Tk, profile_store, profile: Profile | None = None) -> None:
        self._profile_store = profile_store
        self._editing = profile
        self._steps: list[ActionStep] = list(profile.steps) if profile else []
        self._editing_step_index: int | None = None
        self.result: Profile | None = None

        self.top = tk.Toplevel(parent)
        self.top.title("Edit Profile" if profile else "New Profile")
        self.top.geometry("720x760")
        self.top.minsize(680, 720)
        self.top.resizable(True, True)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg=COLORS["bg"])
        configure_theme(self.top)

        shell = ttk.Frame(self.top, style="App.TFrame", padding=(22, 20, 22, 20))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        hero = ttk.Frame(shell, style="App.TFrame")
        hero.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            hero,
            text="Profile Builder",
            style="HeroTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            hero,
            text="Define a reusable action chain with optional hotkey bindings and ordered steps.",
            style="HeroBody.TLabel",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(6, 16))

        content = ttk.Frame(shell, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(1, weight=1)

        details = ttk.Frame(content, style="Card.TFrame", padding=(18, 18, 18, 18))
        details.grid(row=0, column=0, columnspan=2, sticky="ew")
        details.columnconfigure(0, weight=1)
        details.columnconfigure(1, weight=1)

        ttk.Label(details, text="Profile Name", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            details,
            text="Hotkey (optional, example: ctrl+alt+1)",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self._name_var = tk.StringVar(value=profile.name if profile else "")
        ttk.Entry(details, textvariable=self._name_var).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        initial_hotkey = profile.hotkey if profile and profile.hotkey else ""
        self._hotkey_var = tk.StringVar(value=initial_hotkey)
        ttk.Entry(details, textvariable=self._hotkey_var).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(8, 0)
        )

        ttk.Label(details, text="Repeat (0 = loop forever)", style="SectionTitle.TLabel").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )
        initial_repeat = str(profile.repeat) if profile else "1"
        self._repeat_var = tk.StringVar(value=initial_repeat)
        ttk.Entry(details, textvariable=self._repeat_var, width=8).grid(
            row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0)
        )

        steps_panel = ttk.Frame(content, style="Card.TFrame", padding=(18, 18, 18, 18))
        steps_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12), pady=(14, 0))
        steps_panel.columnconfigure(0, weight=1)
        steps_panel.rowconfigure(1, weight=1)

        steps_header = ttk.Frame(steps_panel, style="Card.TFrame")
        steps_header.grid(row=0, column=0, sticky="ew")
        steps_header.columnconfigure(0, weight=1)
        ttk.Label(steps_header, text="Chain Steps", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._step_count_label = ttk.Label(steps_header, text="0/50 steps", style="Badge.TLabel")
        self._step_count_label.grid(row=0, column=1, sticky="e")
        list_shell = tk.Frame(
            steps_panel,
            bg=COLORS["entry_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        list_shell.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        list_shell.grid_columnconfigure(0, weight=1)
        list_shell.grid_rowconfigure(0, weight=1)

        self._steps_listbox = tk.Listbox(
            list_shell,
            height=12,
            font=(MONO_FONT, 9),
            exportselection=False,
        )
        style_listbox(self._steps_listbox)
        self._steps_listbox.grid(row=0, column=0, sticky="nsew")
        self._steps_listbox.bind("<<ListboxSelect>>", self._on_step_select)

        step_scroll = ttk.Scrollbar(
            list_shell, orient="vertical", command=self._steps_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        step_scroll.grid(row=0, column=1, sticky="ns")
        self._steps_listbox.configure(yscrollcommand=step_scroll.set)

        step_btn_frame = ttk.Frame(steps_panel, style="Card.TFrame")
        step_btn_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(4):
            step_btn_frame.columnconfigure(column, weight=1)
        ttk.Button(step_btn_frame, text="Up", style="Secondary.TButton", command=self._move_up).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            step_btn_frame, text="Down", style="Secondary.TButton", command=self._move_down
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(
            step_btn_frame, text="Remove", style="Danger.TButton", command=self._remove_step
        ).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(
            step_btn_frame, text="Reset", style="Secondary.TButton", command=self._reset_step_form
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        editor_panel = ttk.Frame(content, style="Card.TFrame", padding=(18, 18, 18, 18))
        editor_panel.grid(row=1, column=1, sticky="nsew", pady=(14, 0))
        editor_panel.columnconfigure(0, weight=1)

        ttk.Label(editor_panel, text="Step Editor", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            editor_panel,
            text="Select an existing step to update it, or configure a new one below.",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(4, 14))

        action_frame = ttk.Frame(editor_panel, style="Card.TFrame")
        action_frame.pack(fill="x")
        ttk.Label(action_frame, text="Action", style="Panel.TLabel").pack(anchor="w")
        self._action_var = tk.StringVar(value="move")
        self._action_combo = ttk.Combobox(
            action_frame,
            textvariable=self._action_var,
            values=sorted(VALID_ACTIONS),
            state="readonly",
        )
        self._action_combo.pack(fill="x", pady=(8, 12))
        self._action_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._on_action_change(self._action_var.get()),
        )
        self._action_hint_label = tk.Label(
            editor_panel,
            text=_ACTION_HINTS["move"],
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self._action_hint_label.pack(fill="x", pady=(0, 12))

        action_tools = ttk.Frame(editor_panel, style="Card.TFrame")
        action_tools.pack(fill="x", pady=(0, 10))
        self._pick_btn = ttk.Button(
            action_tools,
            text="Pick Position",
            style="Secondary.TButton",
            command=self._pick_position,
        )
        self._pick_btn.pack(side="right")

        self._param_frame = ttk.Frame(editor_panel, style="Card.TFrame")
        self._param_frame.pack(fill="x")
        self._param_entries: dict[str, ttk.Entry] = {}
        self._param_vars: dict[str, tk.StringVar] = {}
        self._build_param_fields("move")

        self._add_step_btn = ttk.Button(
            editor_panel, text="+ Add Step", style="Primary.TButton", command=self._add_step
        )
        self._add_step_btn.pack(fill="x", pady=(16, 0))
        self._editing_state_label = tk.Label(
            editor_panel,
            text="Adding a new step",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
        )
        self._editing_state_label.pack(fill="x", pady=(10, 0))

        bottom_frame = ttk.Frame(shell, style="App.TFrame")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)
        ttk.Button(bottom_frame, text="Cancel", style="Secondary.TButton", command=self.top.destroy).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Button(bottom_frame, text="Save Profile", style="Primary.TButton", command=self._save).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        self._refresh_steps_list()

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

        self._param_frame.columnconfigure(1, weight=1)

        if action in _NEEDS_POSITION:
            self._pick_btn.pack(side="right")
        else:
            self._pick_btn.pack_forget()

    def _on_action_change(self, action: str) -> None:
        self._build_param_fields(action)
        self._action_hint_label.config(text=_ACTION_HINTS.get(action, "Configure this step."))

    def _load_step_into_form(self, step: ActionStep) -> None:
        self._action_var.set(step.action)
        self._build_param_fields(step.action)
        for name, value in step.params.items():
            if name in self._param_vars:
                self._param_vars[name].set(str(value))
        self._action_hint_label.config(text=_ACTION_HINTS.get(step.action, "Configure this step."))

    def _reset_step_form(self) -> None:
        self._editing_step_index = None
        self._steps_listbox.selection_clear(0, tk.END)
        self._action_var.set("move")
        self._build_param_fields("move")
        self._add_step_btn.config(text="+ Add Step")
        self._editing_state_label.config(text="Adding a new step")
        self._action_hint_label.config(text=_ACTION_HINTS["move"])

    def _refresh_steps_list(self) -> None:
        self._steps_listbox.delete(0, tk.END)
        for index, step in enumerate(self._steps, start=1):
            self._steps_listbox.insert(tk.END, f"{index}. {_format_step(step)}")
        can_add_new = len(self._steps) < MAX_STEPS or self._editing_step_index is not None
        self._add_step_btn.config(state="normal" if can_add_new else "disabled")
        self._step_count_label.config(text=f"{len(self._steps)}/{MAX_STEPS} steps")

    def _on_step_select(self, event) -> None:
        selection = self._steps_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self._editing_step_index = index
        self._load_step_into_form(self._steps[index])
        self._add_step_btn.config(text="Save Step")
        self._add_step_btn.config(state="normal")
        self._editing_state_label.config(text=f"Editing step {index + 1}")

    def _add_step(self) -> None:
        action = self._action_var.get()
        params: dict[str, object] = {}

        for name, var in self._param_vars.items():
            raw_value = var.get().strip()
            if name in _INT_PARAMS:
                try:
                    params[name] = int(raw_value)
                except ValueError:
                    messagebox.showwarning("Invalid", f"{name} must be an integer")
                    return
            else:
                params[name] = raw_value

        step = ActionStep(action=action, params=params)
        if not step.validate():
            messagebox.showwarning("Invalid", "Missing required parameters")
            return

        if self._editing_step_index is None:
            self._steps.append(step)
        else:
            self._steps[self._editing_step_index] = step
        self._refresh_steps_list()
        self._reset_step_form()

    def _remove_step(self) -> None:
        selection = self._steps_listbox.curselection()
        if not selection:
            return
        del self._steps[selection[0]]
        self._refresh_steps_list()
        self._reset_step_form()

    def _move_up(self) -> None:
        selection = self._steps_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        index = selection[0]
        self._steps[index - 1], self._steps[index] = self._steps[index], self._steps[index - 1]
        self._refresh_steps_list()
        self._steps_listbox.selection_set(index - 1)
        self._on_step_select(None)

    def _move_down(self) -> None:
        selection = self._steps_listbox.curselection()
        if not selection or selection[0] >= len(self._steps) - 1:
            return
        index = selection[0]
        self._steps[index], self._steps[index + 1] = self._steps[index + 1], self._steps[index]
        self._refresh_steps_list()
        self._steps_listbox.selection_set(index + 1)
        self._on_step_select(None)

    def _pick_position(self) -> None:
        self._pick_btn.config(state="disabled")
        self._countdown(3)

    def _countdown(self, remaining: int) -> None:
        if remaining > 0:
            self._pick_btn.config(text=f"{remaining}...")
            self.top.after(1000, lambda: self._countdown(remaining - 1))
            return

        pos = get_cursor_pos()
        if pos is not None:
            if "x" in self._param_vars:
                self._param_vars["x"].set(str(pos[0]))
            if "y" in self._param_vars:
                self._param_vars["y"].set(str(pos[1]))
        self._pick_btn.config(text="Pick Position", state="normal")

    def _save(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Invalid", "Name cannot be empty")
            return
        if not self._steps:
            messagebox.showwarning("Invalid", "Add at least one step")
            return

        hotkey = self._hotkey_var.get().strip() or None
        if hotkey:
            hotkey_lower = hotkey.lower()
            if hotkey_lower in SYSTEM_HOTKEYS:
                messagebox.showwarning("Conflict", f"{hotkey} conflicts with a system hotkey")
                return
            if self._profile_store is not None:
                for profile in self._profile_store.load():
                    if self._editing is not None and profile.id == self._editing.id:
                        continue
                    if profile.hotkey and profile.hotkey.lower() == hotkey_lower:
                        messagebox.showwarning(
                            "Conflict",
                            f"{hotkey} is already used by profile '{profile.name}'",
                        )
                        return

        repeat_raw = self._repeat_var.get().strip()
        try:
            repeat = int(repeat_raw)
            if repeat < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Repeat must be a whole number \u2265 0")
            return

        for index, step in enumerate(self._steps):
            if (
                step.action == "lock"
                and step.params.get("duration_ms", 0) == 0
                and index < len(self._steps) - 1
            ):
                messagebox.showinfo(
                    "Note",
                    f"Step {index + 1} is a permanent lock. Later steps will never run.",
                )
                break

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

        self.top.destroy()
