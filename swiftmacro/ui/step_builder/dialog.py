"""Modal profile editor — orchestrates the steps list and step editor panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from swiftmacro.constants import (
    MAX_STEPS,
    STEP_BUILDER_MIN_SIZE,
    STEP_BUILDER_SIZE,
    SYSTEM_HOTKEYS,
)
from swiftmacro.cursor import get_cursor_pos
from swiftmacro.models import ActionStep, Profile, VALID_ACTIONS
from swiftmacro.ui.step_builder.forms import (
    _ACTION_HINTS,
    _COMBO_VALUES,
    _INT_PARAMS,
    _NEEDS_POSITION,
    _PARAM_FIELDS,
    COMMON_KEYS,
)
from swiftmacro.ui.theme import COLORS, MONO_FONT, configure_theme, style_listbox


class StepBuilderDialog:
    """Toplevel window for adding or editing a single :class:`Profile`.

    The dialog is split internally into three areas:

    * a *details* card (name / hotkey / repeat),
    * a *steps* card (ordered list + reordering buttons),
    * a *step editor* card (action picker + dynamic parameter fields).

    Attribute names are kept underscore-prefixed because the test suite
    reaches into them by name (``_param_vars``, ``_steps``, ``_repeat_var``,
    ``_pick_btn`` and friends).
    """

    def __init__(self, parent: tk.Tk, profile_store, profile: Profile | None = None) -> None:
        self._profile_store = profile_store
        self._editing = profile
        self._steps: list[ActionStep] = list(profile.steps) if profile else []
        self._editing_step_index: int | None = None
        self.result: Profile | None = None

        self.top = tk.Toplevel(parent)
        self.top.title("Edit Profile" if profile else "New Profile")
        self.top.geometry(f"{STEP_BUILDER_SIZE[0]}x{STEP_BUILDER_SIZE[1]}")
        self.top.minsize(*STEP_BUILDER_MIN_SIZE)
        self.top.resizable(True, True)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg=COLORS["bg"])
        configure_theme(self.top)

        shell = ttk.Frame(self.top, style="App.TFrame", padding=(28, 24, 28, 24))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        self._build_hero(shell)

        content = ttk.Frame(shell, style="App.TFrame")
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5)
        content.columnconfigure(1, weight=4)
        content.rowconfigure(1, weight=1)

        self._build_details_card(content, profile)
        self._build_steps_panel(content)
        self._build_editor_panel(content)
        self._build_bottom_bar(shell)

        self._refresh_steps_list()

    # --- build helpers -----------------------------------------------------
    def _build_hero(self, shell: ttk.Frame) -> None:
        hero = ttk.Frame(shell, style="App.TFrame")
        hero.grid(row=0, column=0, sticky="ew")
        ttk.Label(hero, text="Profile Builder", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            hero,
            text="Define a reusable action chain with optional hotkey bindings and ordered steps.",
            style="HeroBody.TLabel",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(6, 18))

    def _build_details_card(self, content: ttk.Frame, profile: Profile | None) -> None:
        details = ttk.Frame(content, style="Card.TFrame", padding=(20, 18, 20, 20))
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
        ttk.Label(details, text="Repeat (0 = loop forever)", style="SectionTitle.TLabel").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )

        self._name_var = tk.StringVar(value=profile.name if profile else "")
        ttk.Entry(details, textvariable=self._name_var).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        initial_hotkey = profile.hotkey if profile and profile.hotkey else ""
        self._hotkey_var = tk.StringVar(value=initial_hotkey)
        ttk.Entry(details, textvariable=self._hotkey_var).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(8, 0)
        )

        initial_repeat = str(profile.repeat) if profile else "1"
        self._repeat_var = tk.StringVar(value=initial_repeat)
        ttk.Entry(details, textvariable=self._repeat_var, width=8).grid(
            row=1, column=2, sticky="w", padx=(12, 0), pady=(8, 0)
        )

    def _build_steps_panel(self, content: ttk.Frame) -> None:
        steps_panel = ttk.Frame(content, style="Card.TFrame", padding=(20, 18, 20, 20))
        steps_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 14), pady=(14, 0))
        steps_panel.columnconfigure(0, weight=1)
        steps_panel.rowconfigure(1, weight=1)

        steps_header = ttk.Frame(steps_panel, style="Card.TFrame")
        steps_header.grid(row=0, column=0, sticky="ew")
        steps_header.columnconfigure(0, weight=1)
        ttk.Label(steps_header, text="Chain Steps", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._step_count_label = ttk.Label(
            steps_header, text=f"0/{MAX_STEPS} steps", style="Badge.TLabel"
        )
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
            font=(MONO_FONT, 10),
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
        ttk.Button(
            step_btn_frame, text="↑  Up", style="Secondary.TButton", command=self._move_up,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            step_btn_frame, text="↓  Down", style="Secondary.TButton", command=self._move_down,
        ).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(
            step_btn_frame, text="✕  Remove", style="Danger.TButton", command=self._remove_step,
        ).grid(row=0, column=2, sticky="ew", padx=6)
        ttk.Button(
            step_btn_frame, text="Reset", style="Secondary.TButton", command=self._reset_step_form,
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

    def _build_editor_panel(self, content: ttk.Frame) -> None:
        editor_panel = ttk.Frame(content, style="Card.TFrame", padding=(20, 18, 20, 20))
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
            editor_panel, text="＋  Add Step", style="Primary.TButton", command=self._add_step
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

    def _build_bottom_bar(self, shell: ttk.Frame) -> None:
        bottom_frame = ttk.Frame(shell, style="App.TFrame")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)
        ttk.Button(
            bottom_frame, text="Cancel", style="Secondary.TButton", command=self.top.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            bottom_frame, text="✓  Save", style="Primary.TButton", command=self._save,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    # --- editor helpers ----------------------------------------------------
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
        self._action_hint_label.config(
            text=_ACTION_HINTS.get(step.action, "Configure this step.")
        )

    def _reset_step_form(self) -> None:
        self._editing_step_index = None
        self._steps_listbox.selection_clear(0, tk.END)
        self._action_var.set("move")
        self._build_param_fields("move")
        self._add_step_btn.config(text="＋  Add Step")
        self._editing_state_label.config(text="Adding a new step")
        self._action_hint_label.config(text=_ACTION_HINTS["move"])

    def _refresh_steps_list(self) -> None:
        self._steps_listbox.delete(0, tk.END)
        for index, step in enumerate(self._steps, start=1):
            self._steps_listbox.insert(tk.END, f"{index}. {step.format_label()}")
        can_add_new = len(self._steps) < MAX_STEPS or self._editing_step_index is not None
        self._add_step_btn.config(state="normal" if can_add_new else "disabled")
        self._step_count_label.config(text=f"{len(self._steps)}/{MAX_STEPS} steps")

    def _on_step_select(self, _event) -> None:
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
        if hotkey and not self._validate_hotkey(hotkey):
            return

        repeat_raw = self._repeat_var.get().strip()
        try:
            repeat = int(repeat_raw)
            if repeat < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Repeat must be a whole number \u2265 0")
            return

        if not self._warn_if_blocking_lock_not_last():
            return  # user opted to keep editing

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

    def _validate_hotkey(self, hotkey: str) -> bool:
        hotkey_lower = hotkey.lower()
        if hotkey_lower in SYSTEM_HOTKEYS:
            messagebox.showwarning("Conflict", f"{hotkey} conflicts with a system hotkey")
            return False
        if self._profile_store is None:
            return True
        for profile in self._profile_store.load():
            if self._editing is not None and profile.id == self._editing.id:
                continue
            if profile.hotkey and profile.hotkey.lower() == hotkey_lower:
                messagebox.showwarning(
                    "Conflict",
                    f"{hotkey} is already used by profile '{profile.name}'",
                )
                return False
        return True

    def _warn_if_blocking_lock_not_last(self) -> bool:
        """Return True if the user accepted (or there is no problem)."""
        for index, step in enumerate(self._steps):
            if (
                step.action == "lock"
                and step.params.get("duration_ms", 0) == 0
                and index < len(self._steps) - 1
            ):
                return messagebox.askyesno(
                    "Permanent lock blocks later steps",
                    (
                        f"Step {index + 1} is a permanent lock (duration 0 ms). "
                        f"All {len(self._steps) - index - 1} step(s) after it will "
                        f"never run.\n\nSave anyway?"
                    ),
                )
        return True
