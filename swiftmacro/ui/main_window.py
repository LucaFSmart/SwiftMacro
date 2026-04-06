"""Main application window — orchestrates section panels and the poll loop.

This module owns very little: it wires together :class:`HeroSection`,
:class:`ProfilesPanel` and :class:`Sidebar`, routes user commands to the
:class:`ProfileManager`, and forwards periodic state into the sections via
``_poll()``. All widget construction lives in the section modules.
"""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from swiftmacro.constants import (
    APP_NAME,
    MAIN_WINDOW_MIN_SIZE,
    MAIN_WINDOW_SIZE,
    MAX_PROFILES,
    UI_POLL_MS,
)
from swiftmacro.profile_manager import ProfileManager
from swiftmacro.shutdown import ShutdownCoordinator
from swiftmacro.state import AppState
from swiftmacro.ui.sections import HeroSection, ProfilesPanel, Sidebar
from swiftmacro.ui.theme import COLORS, configure_theme


class MainWindow:
    def __init__(
        self,
        root: tk.Tk,
        state: AppState,
        tray_available: bool,
        profile_store=None,
        hotkey_mgr=None,
        action_runner=None,
        profile_manager: ProfileManager | None = None,
        shutdown: ShutdownCoordinator | None = None,
    ) -> None:
        self._root = root
        self._state = state
        self._profile_store = profile_store
        self._hotkey_mgr = hotkey_mgr
        self._action_runner = action_runner
        self._tray_available = tray_available
        self._shutdown = shutdown

        # If no manager was passed (legacy/test path), build one on the fly so
        # the rest of the UI only ever talks to the manager. The manager is
        # tolerant of profile_store=None — list() returns [] in that case.
        if profile_manager is not None:
            self._profile_manager = profile_manager
        elif profile_store is not None:
            self._profile_manager = ProfileManager(profile_store, hotkey_mgr)
        else:
            self._profile_manager = None

        self._style = configure_theme(root)

        root.title(f"{APP_NAME} Control Center")
        root.geometry(f"{MAIN_WINDOW_SIZE[0]}x{MAIN_WINDOW_SIZE[1]}")
        root.minsize(*MAIN_WINDOW_MIN_SIZE)
        root.configure(bg=COLORS["bg"])

        self._build_layout()
        self._wire_backwards_compat_attrs()
        self._bind_shortcuts()

        if tray_available:
            root.protocol("WM_DELETE_WINDOW", root.withdraw)
        else:
            root.protocol("WM_DELETE_WINDOW", self._on_close_no_tray)

        self._refresh_profile_list()
        self._update_action_buttons()
        root.after(UI_POLL_MS, self._poll)

    # --- layout ------------------------------------------------------------
    def _build_layout(self) -> None:
        shell = ttk.Frame(self._root, style="App.TFrame", padding=(28, 24, 28, 24))
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(1, weight=1)

        self._hero = HeroSection(
            shell,
            state=self._state,
            tray_available=self._tray_available,
            on_open_update=self._open_update_url,
        )
        self._hero.frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        self._profiles_panel = ProfilesPanel(
            shell,
            on_add=self._cmd_add,
            on_edit=self._cmd_edit,
            on_duplicate=self._cmd_duplicate,
            on_delete=self._cmd_delete,
            on_run=self._cmd_run,
            on_stop=self._cmd_stop_chain,
            on_select=self._on_profile_select,
        )
        self._profiles_panel.frame.grid(row=1, column=0, sticky="nsew", padx=(0, 14))

        self._sidebar = Sidebar(
            shell,
            state=self._state,
            tray_available=self._tray_available,
            on_import=self._cmd_import,
            on_export=self._cmd_export,
        )
        self._sidebar.frame.grid(row=1, column=1, sticky="nsew")

    def _wire_backwards_compat_attrs(self) -> None:
        """Expose section widgets under their legacy names for tests/callers.

        Older tests reach into ``MainWindow`` for things like ``_add_btn`` and
        ``_profile_tree``. Keep those attribute names alive without forcing
        section classes to use the underscore-prefixed style.
        """
        # Hero
        self._profile_count_label = self._hero.profile_count_label
        self._runner_chip = self._hero.runner_chip
        self._tray_chip = self._hero.tray_chip
        self._update_chip = self._hero.update_chip
        self._pos_label = self._hero.pos_label
        self._lock_label = self._hero.lock_label

        # Profiles panel
        self._status_label = self._profiles_panel.status_label
        self._progress_bar = self._profiles_panel.progress_bar
        self._list_shell = self._profiles_panel.list_shell
        self._empty_state_frame = self._profiles_panel.empty_state_frame
        self._profile_tree = self._profiles_panel.profile_tree
        self._add_btn = self._profiles_panel.add_btn
        self._edit_btn = self._profiles_panel.edit_btn
        self._duplicate_btn = self._profiles_panel.duplicate_btn
        self._delete_btn = self._profiles_panel.delete_btn
        self._run_btn = self._profiles_panel.run_btn
        self._stop_btn = self._profiles_panel.stop_btn

        # Sidebar
        self._selected_profile_name = self._sidebar.selected_profile_name
        self._selected_profile_meta = self._sidebar.selected_profile_meta
        self._selected_profile_steps = self._sidebar.selected_profile_steps
        self._import_btn = self._sidebar.import_btn
        self._export_btn = self._sidebar.export_btn
        self._error_frame = self._sidebar.error_frame
        self._error_label = self._sidebar.error_label
        self._footer_label = self._sidebar.footer_label

    # --- shortcuts ---------------------------------------------------------
    def _bind_shortcuts(self) -> None:
        """Wire UI-only keyboard shortcuts (in-window, not global hotkeys).

        Skipped when focus is inside an Entry/Combobox so typed text isn't
        eaten by Delete/Enter.
        """
        bindings: dict[str, callable] = {
            "<Control-n>": self._cmd_add,
            "<Control-N>": self._cmd_add,
            "<Control-d>": self._cmd_duplicate,
            "<Control-D>": self._cmd_duplicate,
            "<F2>": self._cmd_edit,
            "<Return>": self._cmd_edit,
            "<Delete>": self._cmd_delete,
            "<F5>": self._cmd_run,
            "<Escape>": self._cmd_stop_chain,
        }
        for sequence, handler in bindings.items():
            self._root.bind(sequence, self._make_shortcut_handler(handler))

    def _make_shortcut_handler(self, handler):
        def _handle(event):
            widget = event.widget
            try:
                cls = widget.winfo_class()
            except Exception:
                cls = ""
            if cls in {"TEntry", "Entry", "TCombobox", "Text"}:
                return None
            handler()
            return "break"
        return _handle

    # --- helpers -----------------------------------------------------------
    def _on_close_no_tray(self) -> None:
        """Window-close handler when the tray icon is unavailable.

        Routes through the :class:`ShutdownCoordinator` if available so we
        don't depend on legacy globals; falls back to ``root.destroy`` only
        as a last-resort safety net.
        """
        if self._shutdown is not None:
            self._shutdown.trigger()
        else:
            try:
                self._root.destroy()
            except Exception:
                pass

    def _open_update_url(self, _event=None) -> None:
        _, url = self._state.get_update_available()
        if url:
            webbrowser.open(url)

    def _load_profiles(self) -> list:
        if self._profile_manager is None:
            return []
        return self._profile_manager.list()

    def _selected_profile(self):
        profile_id = self._state.get_active_profile_id()
        if profile_id is None or self._profile_manager is None:
            return None
        return self._profile_manager.get(profile_id)

    def _refresh_profile_list(self) -> None:
        profiles = self._load_profiles()
        active_id = self._state.get_active_profile_id()
        self._profiles_panel.refresh(profiles, active_id)
        self._hero.update_profile_count(len(profiles))
        self._sidebar.update_selected_profile(self._selected_profile(), len(profiles))
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        has_selection = self._selected_profile() is not None
        runner_busy = self._state.get_runner_busy()
        self._profiles_panel.update_buttons(has_selection, runner_busy)

    def _on_profile_select(self, profile_id: str) -> None:
        self._state.set_active_profile_id(profile_id)
        self._sidebar.update_selected_profile(
            self._selected_profile(), len(self._load_profiles())
        )
        self._update_action_buttons()

    # --- commands ----------------------------------------------------------
    def _cmd_add(self) -> None:
        if self._profile_manager is None:
            return
        from swiftmacro.ui.step_builder import StepBuilderDialog

        dialog = StepBuilderDialog(self._root, self._profile_store)
        self._root.wait_window(dialog.top)
        if dialog.result is None:
            return
        self._profile_manager.add(dialog.result)
        self._state.set_active_profile_id(dialog.result.id)
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile saved: {dialog.result.name}")

    def _cmd_edit(self) -> None:
        if self._profile_manager is None:
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
        self._profile_manager.update(dialog.result)
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile updated: {dialog.result.name}")

    def _cmd_duplicate(self) -> None:
        if self._profile_manager is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        if len(self._load_profiles()) >= MAX_PROFILES:
            self._state.set_status_message(
                f"Cannot duplicate — max {MAX_PROFILES} profiles reached"
            )
            return
        duplicate = self._profile_manager.duplicate(profile.id)
        self._state.set_active_profile_id(duplicate.id)
        self._refresh_profile_list()
        self._state.set_status_message(f"Profile duplicated: {duplicate.name}")

    def _cmd_delete(self) -> None:
        if self._profile_manager is None:
            return
        profile = self._selected_profile()
        if profile is None:
            self._state.set_status_message("No profile selected")
            return
        if not messagebox.askyesno("Delete Profile", f"Delete profile '{profile.name}'?"):
            return
        self._profile_manager.delete(profile.id)
        self._state.set_active_profile_id(None)
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
        if self._profile_manager is None:
            return
        path = filedialog.askopenfilename(
            title="Import Profiles",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            result = self._profile_manager.import_file(path)
        except ValueError as exc:
            messagebox.showwarning("Import Failed", str(exc))
            return

        if result.imported_ids:
            self._state.set_active_profile_id(result.imported_ids[-1])
        self._refresh_profile_list()

        parts = [f"Imported {len(result.imported_ids)} profile(s)"]
        if result.cleared_hotkeys:
            parts.append(f"cleared {result.cleared_hotkeys} conflicting hotkey(s)")
        if result.skipped_invalid:
            parts.append(f"skipped {result.skipped_invalid} invalid profile(s)")
        self._state.set_status_message(", ".join(parts))

    def _cmd_export(self) -> None:
        if self._profile_manager is None:
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

        exported = self._profile_manager.export_file(
            path,
            [profile.id] if profile is not None else None,
        )
        if profile is not None:
            self._state.set_status_message(f"Exported '{profile.name}' (1 profile)")
        else:
            noun = "profile" if exported == 1 else "profiles"
            self._state.set_status_message(f"Exported {exported} {noun}")

    # --- backwards-compat shim ---------------------------------------------
    def _format_profile_step(self, step) -> str:
        """Legacy hook — kept so older tests/callers don't break."""
        return step.format_label()

    # --- poll loop ---------------------------------------------------------
    def _poll(self) -> None:
        if self._state.stop_event.is_set():
            return

        profile = self._selected_profile()
        chain_active, chain_pos = self._state.get_chain_lock()
        runner_busy = self._state.get_runner_busy()

        # Hero
        self._hero.update_focus(profile)
        self._hero.update_execution(runner_busy, chain_active, chain_pos)
        self._hero.update_runner_chip(runner_busy)
        available, _ = self._state.get_update_available()
        self._hero.update_update_chip(available)

        # Profiles panel
        self._profiles_panel.update_status_message(
            self._state.get_status_message().strip()
        )
        current, total = self._state.get_chain_progress()
        self._profiles_panel.update_progress(current, total, runner_busy)
        profiles = self._load_profiles()
        self._profiles_panel.toggle_empty_state(bool(profiles))

        # Sidebar
        self._sidebar.update_errors(self._state.get_hotkey_errors())
        self._sidebar.update_footer()
        self._sidebar.update_selected_profile(profile, len(profiles))

        self._update_action_buttons()
        self._root.after(UI_POLL_MS, self._poll)
