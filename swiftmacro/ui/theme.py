"""Shared UI theme tokens and ttk styling."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

FONT_FAMILY = "Segoe UI"
HEADING_FONT = "Bahnschrift SemiBold"
MONO_FONT = "Consolas"

COLORS: dict[str, str] = {
    "bg": "#0b1220",
    "surface": "#111a2b",
    "surface_alt": "#162238",
    "surface_soft": "#1c2b45",
    "border": "#243552",
    "text": "#ecf3ff",
    "muted": "#93a6c7",
    "accent": "#4fd1c5",
    "accent_active": "#2fb3a9",
    "danger": "#ff7a90",
    "warning": "#f6c177",
    "success": "#7ce0a7",
    "badge": "#12243a",
    "entry_bg": "#0e1728",
    "selection": "#1f4468",
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
}


def configure_theme(root: tk.Misc) -> ttk.Style:
    """Apply a consistent ttk theme to the application."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLORS["bg"])
    root.option_add("*Font", f"{{{FONT_FAMILY}}} 10")
    root.option_add("*TCombobox*Listbox.background", COLORS["surface"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure(
        "App.TFrame",
        background=COLORS["bg"],
    )
    style.configure(
        "Card.TFrame",
        background=COLORS["surface"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "AltCard.TFrame",
        background=COLORS["surface_alt"],
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Panel.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "HeroTitle.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=(HEADING_FONT, 22),
    )
    style.configure(
        "HeroBody.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=(HEADING_FONT, 13),
    )
    style.configure(
        "Value.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=(HEADING_FONT, 18),
    )
    style.configure(
        "Badge.TLabel",
        background=COLORS["badge"],
        foreground=COLORS["accent"],
        font=(FONT_FAMILY, 9, "bold"),
        padding=(10, 4),
    )
    style.configure(
        "StatusValue.TLabel",
        background=COLORS["surface_alt"],
        foreground=COLORS["accent"],
        font=(HEADING_FONT, 18),
    )
    style.configure(
        "StatusBody.TLabel",
        background=COLORS["surface_alt"],
        foreground=COLORS["muted"],
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "TButton",
        padding=(12, 8),
        font=(FONT_FAMILY, 10),
        borderwidth=0,
        focusthickness=0,
    )
    style.map(
        "TButton",
        background=[("active", COLORS["surface_soft"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["accent"],
        foreground="#081018",
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["accent_active"]), ("disabled", COLORS["surface_soft"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["surface_soft"],
        foreground=COLORS["text"],
    )
    style.map(
        "Secondary.TButton",
        background=[("active", COLORS["selection"]), ("disabled", COLORS["surface_soft"])],
    )
    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="#22060d",
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#f05f78"), ("disabled", COLORS["surface_soft"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "TEntry",
        fieldbackground=COLORS["entry_bg"],
        foreground=COLORS["text"],
        insertcolor=COLORS["text"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(8, 6),
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["entry_bg"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["accent"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(8, 6),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["entry_bg"])],
        selectbackground=[("readonly", COLORS["entry_bg"])],
        selectforeground=[("readonly", COLORS["text"])],
    )
    style.configure(
        "TSeparator",
        background=COLORS["border"],
    )
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
    style.configure(
        "Teal.Horizontal.TProgressbar",
        troughcolor=COLORS["surface_alt"],
        background=COLORS["accent"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent"],
        thickness=5,
    )
    return style


def style_listbox(listbox: tk.Listbox) -> None:
    """Apply a dark listbox appearance that matches the ttk theme."""
    listbox.configure(
        bg=COLORS["entry_bg"],
        fg=COLORS["text"],
        selectbackground=COLORS["selection"],
        selectforeground=COLORS["text"],
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        relief="flat",
        bd=0,
        activestyle="none",
    )


def make_chip(parent, text: str, bg: str, fg: str) -> tk.Label:
    """Create a styled status chip (raw tk.Label with fixed colors)."""
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("Segoe UI", 9, "bold"),
        padx=12,
        pady=5,
    )
