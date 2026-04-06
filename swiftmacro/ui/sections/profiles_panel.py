"""Profiles panel — list of profiles, status line, progress bar, action buttons."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Sequence

from swiftmacro.constants import MAX_PROFILES
from swiftmacro.models import Profile
from swiftmacro.ui.theme import COLORS, FONT_FAMILY, HEADING_FONT


class ProfilesPanel:
    """Card showing the profile list with full CRUD action row.

    The main window provides command callbacks; this class never reaches into
    state directly. ``refresh()`` repopulates the tree, ``update_buttons()``
    syncs enabled/disabled states, ``update_progress()`` and
    ``toggle_empty_state()`` keep the secondary UI bits in sync.
    """

    def __init__(
        self,
        parent: ttk.Frame,
        on_add: Callable[[], None],
        on_edit: Callable[[], None],
        on_duplicate: Callable[[], None],
        on_delete: Callable[[], None],
        on_run: Callable[[], None],
        on_stop: Callable[[], None],
        on_select: Callable[[str], None],
    ) -> None:
        self._on_select = on_select
        self._all_profiles: list[Profile] = []
        self._active_id: str | None = None

        self.frame = ttk.Frame(parent, style="Card.TFrame", padding=(24, 22, 24, 22))
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(3, weight=1)

        self._build_header()
        self._build_status_label()
        self._build_progress_bar()
        self._build_list_and_empty_state(on_add)
        self._build_button_row(on_add, on_edit, on_duplicate, on_delete, on_run, on_stop)

    # --- build helpers -----------------------------------------------------
    def _build_header(self) -> None:
        header = ttk.Frame(self.frame, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        # Eyebrow (uppercase kicker) + title + subtitle
        title_block = ttk.Frame(header, style="Card.TFrame")
        title_block.grid(row=0, column=0, sticky="w")
        ttk.Label(title_block, text="LIBRARY", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(title_block, text="Profiles", style="SectionTitle.TLabel").pack(
            anchor="w", pady=(2, 4)
        )
        ttk.Label(
            title_block,
            text="Create reusable automation chains and run only the profile you actually need.",
            style="Muted.TLabel",
            wraplength=460,
            justify="left",
        ).pack(anchor="w")

        # Search field — sits to the right of the title block, vertically
        # centered. Wrapped in a 1px frame so we can give it a hairline accent
        # without fighting ttk's TEntry border state.
        search_wrap = tk.Frame(
            header,
            bg=COLORS["border"],
            highlightthickness=0,
            bd=0,
        )
        search_wrap.grid(row=0, column=1, sticky="e", padx=(16, 0))
        inner = tk.Frame(search_wrap, bg=COLORS["entry_bg"])
        inner.pack(padx=1, pady=1)
        tk.Label(
            inner,
            text="⌕",
            bg=COLORS["entry_bg"],
            fg=COLORS["accent"],
            font=(FONT_FAMILY, 12, "bold"),
            padx=10,
        ).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            inner,
            textvariable=self.search_var,
            bg=COLORS["entry_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(FONT_FAMILY, 10),
            width=22,
        )
        self.search_entry.pack(side="left", padx=(0, 12), pady=8, ipady=2)
        self.search_var.trace_add("write", lambda *_: self._on_search_changed())

    def _build_status_label(self) -> None:
        # Status line gets a thin accent bar on the left, like an editorial
        # callout — keeps the eye anchored without a full pill background.
        wrap = tk.Frame(self.frame, bg=COLORS["surface"])
        wrap.grid(row=1, column=0, sticky="ew", pady=(16, 14))
        tk.Frame(wrap, bg=COLORS["accent"], width=3).pack(side="left", fill="y")
        self.status_label = tk.Label(
            wrap,
            text="",
            bg=COLORS["surface"],
            fg=COLORS["accent"],
            font=(FONT_FAMILY, 10, "bold"),
            anchor="w",
            wraplength=560,
            justify="left",
            padx=12,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

    def _build_progress_bar(self) -> None:
        self.progress_bar = ttk.Progressbar(
            self.frame,
            orient="horizontal",
            mode="determinate",
            style="Teal.Horizontal.TProgressbar",
            maximum=100,
            value=0,
        )
        # Visibility is controlled by update_progress().

    def _build_list_and_empty_state(self, on_add: Callable[[], None]) -> None:
        self.list_shell = tk.Frame(
            self.frame,
            bg=COLORS["entry_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self.list_shell.grid(row=3, column=0, sticky="nsew")
        self.list_shell.grid_columnconfigure(0, weight=1)
        self.list_shell.grid_rowconfigure(0, weight=1)

        self.empty_state_frame = tk.Frame(
            self.frame,
            bg=COLORS["entry_bg"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        inner = tk.Frame(self.empty_state_frame, bg=COLORS["entry_bg"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(
            inner, text="◇", bg=COLORS["entry_bg"], fg=COLORS["accent"],
            font=(HEADING_FONT, 36),
        ).pack()
        tk.Label(
            inner, text="THE LIBRARY IS EMPTY",
            bg=COLORS["entry_bg"], fg=COLORS["eyebrow"],
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(pady=(10, 2))
        tk.Label(
            inner, text="No profiles yet",
            bg=COLORS["entry_bg"], fg=COLORS["text"],
            font=(HEADING_FONT, 16),
        ).pack()
        tk.Label(
            inner,
            text="Build a reusable action chain to get started.",
            bg=COLORS["entry_bg"], fg=COLORS["muted"],
            font=(FONT_FAMILY, 10),
        ).pack(pady=(4, 16))
        ttk.Button(
            inner, text="＋  Add your first profile",
            style="Primary.TButton", command=on_add,
        ).pack()

        self.profile_tree = ttk.Treeview(
            self.list_shell,
            columns=("name", "hotkey", "steps"),
            show="headings",
            selectmode="browse",
            style="App.Treeview",
        )
        self.profile_tree.heading("name",   text="Profile", anchor="w")
        self.profile_tree.heading("hotkey", text="Hotkey",  anchor="w")
        self.profile_tree.heading("steps",  text="Steps",   anchor="center")
        self.profile_tree.column("name",   stretch=True,  minwidth=150, anchor="w")
        self.profile_tree.column("hotkey", stretch=False, width=140,    anchor="w")
        self.profile_tree.column("steps",  stretch=False, width=64,     anchor="center")
        self.profile_tree.grid(row=0, column=0, sticky="nsew")
        self.profile_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        scroll = ttk.Scrollbar(
            self.list_shell, orient="vertical", command=self.profile_tree.yview,
            style="App.Vertical.TScrollbar",
        )
        scroll.grid(row=0, column=1, sticky="ns")
        self.profile_tree.configure(yscrollcommand=scroll.set)

    def _build_button_row(
        self,
        on_add: Callable[[], None],
        on_edit: Callable[[], None],
        on_duplicate: Callable[[], None],
        on_delete: Callable[[], None],
        on_run: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        row = ttk.Frame(self.frame, style="Card.TFrame")
        row.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        for column in range(6):
            row.columnconfigure(column, weight=1)

        self.add_btn = ttk.Button(
            row, text="＋  Add", style="Primary.TButton", command=on_add
        )
        self.add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.edit_btn = ttk.Button(
            row, text="✎  Edit", style="Secondary.TButton", command=on_edit
        )
        self.edit_btn.grid(row=0, column=1, sticky="ew", padx=6)
        self.duplicate_btn = ttk.Button(
            row, text="⊞  Copy", style="Secondary.TButton", command=on_duplicate
        )
        self.duplicate_btn.grid(row=0, column=2, sticky="ew", padx=6)
        self.delete_btn = ttk.Button(
            row, text="✕  Delete", style="Danger.TButton", command=on_delete
        )
        self.delete_btn.grid(row=0, column=3, sticky="ew", padx=6)
        self.run_btn = ttk.Button(
            row, text="▶  Run", style="Primary.TButton", command=on_run
        )
        self.run_btn.grid(row=0, column=4, sticky="ew", padx=6)
        self.stop_btn = ttk.Button(
            row, text="■  Stop", style="Secondary.TButton", command=on_stop
        )
        self.stop_btn.grid(row=0, column=5, sticky="ew", padx=(6, 0))

    # --- event glue --------------------------------------------------------
    def _on_tree_select(self, _event) -> None:
        selection = self.profile_tree.selection()
        if not selection:
            return
        self._on_select(selection[0])

    def _on_search_changed(self) -> None:
        self._render_tree()

    def _filtered_profiles(self) -> list[Profile]:
        query = self.search_var.get().strip().lower()
        if not query:
            return list(self._all_profiles)
        return [
            p for p in self._all_profiles
            if query in p.name.lower()
            or (p.hotkey and query in p.hotkey.lower())
        ]

    def _render_tree(self) -> None:
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        for profile in self._filtered_profiles():
            hotkey_str = profile.hotkey or "\u2014"
            self.profile_tree.insert(
                "", "end",
                iid=profile.id,
                values=(profile.name, hotkey_str, str(len(profile.steps))),
            )
        if self._active_id and self.profile_tree.exists(self._active_id):
            self.profile_tree.selection_set(self._active_id)
            self.profile_tree.see(self._active_id)

    # --- update API --------------------------------------------------------
    def refresh(self, profiles: Sequence[Profile], active_id: str | None) -> None:
        self._all_profiles = list(profiles)
        self._active_id = active_id
        self._render_tree()
        self.add_btn.config(
            state="disabled" if len(profiles) >= MAX_PROFILES else "normal"
        )

    def update_buttons(self, has_selection: bool, runner_busy: bool) -> None:
        idle_with_sel = "normal" if (has_selection and not runner_busy) else "disabled"
        self.edit_btn.config(state=idle_with_sel)
        self.duplicate_btn.config(state=idle_with_sel)
        self.delete_btn.config(state=idle_with_sel)
        self.run_btn.config(state=idle_with_sel)
        self.stop_btn.config(state="normal" if runner_busy else "disabled")

    def update_status_message(self, message: str) -> None:
        self.status_label.config(
            text=message or "Ready. Create, select or run a profile."
        )

    def update_progress(self, current: int, total: int, runner_busy: bool) -> None:
        if runner_busy and total > 0:
            pct = int(current / total * 100)
            self.progress_bar.config(value=pct)
            self.progress_bar.grid(row=2, column=0, sticky="ew")
        else:
            self.progress_bar.grid_remove()

    def toggle_empty_state(self, has_profiles: bool) -> None:
        if has_profiles:
            self.empty_state_frame.grid_remove()
            self.list_shell.grid()
        else:
            self.list_shell.grid_remove()
            self.empty_state_frame.grid(row=3, column=0, sticky="nsew")
