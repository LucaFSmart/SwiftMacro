"""Main application window with profile management."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from swiftmacro.constants import APP_NAME, MAX_PROFILES, UI_POLL_MS
from swiftmacro.hotkeys import _shutdown_ref
from swiftmacro.state import AppState
from swiftmacro.ui.theme import COLORS, HEADING_FONT, MONO_FONT, configure_theme, make_chip, style_listbox


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        state: AppState,
        tray_available: bool,
        profile_store=None,
        hotkey_mgr=None,
        action_runner=None,
    ) -> None:
        self._root = root
        self._state = state
        self._profile_store = profile_store
        self._hotkey_mgr = hotkey_mgr
        self._action_runner = action_runner
        self._tray_available = tray_available
        self._style = configure_theme(root)

        root.title(f"{APP_NAME} Control Center")
        root.geometry("980x720")
        root.minsize(920, 680)
        root.configure(bg=COLORS["bg"])

        self._build_layout()

        if tray_available:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)
        else:
            root.protocol("WM_DELETE_WINDOW", lambda: _shutdown_ref[0]())

        self._refresh_profile_list()
        self._update_action_buttons()
        root.after(UI_POLL_MS, self._poll)

    def _build_layout(self) -> None:
        shell = ttk.Frame(self._root, style="App.TFrame", padding=(26, 22, 26, 22))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(1, weight=1)

        self._build_hero(shell)
        self._build_profiles_panel(shell)
        self._build_sidebar(shell)

    def _build_hero(self, parent: ttk.Frame) -> None:
        hero = ttk.Frame(parent, style="App.TFrame")
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        hero.columnconfigure(0, weight=3)
        hero.columnconfigure(1, weight=2)

        left = ttk.Frame(hero, style="App.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        ttk.Label(left, text=APP_NAME, style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            text=(
                "Profile-first desktop automation for gamers and power users — build reusable click, keypress, wait and lock flows."
            ),
            style="HeroBody.TLabel",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(6, 14))

        badge_row = ttk.Frame(left, style="App.TFrame")
        badge_row.pack(anchor="w")
        self._profile_count_label = ttk.Label(badge_row, text="0 profiles", style="Badge.TLabel")
        self._profile_count_label.pack(side="left")
        ttk.Label(badge_row, text="Desktop automation hub", style="HeroBody.TLabel").pack(
            side="left", padx=(12, 0)
        )

        chip_row = tk.Frame(left, bg=COLORS["bg"])
        chip_row.pack(anchor="w", pady=(14, 0))
        self._runner_chip = make_chip(
            chip_row,
            text="Idle",
            bg=COLORS["chip_idle_bg"],
            fg=COLORS["chip_idle_fg"],
        )
        self._runner_chip.pack(side="left")
        self._tray_chip = make_chip(
            chip_row,
            text="Tray Ready" if self._tray_available else "Tray Offline",
            bg=COLORS["chip_online_bg"] if self._tray_available else COLORS["chip_offline_bg"],
            fg=COLORS["success"] if self._tray_available else COLORS["warning"],
        )
        self._tray_chip.pack(side="left", padx=(10, 0))
        self._update_chip = make_chip(
            chip_row,
            text="↑ Update available",
            bg=COLORS["chip_update_bg"],
            fg=COLORS["chip_update_fg"],
        )
        self._update_chip.bind(
            "<Button-1>",
            lambda _: webbrowser.open(self._state.get_update_available()[1]),
        )
        self._update_chip.config(cursor="hand2")
        # Note: _update_chip is intentionally NOT packed here — _poll() controls visibility
        tk.Label(
            left,
            text="Create a profile, preview its steps on the right, then run it directly or via hotkey.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=520,
        ).pack(anchor="w", pady=(18, 0))

        status_card = ttk.Frame(hero, style="AltCard.TFrame", padding=(18, 18, 18, 18))
        status_card.grid(row=0, column=1, sticky="nsew")
        status_card.columnconfigure(0, weight=1)
        ttk.Label(status_card, text="Automation Status", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            status_card,
            text="A quick read on what the app is doing right now and which profile is in focus.",
            style="StatusBody.TLabel",
            wraplength=280,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        stats = ttk.Frame(status_card, style="AltCard.TFrame")
        stats.grid(row=2, column=0, sticky="ew")
        stats.columnconfigure(0, weight=1)
        stats.columnconfigure(1, weight=1)

        pos_card = tk.Frame(stats, bg=COLORS["surface_alt"], highlightthickness=0)
        pos_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(
            pos_card,
            text="Current Focus",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")
        self._pos_label = tk.Label(
            pos_card,
            text="No profile",
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(HEADING_FONT, 16),
            anchor="w",
        )
        self._pos_label.pack(fill="x", pady=(4, 0))

        lock_card = tk.Frame(stats, bg=COLORS["surface_alt"], highlightthickness=0)
        lock_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(
            lock_card,
            text="Execution",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")
        self._lock_label = tk.Label(
            lock_card,
            text="Idle",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(HEADING_FONT, 16),
            anchor="w",
        )
        self._lock_label.pack(fill="x", pady=(4, 0))

    def _build_profiles_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Card.TFrame", padding=(18, 18, 18, 18))
        panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(3, weight=1)

        header = ttk.Frame(panel, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Profiles", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Create reusable automation chains and run only the profile you actually need.",
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self._status_label = tk.Label(
            panel,
            text="",
            bg=COLORS["surface"],
            fg=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            wraplength=560,
            justify="left",
        )
        self._status_label.grid(row=1, column=0, sticky="ew", pady=(12, 12))

        self._progress_bar = ttk.Progressbar(
            panel,
            orient="horizontal",
            mode="determinate",
            style="Teal.Horizontal.TProgressbar",
            maximum=100,
            value=0,
        )
        # Do NOT grid here — _poll() shows/hides it

        list_shell = tk.Frame(panel, bg=COLORS["entry_bg"], highlightbackground=COLORS["border"], highlightthickness=1)
        self._list_shell = list_shell
        list_shell.grid(row=3, column=0, sticky="nsew")
        list_shell.grid_columnconfigure(0, weight=1)
        list_shell.grid_rowconfigure(0, weight=1)

        self._empty_state_frame = tk.Frame(
            panel,
            bg=COLORS["entry_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        # Same grid slot as list_shell (row 3) — starts NOT gridded, _poll() controls visibility
        inner = tk.Frame(self._empty_state_frame, bg=COLORS["entry_bg"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            inner, text="⚡", bg=COLORS["entry_bg"], fg=COLORS["accent"],
            font=("Segoe UI", 28),
        ).pack()
        ttk.Label(inner, text="No profiles yet", style="SectionTitle.TLabel").pack(pady=(6, 0))
        ttk.Label(
            inner,
            text="Build a reusable action chain to get started",
            style="Muted.TLabel",
        ).pack(pady=(4, 12))
        ttk.Button(
            inner, text="＋ Add your first profile",
            style="Primary.TButton", command=self._cmd_add,
        ).pack()

        self._profile_listbox = tk.Listbox(
            list_shell,
            height=12,
            font=(MONO_FONT, 10),
            exportselection=False,
        )
        style_listbox(self._profile_listbox)
        self._profile_listbox.grid(row=0, column=0, sticky="nsew")
        self._profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        profile_scroll = ttk.Scrollbar(
            list_shell, orient="vertical", command=self._profile_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        profile_scroll.grid(row=0, column=1, sticky="ns")
        self._profile_listbox.configure(yscrollcommand=profile_scroll.set)

        profile_btn_frame = ttk.Frame(panel, style="Card.TFrame")
        profile_btn_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        for column in range(6):
            profile_btn_frame.columnconfigure(column, weight=1)

        self._add_btn = ttk.Button(
            profile_btn_frame, text="Add", style="Primary.TButton", command=self._cmd_add
        )
        self._add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._edit_btn = ttk.Button(
            profile_btn_frame, text="Edit", style="Secondary.TButton", command=self._cmd_edit
        )
        self._edit_btn.grid(row=0, column=1, sticky="ew", padx=6)
        self._duplicate_btn = ttk.Button(
            profile_btn_frame,
            text="Duplicate",
            style="Secondary.TButton",
            command=self._cmd_duplicate,
        )
        self._duplicate_btn.grid(row=0, column=2, sticky="ew", padx=6)
        self._delete_btn = ttk.Button(
            profile_btn_frame, text="Delete", style="Danger.TButton", command=self._cmd_delete
        )
        self._delete_btn.grid(row=0, column=3, sticky="ew", padx=6)
        self._run_btn = ttk.Button(
            profile_btn_frame, text="Run", style="Primary.TButton", command=self._cmd_run
        )
        self._run_btn.grid(row=0, column=4, sticky="ew", padx=6)
        self._stop_btn = ttk.Button(
            profile_btn_frame,
            text="Stop",
            style="Secondary.TButton",
            command=self._cmd_stop_chain,
        )
        self._stop_btn.grid(row=0, column=5, sticky="ew", padx=(6, 0))

    def _build_sidebar(self, parent: ttk.Frame) -> None:
        sidebar = ttk.Frame(parent, style="App.TFrame")
        sidebar.grid(row=1, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)

        profile_card = ttk.Frame(sidebar, style="Card.TFrame", padding=(18, 18, 18, 18))
        profile_card.grid(row=0, column=0, sticky="ew")
        ttk.Label(profile_card, text="Selected Profile", style="SectionTitle.TLabel").pack(anchor="w")
        self._selected_profile_name = tk.Label(
            profile_card,
            text="No profile selected",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(HEADING_FONT, 16),
            anchor="w",
            justify="left",
        )
        self._selected_profile_name.pack(fill="x", pady=(8, 2))
        self._selected_profile_meta = tk.Label(
            profile_card,
            text="Choose a profile to inspect its hotkey and action chain.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self._selected_profile_meta.pack(fill="x")
        self._selected_profile_steps = tk.Label(
            profile_card,
            text="No steps to preview yet.",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Consolas", 9),
            anchor="w",
            justify="left",
            wraplength=280,
            padx=10,
            pady=10,
        )
        self._selected_profile_steps.pack(fill="x", pady=(12, 0))

        import_card = ttk.Frame(sidebar, style="Card.TFrame", padding=(18, 18, 18, 18))
        import_card.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(import_card, text="Data", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            import_card,
            text="Import existing profile packs or export your selected automation setup.",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(4, 14))

        self._import_btn = ttk.Button(
            import_card, text="Import Profiles", style="Secondary.TButton", command=self._cmd_import
        )
        self._import_btn.pack(fill="x")
        self._export_btn = ttk.Button(
            import_card, text="Export Selection", style="Primary.TButton", command=self._cmd_export
        )
        self._export_btn.pack(fill="x", pady=(10, 0))

        hotkey_card = ttk.Frame(sidebar, style="Card.TFrame", padding=(18, 18, 18, 18))
        hotkey_card.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(hotkey_card, text="Hotkeys", style="SectionTitle.TLabel").pack(anchor="w")
        hotkey_text = (
            "Run Active Profile: Ctrl+Alt+R\n"
            "Stop Chain: Ctrl+Alt+X\n"
            "Exit: Ctrl+Alt+Esc"
        )
        ttk.Label(
            hotkey_card,
            text=hotkey_text,
            style="Muted.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            hotkey_card,
            text="Manual cursor controls still exist in the background, but the UI now stays focused on profiles.",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

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

        footer = ttk.Frame(sidebar, style="Card.TFrame", padding=(18, 18, 18, 18))
        footer.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(footer, text="Window Behavior", style="SectionTitle.TLabel").pack(anchor="w")
        self._footer_label = ttk.Label(
            footer,
            text=(
                "Close hides the window to the tray when available. Use the tray icon or "
                "taskbar icon to bring the UI back instantly."
            ),
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        )
        self._footer_label.pack(anchor="w", pady=(4, 0))

    def _load_profiles(self) -> list:
        if self._profile_store is None:
            return []
        return self._profile_store.load()

    def _selected_profile(self):
        profile_id = self._state.get_active_profile_id()
        if profile_id is None or self._profile_store is None:
            return None
        return self._profile_store.get_by_id(profile_id)

    def _refresh_profile_list(self) -> None:
        self._profile_listbox.delete(0, tk.END)
        profiles = self._load_profiles()
        active_id = self._state.get_active_profile_id()
        active_index = None

        for index, profile in enumerate(profiles):
            marker = "ACTIVE" if profile.id == active_id else "READY "
            hotkey_str = profile.hotkey or "manual"
            step_count = len(profile.steps)
            self._profile_listbox.insert(
                tk.END,
                f"{marker:<6}  {profile.name:<18}  {step_count:>2} steps  [{hotkey_str:<14}]",
            )
            if profile.id == active_id:
                active_index = index

        if active_index is not None:
            self._profile_listbox.selection_clear(0, tk.END)
            self._profile_listbox.selection_set(active_index)

        self._profile_count_label.config(text=f"{len(profiles)}/{MAX_PROFILES} profiles")
        self._update_profile_details()
        self._add_btn.config(state="disabled" if len(profiles) >= MAX_PROFILES else "normal")
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        has_selection = self._selected_profile() is not None
        runner_busy = self._state.get_runner_busy()
        self._edit_btn.config(state="normal" if has_selection and not runner_busy else "disabled")
        self._duplicate_btn.config(state="normal" if has_selection and not runner_busy else "disabled")
        self._delete_btn.config(state="normal" if has_selection and not runner_busy else "disabled")
        self._run_btn.config(state="normal" if has_selection and not runner_busy else "disabled")
        self._stop_btn.config(state="normal" if runner_busy else "disabled")

    def _on_profile_select(self, event) -> None:
        selection = self._profile_listbox.curselection()
        profiles = self._load_profiles()
        if not selection or selection[0] >= len(profiles):
            return
        self._state.set_active_profile_id(profiles[selection[0]].id)
        self._refresh_profile_list()

    def _cmd_add(self) -> None:
        if self._profile_store is None:
            return
        from swiftmacro.ui.step_builder import StepBuilderDialog

        dialog = StepBuilderDialog(self._root, self._profile_store)
        self._root.wait_window(dialog.top)
        if dialog.result is None:
            return
        self._profile_store.add_profile(dialog.result)
        self._state.set_active_profile_id(dialog.result.id)
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile saved: {dialog.result.name}")

    def _cmd_edit(self) -> None:
        if self._profile_store is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        from swiftmacro.ui.step_builder import StepBuilderDialog

        dialog = StepBuilderDialog(self._root, self._profile_store, profile)
        self._root.wait_window(dialog.top)
        if dialog.result is None:
            return
        self._profile_store.update_profile(dialog.result)
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile updated: {dialog.result.name}")

    def _cmd_duplicate(self) -> None:
        if self._profile_store is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        duplicate = self._profile_store.duplicate_profile(profile.id)
        self._state.set_active_profile_id(duplicate.id)
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile duplicated: {duplicate.name}")

    def _cmd_delete(self) -> None:
        if self._profile_store is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        confirmed = messagebox.askyesno("Delete Profile", f"Delete profile '{profile.name}'?")
        if not confirmed:
            return
        self._profile_store.delete_profile(profile.id)
        self._state.set_active_profile_id(None)
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile deleted: {profile.name}")

    def _cmd_run(self) -> None:
        if self._action_runner is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        self._action_runner.run_profile(profile)

    def _cmd_stop_chain(self) -> None:
        if self._action_runner is not None:
            self._action_runner.stop()

    def _cmd_import(self) -> None:
        if self._profile_store is None:
            return
        path = filedialog.askopenfilename(
            title="Import Profiles",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            result = self._profile_store.import_profiles(path)
        except ValueError as exc:
            messagebox.showwarning("Import Failed", str(exc))
            return

        if result.imported_ids:
            self._state.set_active_profile_id(result.imported_ids[-1])
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.refresh_profile_hotkeys(self._profile_store.load())
        self._refresh_profile_list()

        parts = [f"Imported {len(result.imported_ids)} profile(s)"]
        if result.cleared_hotkeys:
            parts.append(f"cleared {result.cleared_hotkeys} conflicting hotkey(s)")
        if result.skipped_invalid:
            parts.append(f"skipped {result.skipped_invalid} invalid profile(s)")
        self._state.set_status_message(", ".join(parts))

    def _cmd_export(self) -> None:
        if self._profile_store is None:
            return
        profile = self._selected_profile()
        default_name = f"{profile.name}.json" if profile is not None else "profiles.json"
        path = filedialog.asksaveasfilename(
            title="Export Profiles",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return

        exported = self._profile_store.export_profiles(
            path,
            [profile.id] if profile is not None else None,
        )
        scope = "profile(s)" if profile is None else "profile"
        self._state.set_status_message(f"Exported {exported} {scope}")

    def _update_profile_details(self) -> None:
        profile = self._selected_profile()
        if profile is None:
            profiles = self._load_profiles()
            if profiles:
                self._selected_profile_name.config(text="No profile selected", fg=COLORS["text"])
                self._selected_profile_meta.config(
                    text="Pick a profile from the list to see its hotkey, step count and preview."
                )
            else:
                self._selected_profile_name.config(text="No profiles yet", fg=COLORS["muted"])
                self._selected_profile_meta.config(
                    text="Create your first profile to build a reusable click or keypress flow."
                )
            self._selected_profile_steps.config(text="No step preview available.")
            return

        hotkey = profile.hotkey or "Manual run only"
        self._selected_profile_name.config(text=profile.name, fg=COLORS["text"])
        self._selected_profile_meta.config(
            text=f"Hotkey: {hotkey}\nSteps: {len(profile.steps)}",
        )
        preview_lines = []
        for index, step in enumerate(profile.steps[:5], start=1):
            preview_lines.append(f"{index}. {self._format_profile_step(step)}")
        if len(profile.steps) > 5:
            preview_lines.append(f"... +{len(profile.steps) - 5} more step(s)")
        self._selected_profile_steps.config(text="\n".join(preview_lines))

    def _format_profile_step(self, step) -> str:
        params = step.params
        if step.action == "move":
            return f"Move to {params.get('x')}, {params.get('y')}"
        if step.action == "click":
            return f"{params.get('button', 'left').title()} click at {params.get('x')}, {params.get('y')}"
        if step.action == "repeat_click":
            return (
                f"{params.get('button', 'left').title()} click x{params.get('count')} "
                f"at {params.get('x')}, {params.get('y')}"
            )
        if step.action == "keypress":
            return f"Press key '{params.get('key')}'"
        if step.action == "wait":
            return f"Wait {params.get('ms')} ms"
        if step.action == "lock":
            duration = params.get("duration_ms", 0)
            suffix = "forever" if duration == 0 else f"{duration} ms"
            return f"Lock at {params.get('x')}, {params.get('y')} for {suffix}"
        return step.action

    def _poll(self) -> None:
        if self._state.stop_event.is_set():
            return

        profile = self._selected_profile()
        chain_active, chain_pos = self._state.get_chain_lock()
        runner_busy = self._state.get_runner_busy()

        self._pos_label.config(
            text=profile.name if profile is not None else "No profile",
            fg=COLORS["text"] if profile is not None else COLORS["muted"],
        )

        if runner_busy:
            lock_text = "Running"
            lock_color = COLORS["success"]
        elif chain_active and chain_pos is not None:
            lock_text = f"Lock at {chain_pos[0]}, {chain_pos[1]}"
            lock_color = COLORS["warning"]
        else:
            lock_text = "Idle"
            lock_color = COLORS["muted"]
        self._lock_label.config(text=lock_text, fg=lock_color)

        status_message = self._state.get_status_message().strip()
        self._status_label.config(
            text=status_message or "Ready. Create, select or run a profile."
        )

        errors = self._state.get_hotkey_errors()
        if errors:
            self._error_label.config(text="\n".join(errors))
            self._error_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        else:
            self._error_frame.grid_forget()

        self._runner_chip.config(
            text="Running Chain" if runner_busy else "Idle",
            bg=COLORS["chip_running_bg"] if runner_busy else COLORS["chip_idle_bg"],
            fg=COLORS["success"] if runner_busy else COLORS["chip_idle_fg"],
        )
        available, _ = self._state.get_update_available()
        if available:
            self._update_chip.pack(side="left", padx=(10, 0))
        else:
            self._update_chip.pack_forget()
        self._footer_label.config(
            text=(
                "Close hides the window to the tray when available. Use the tray icon or "
                "taskbar icon to bring the UI back instantly."
                if self._tray_available
                else "Tray is unavailable right now. Closing the window will exit the application."
            )
        )
        self._update_profile_details()
        self._update_action_buttons()

        current, total = self._state.get_chain_progress()
        if self._state.get_runner_busy() and total > 0:
            pct = int(current / total * 100)
            self._progress_bar.config(value=pct)
            self._progress_bar.grid(row=2, column=0, sticky="ew")
        else:
            self._progress_bar.grid_remove()

        # Using _load_profiles() rather than _profile_store.load() directly — safer: handles profile_store=None
        profiles = self._load_profiles()
        if profiles:
            self._empty_state_frame.grid_remove()
            self._list_shell.grid()
        else:
            self._list_shell.grid_remove()
            self._empty_state_frame.grid(row=3, column=0, sticky="nsew")

        self._root.after(UI_POLL_MS, self._poll)
