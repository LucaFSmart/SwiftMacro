import tkinter as tk

import pytest

from swiftmacro.constants import MAX_STEPS
from swiftmacro.models import ActionStep, Profile
from swiftmacro.state import make_state
from swiftmacro.ui.main_window import MainWindow
from swiftmacro.ui.step_builder import StepBuilderDialog


class _Store:
    def __init__(self, profiles):
        self._profiles = list(profiles)

    def load(self):
        return list(self._profiles)

    def get_by_id(self, profile_id):
        return next((p for p in self._profiles if p.id == profile_id), None)


def _widget_state(widget) -> str:
    return str(widget.cget("state"))


def _make_profile():
    return Profile(
        id="p1",
        name="Farm",
        hotkey="ctrl+alt+1",
        steps=[ActionStep(action="move", params={"x": 10, "y": 20})],
    )


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


def test_main_window_buttons_disabled_without_active_profile(tk_root):
    state = make_state()
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=_Store([_make_profile()]))
    tk_root.update_idletasks()

    assert _widget_state(ui._add_btn) == "normal"
    assert _widget_state(ui._edit_btn) == "disabled"
    assert _widget_state(ui._duplicate_btn) == "disabled"
    assert _widget_state(ui._delete_btn) == "disabled"
    assert _widget_state(ui._run_btn) == "disabled"
    assert _widget_state(ui._stop_btn) == "disabled"

    for child in tk_root.winfo_children():
        child.destroy()


def test_main_window_stop_enabled_while_runner_busy(tk_root):
    state = make_state()
    profile = _make_profile()
    state.set_active_profile_id(profile.id)
    state.set_runner_busy(True)
    ui = MainWindow(tk_root, state, tray_available=False, profile_store=_Store([profile]))
    tk_root.update_idletasks()

    assert _widget_state(ui._edit_btn) == "disabled"
    assert _widget_state(ui._duplicate_btn) == "disabled"
    assert _widget_state(ui._delete_btn) == "disabled"
    assert _widget_state(ui._run_btn) == "disabled"
    assert _widget_state(ui._stop_btn) == "normal"

    for child in tk_root.winfo_children():
        child.destroy()


def test_main_window_profile_details_show_selected_profile(tk_root):
    state = make_state()
    profile = _make_profile()
    state.set_active_profile_id(profile.id)
    ui = MainWindow(tk_root, state, tray_available=True, profile_store=_Store([profile]))
    tk_root.update_idletasks()

    assert ui._selected_profile_name.cget("text") == "Farm"
    assert "Hotkey: ctrl+alt+1" in ui._selected_profile_meta.cget("text")
    assert "Move to 10, 20" in ui._selected_profile_steps.cget("text")
    assert ui._tray_chip.cget("text") == "Tray Ready"

    for child in tk_root.winfo_children():
        child.destroy()


def test_step_builder_pick_button_visibility_changes_by_action(tk_root):
    dialog = StepBuilderDialog(tk_root, _Store([]))
    tk_root.update_idletasks()
    assert dialog._pick_btn.winfo_manager() == "pack"

    dialog._on_action_change("keypress")
    tk_root.update_idletasks()
    assert dialog._pick_btn.winfo_manager() == ""

    dialog.top.destroy()


def test_step_builder_can_edit_existing_step(tk_root):
    profile = Profile(
        id="p2",
        name="Edit Me",
        hotkey=None,
        steps=[ActionStep(action="move", params={"x": 10, "y": 20})],
    )
    dialog = StepBuilderDialog(tk_root, _Store([]), profile)
    dialog._steps_listbox.selection_set(0)
    dialog._on_step_select(None)
    dialog._param_vars["x"].set("99")
    dialog._param_vars["y"].set("88")

    dialog._add_step()

    assert len(dialog._steps) == 1
    assert dialog._steps[0].params == {"x": 99, "y": 88}
    assert dialog._add_step_btn.cget("text") == "+ Add Step"

    dialog.top.destroy()


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


def test_step_builder_can_edit_when_profile_is_at_max_steps(tk_root):
    profile = Profile(
        id="p3",
        name="Full",
        hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 1}) for _ in range(MAX_STEPS)],
    )
    dialog = StepBuilderDialog(tk_root, _Store([]), profile)
    tk_root.update_idletasks()

    assert _widget_state(dialog._add_step_btn) == "disabled"

    dialog._steps_listbox.selection_set(0)
    dialog._on_step_select(None)
    tk_root.update_idletasks()

    assert dialog._add_step_btn.cget("text") == "Save Step"
    assert _widget_state(dialog._add_step_btn) == "normal"

    dialog.top.destroy()


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
    assert chip.cget("bg") == COLORS["chip_idle_bg"]
    assert chip.cget("fg") == COLORS["chip_idle_fg"]
    chip.destroy()


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
