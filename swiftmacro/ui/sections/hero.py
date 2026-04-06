"""Hero section — gradient strip, brand block and automation status card.

Aesthetic notes
---------------
The hero is the only place in the app where we spend visual budget on
decoration. A 4-pixel mint→violet→amber gradient strip sits above the
brand block as a *signature*: it's the one thing the eye locks onto when
the window opens. Everything else stays restrained so the strip carries.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from swiftmacro.constants import APP_NAME, APP_VERSION, MAX_PROFILES
from swiftmacro.models import Profile
from swiftmacro.state import AppState
from swiftmacro.ui.theme import (
    COLORS,
    DISPLAY_FONT,
    FONT_FAMILY,
    HEADING_FONT,
    MONO_FONT,
    make_chip,
    paint_gradient_strip,
)


class HeroSection:
    """Top hero strip: gradient accent + brand block + automation status card."""

    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        tray_available: bool,
        on_open_update: Callable[[], None],
    ) -> None:
        self._state = state
        self._tray_available = tray_available
        self._on_open_update = on_open_update

        self.frame = ttk.Frame(parent, style="App.TFrame")
        self.frame.columnconfigure(0, weight=3)
        self.frame.columnconfigure(1, weight=2)

        self._build_gradient_strip()
        self._build_brand_block()
        self._build_status_card()

    # --- build helpers -----------------------------------------------------
    def _build_gradient_strip(self) -> None:
        """A 4px multi-stop gradient strip that anchors the entire hero.

        Painted on a Canvas so we can interpolate colors per pixel — ttk
        styles can't express this. Repaints on every <Configure> so the
        strip stretches with the window.
        """
        self._strip_canvas = tk.Canvas(
            self.frame,
            height=4,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self._strip_canvas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        self._strip_canvas.bind("<Configure>", self._repaint_strip)

    def _repaint_strip(self, event: tk.Event) -> None:
        paint_gradient_strip(
            self._strip_canvas,
            event.width,
            event.height,
            stops=[
                COLORS["accent"],
                COLORS["accent_glow"],
                COLORS["accent2"],
                COLORS["warning"],
            ],
        )

    def _build_brand_block(self) -> None:
        left = ttk.Frame(self.frame, style="App.TFrame")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 18))

        # Eyebrow — uppercase kicker that frames the wordmark
        ttk.Label(
            left,
            text=f"AUTOMATION  COCKPIT  ·  v{APP_VERSION}",
            style="EyebrowDark.TLabel",
        ).pack(anchor="w", pady=(0, 4))

        # Wordmark — large display font
        title_row = ttk.Frame(left, style="App.TFrame")
        title_row.pack(anchor="w")
        ttk.Label(title_row, text=APP_NAME, style="HeroTitle.TLabel").pack(side="left")
        # Trailing accent dot — a small signature
        tk.Label(
            title_row,
            text="●",
            bg=COLORS["bg"],
            fg=COLORS["accent"],
            font=(DISPLAY_FONT, 20),
        ).pack(side="left", padx=(10, 0), pady=(12, 0))

        ttk.Label(
            left,
            text=(
                "Profile-first desktop automation. Build reusable click, "
                "keypress, wait and lock flows — then launch them with a hotkey."
            ),
            style="HeroBody.TLabel",
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(8, 16))

        badge_row = ttk.Frame(left, style="App.TFrame")
        badge_row.pack(anchor="w")
        self.profile_count_label = ttk.Label(
            badge_row, text="0 profiles", style="Badge.TLabel"
        )
        self.profile_count_label.pack(side="left")
        ttk.Label(
            badge_row, text="·  Desktop automation hub", style="HeroBody.TLabel"
        ).pack(side="left", padx=(10, 0))

        chip_row = tk.Frame(left, bg=COLORS["bg"])
        chip_row.pack(anchor="w", pady=(16, 0))
        self.runner_chip = make_chip(
            chip_row,
            text="● IDLE",
            bg=COLORS["chip_idle_bg"],
            fg=COLORS["chip_idle_fg"],
        )
        self.runner_chip.pack(side="left")
        self.tray_chip = make_chip(
            chip_row,
            text="TRAY READY" if self._tray_available else "TRAY OFFLINE",
            bg=COLORS["chip_online_bg"] if self._tray_available else COLORS["chip_offline_bg"],
            fg=COLORS["success"] if self._tray_available else COLORS["warning"],
        )
        self.tray_chip.pack(side="left", padx=(10, 0))
        self.update_chip = make_chip(
            chip_row,
            text="↑  UPDATE AVAILABLE",
            bg=COLORS["chip_update_bg"],
            fg=COLORS["chip_update_fg"],
        )
        self.update_chip.bind("<Button-1>", lambda _e: self._on_open_update())
        self.update_chip.config(cursor="hand2")
        # Visibility controlled by update_update_chip().

    def _build_status_card(self) -> None:
        status_card = ttk.Frame(self.frame, style="AltCard.TFrame", padding=(22, 20, 22, 22))
        status_card.grid(row=1, column=1, sticky="nsew")
        status_card.columnconfigure(0, weight=1)

        ttk.Label(
            status_card, text="LIVE STATUS", style="EyebrowAlt.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            status_card, text="Automation Status", style="SectionAltTitle.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(2, 4))
        ttk.Label(
            status_card,
            text="Real-time read of what's running and which profile is in focus.",
            style="StatusBody.TLabel",
            wraplength=300,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(0, 18))

        # Hairline divider above the stat grid
        tk.Frame(status_card, bg=COLORS["divider"], height=1).grid(
            row=3, column=0, sticky="ew", pady=(0, 14)
        )

        stats = ttk.Frame(status_card, style="AltCard.TFrame")
        stats.grid(row=4, column=0, sticky="ew")
        stats.columnconfigure(0, weight=1)
        stats.columnconfigure(1, weight=1)

        self.pos_label = self._build_stat_cell(
            stats, column=0, eyebrow="CURRENT FOCUS", initial="No profile"
        )
        self.lock_label = self._build_stat_cell(
            stats, column=1, eyebrow="EXECUTION", initial="Idle", initial_dim=True
        )

    def _build_stat_cell(
        self,
        parent: ttk.Frame,
        column: int,
        eyebrow: str,
        initial: str,
        initial_dim: bool = False,
    ) -> tk.Label:
        cell = tk.Frame(parent, bg=COLORS["surface_alt"], highlightthickness=0)
        cell.grid(row=0, column=column, sticky="nsew",
                  padx=((0, 8) if column == 0 else (8, 0)))
        tk.Label(
            cell,
            text=eyebrow,
            bg=COLORS["surface_alt"],
            fg=COLORS["eyebrow"],
            font=(FONT_FAMILY, 8, "bold"),
            anchor="w",
        ).pack(fill="x")
        value = tk.Label(
            cell,
            text=initial,
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"] if initial_dim else COLORS["text"],
            font=(HEADING_FONT, 17),
            anchor="w",
        )
        value.pack(fill="x", pady=(6, 0))
        return value

    # --- update API --------------------------------------------------------
    def update_profile_count(self, count: int) -> None:
        self.profile_count_label.config(text=f"{count}/{MAX_PROFILES} PROFILES")

    def update_focus(self, profile: Profile | None) -> None:
        self.pos_label.config(
            text=profile.name if profile is not None else "No profile",
            fg=COLORS["text"] if profile is not None else COLORS["muted"],
        )

    def update_execution(
        self,
        runner_busy: bool,
        chain_active: bool,
        chain_pos: tuple[int, int] | None,
    ) -> None:
        if runner_busy:
            text, color = "Running", COLORS["success"]
        elif chain_active and chain_pos is not None:
            text, color = f"Lock {chain_pos[0]}, {chain_pos[1]}", COLORS["warning"]
        else:
            text, color = "Idle", COLORS["muted"]
        self.lock_label.config(text=text, fg=color)

    def update_runner_chip(self, runner_busy: bool) -> None:
        self.runner_chip.config(
            text="● RUNNING CHAIN" if runner_busy else "● IDLE",
            bg=COLORS["chip_running_bg"] if runner_busy else COLORS["chip_idle_bg"],
            fg=COLORS["success"] if runner_busy else COLORS["chip_idle_fg"],
        )

    def update_update_chip(self, available: bool) -> None:
        if available:
            self.update_chip.pack(side="left", padx=(10, 0))
        else:
            self.update_chip.pack_forget()
