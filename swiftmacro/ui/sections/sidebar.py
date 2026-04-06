"""Sidebar — selected profile details, import/export, hotkey hints, errors."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
from typing import Callable

from swiftmacro.models import Profile
from swiftmacro.state import AppState
from swiftmacro.ui.theme import COLORS, FONT_FAMILY, HEADING_FONT, MONO_FONT


def _format_relative_time(timestamp: float | None) -> str:
    """Render a Unix timestamp as 'just now' / '5m ago' / '2d ago'."""
    if timestamp is None:
        return "never"
    delta = max(0.0, time.time() - timestamp)
    if delta < 5:
        return "just now"
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"


class Sidebar:
    """Right-hand sidebar containing all secondary cards.

    Owns its widgets; the main window calls ``update_*`` methods from polling.
    """

    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        tray_available: bool,
        on_import: Callable[[], None],
        on_export: Callable[[], None],
    ) -> None:
        self._state = state
        self._tray_available = tray_available

        self.frame = ttk.Frame(parent, style="App.TFrame")
        self.frame.columnconfigure(0, weight=1)

        self._build_selected_profile_card()
        self._build_data_card(on_import, on_export)
        self._build_hotkey_card()
        self._build_error_frame()
        self._build_footer()

    # --- build helpers -----------------------------------------------------
    def _build_selected_profile_card(self) -> None:
        card = ttk.Frame(self.frame, style="Card.TFrame", padding=(22, 20, 22, 22))
        card.grid(row=0, column=0, sticky="ew")

        ttk.Label(card, text="IN FOCUS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(
            card, text="Selected Profile", style="SectionTitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        self.selected_profile_name = tk.Label(
            card,
            text="No profile selected",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(HEADING_FONT, 17),
            anchor="w",
            justify="left",
        )
        self.selected_profile_name.pack(fill="x", pady=(12, 2))

        self.selected_profile_meta = tk.Label(
            card,
            text="Choose a profile to inspect its hotkey and action chain.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 10),
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self.selected_profile_meta.pack(fill="x")

        # Step preview gets a small "PREVIEW" eyebrow + a bordered code block
        # styled to feel like a terminal printout. Mono font from theme.
        ttk.Label(card, text="STEP PREVIEW", style="Eyebrow.TLabel").pack(
            anchor="w", pady=(16, 4)
        )
        preview_wrap = tk.Frame(
            card,
            bg=COLORS["border"],
            highlightthickness=0,
            bd=0,
        )
        preview_wrap.pack(fill="x")
        preview_inner = tk.Frame(preview_wrap, bg=COLORS["entry_bg"])
        preview_inner.pack(fill="x", padx=1, pady=1)
        self.selected_profile_steps = tk.Label(
            preview_inner,
            text="No step preview available.",
            bg=COLORS["entry_bg"],
            fg=COLORS["text"],
            font=(MONO_FONT, 10),
            anchor="w",
            justify="left",
            wraplength=270,
            padx=14,
            pady=14,
        )
        self.selected_profile_steps.pack(fill="x")

    def _build_data_card(
        self,
        on_import: Callable[[], None],
        on_export: Callable[[], None],
    ) -> None:
        card = ttk.Frame(self.frame, style="Card.TFrame", padding=(22, 20, 22, 22))
        card.grid(row=1, column=0, sticky="ew", pady=(16, 0))

        ttk.Label(card, text="EXCHANGE", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(card, text="Data", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(2, 4)
        )
        ttk.Label(
            card,
            text="Import existing profile packs or export your selected automation setup.",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))

        self.import_btn = ttk.Button(
            card, text="↓  Import", style="Secondary.TButton", command=on_import
        )
        self.import_btn.pack(fill="x")
        self.export_btn = ttk.Button(
            card, text="↑  Export", style="Primary.TButton", command=on_export
        )
        self.export_btn.pack(fill="x", pady=(10, 0))

    def _build_hotkey_card(self) -> None:
        card = ttk.Frame(self.frame, style="Card.TFrame", padding=(22, 20, 22, 22))
        card.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        ttk.Label(card, text="SHORTCUTS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(card, text="Hotkeys", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(2, 10)
        )

        # Each shortcut as a row: action label on the left, monospaced key
        # combo on the right inside a small bordered chip.
        rows = [
            ("Run active profile", "Ctrl + Alt + R"),
            ("Stop chain",          "Ctrl + Alt + X"),
            ("Exit application",    "Ctrl + Alt + Esc"),
        ]
        for label, combo in rows:
            row = tk.Frame(card, bg=COLORS["surface"])
            row.pack(fill="x", pady=(0, 6))
            tk.Label(
                row, text=label,
                bg=COLORS["surface"], fg=COLORS["muted"],
                font=(FONT_FAMILY, 10), anchor="w",
            ).pack(side="left")
            chip = tk.Label(
                row, text=combo,
                bg=COLORS["entry_bg"], fg=COLORS["accent"],
                font=(MONO_FONT, 9, "bold"),
                padx=8, pady=2,
            )
            chip.pack(side="right")

        ttk.Label(
            card,
            text="UI keys: Ctrl+N add · F2 edit · Del delete · F5 run · Esc stop",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _build_error_frame(self) -> None:
        self.error_frame = tk.Frame(
            self.frame,
            bg=COLORS["error_bg"],
            highlightbackground=COLORS["error_border"],
            highlightthickness=1,
        )
        self.error_label = tk.Label(
            self.error_frame,
            text="",
            bg=COLORS["error_bg"],
            fg=COLORS["error_text"],
            anchor="w",
            justify="left",
            wraplength=280,
            padx=12,
            pady=12,
        )
        self.error_label.pack(fill="x")

    def _build_footer(self) -> None:
        footer = ttk.Frame(self.frame, style="Card.TFrame", padding=(22, 20, 22, 22))
        footer.grid(row=4, column=0, sticky="ew", pady=(16, 0))
        ttk.Label(footer, text="ENVIRONMENT", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(footer, text="Window Behavior", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(2, 6)
        )
        self.footer_label = ttk.Label(
            footer,
            text="",
            style="Muted.TLabel",
            wraplength=280,
            justify="left",
        )
        self.footer_label.pack(anchor="w", pady=(0, 0))

    # --- update API --------------------------------------------------------
    def update_selected_profile(self, profile: Profile | None, total_profiles: int) -> None:
        if profile is None:
            if total_profiles > 0:
                self.selected_profile_name.config(
                    text="No profile selected", fg=COLORS["text"]
                )
                self.selected_profile_meta.config(
                    text="Pick a profile from the list to see its hotkey, step count and preview."
                )
            else:
                self.selected_profile_name.config(text="No profiles yet", fg=COLORS["muted"])
                self.selected_profile_meta.config(
                    text="Create your first profile to build a reusable click or keypress flow."
                )
            self.selected_profile_steps.config(text="No step preview available.")
            return

        hotkey = profile.hotkey or "Manual run only"
        self.selected_profile_name.config(text=profile.name, fg=COLORS["text"])
        if profile.run_count > 0:
            history_line = (
                f"Runs: {profile.run_count} · last {_format_relative_time(profile.last_run_at)}"
            )
        else:
            history_line = "Runs: never"
        self.selected_profile_meta.config(
            text=(
                f"Hotkey: {hotkey}\n"
                f"Steps: {len(profile.steps)}\n"
                f"{history_line}"
            )
        )
        preview_lines = []
        for index, step in enumerate(profile.steps[:5], start=1):
            preview_lines.append(f"{index}. {step.format_label()}")
        if len(profile.steps) > 5:
            preview_lines.append(f"... +{len(profile.steps) - 5} more step(s)")
        self.selected_profile_steps.config(text="\n".join(preview_lines))

    def update_errors(self, errors: list[str]) -> None:
        if errors:
            self.error_label.config(text="\n".join(errors))
            self.error_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        else:
            self.error_frame.grid_forget()

    def update_footer(self) -> None:
        self.footer_label.config(
            text=(
                "Close hides the window to the tray when available. Use the tray icon or "
                "taskbar icon to bring the UI back instantly."
                if self._tray_available
                else "Tray is unavailable right now. Closing the window will exit the application."
            )
        )
