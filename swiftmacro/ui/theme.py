"""Shared UI theme tokens, ttk styling and decorative helpers.

Aesthetic direction: **Editorial Cockpit** — refined dark control surface
that pairs editorial typography (Bahnschrift display + Cascadia Mono numerics)
with a single saturated mint accent, hairline borders, and a gradient strip
that anchors the hero. The goal is a UI that feels engineered, not generic.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# --- Typography --------------------------------------------------------------
# Bahnschrift ships with Windows 10/11 and has a distinctive condensed
# personality the default Segoe lacks. Cascadia Mono is preinstalled with
# modern Windows builds and reads sharper than Consolas for numeric data.
FONT_FAMILY = "Segoe UI"
HEADING_FONT = "Bahnschrift SemiBold"
DISPLAY_FONT = "Bahnschrift SemiCondensed"
MONO_FONT = "Cascadia Mono"

# --- Color tokens ------------------------------------------------------------
# A six-step elevation ramp on a near-black canvas. Surfaces stay cool;
# the lone bright accent (mint) is what your eye locks onto.
COLORS: dict[str, str] = {
    # Surfaces
    "bg":             "#06090f",
    "bg_deep":        "#04060b",
    "surface":        "#0d1626",
    "surface_alt":    "#111d35",
    "surface_soft":   "#1a2742",
    "surface_hover":  "#243456",
    "border":         "#1f2c49",
    "border_strong":  "#39507f",
    "border_accent":  "#2dd4bf",
    "divider":        "#16213a",

    # Text
    "text":     "#f4f8ff",
    "muted":    "#9bb0d1",
    "dim":      "#5f7196",
    "eyebrow":  "#7c95c0",

    # Primary accent — saturated mint
    "accent":        "#2dd4bf",
    "accent_active": "#5eead4",
    "accent_soft":   "#0a3a36",
    "accent_glow":   "#5eead4",

    # Secondary accent — violet
    "accent2":        "#b08bff",
    "accent2_active": "#9871ff",
    "accent2_soft":   "#241a3d",

    # Status colors
    "danger":        "#ff6b85",
    "danger_active": "#f04766",
    "warning":       "#f6c177",
    "success":       "#7ce0a7",
    "info":          "#7cc6ff",

    # Per-category cues
    "cat_mouse":    "#2dd4bf",
    "cat_keyboard": "#b08bff",
    "cat_timing":   "#f6c177",

    # Form / data surfaces
    "badge":     "#0a2a3a",
    "entry_bg":  "#080f1c",
    "selection": "#1d3b62",
    "row_alt":   "#0f192c",

    # Status chips
    "chip_idle_bg":    "#0f2236",
    "chip_idle_fg":    "#9fc8ff",
    "chip_running_bg": "#0e3d36",
    "chip_online_bg":  "#0f2a20",
    "chip_offline_bg": "#2a1a12",
    "chip_update_bg":  "#3d2600",
    "chip_update_fg":  "#f6c177",

    # Error frame
    "error_bg":     "#2a0e16",
    "error_border": "#6d2436",
    "error_text":   "#ffb2c1",

    # Button text
    "accent_text":  "#04141a",
    "accent2_text": "#120a22",
    "danger_text":  "#22060d",
}


# --- Font availability with graceful fallback --------------------------------
def _resolve_fonts(root: tk.Misc) -> None:
    """Swap font constants for safe fallbacks if the preferred face is missing.

    Bahnschrift and Cascadia Mono are bundled on Windows 10/11, but stripped
    Server installs and Wine can lack them. We probe once at startup so the
    rest of the module just references the resolved names.
    """
    global FONT_FAMILY, HEADING_FONT, DISPLAY_FONT, MONO_FONT
    available = set(tkfont.families(root))

    def pick(preferred: str, *fallbacks: str) -> str:
        if preferred in available:
            return preferred
        for option in fallbacks:
            if option in available:
                return option
        return preferred  # Tk will silently substitute its own fallback.

    FONT_FAMILY = pick("Segoe UI Variable Text", "Segoe UI", "Helvetica")
    HEADING_FONT = pick("Bahnschrift SemiBold", "Bahnschrift", "Segoe UI Semibold", "Segoe UI")
    DISPLAY_FONT = pick("Bahnschrift SemiCondensed", "Bahnschrift", "Segoe UI Semibold", "Segoe UI")
    MONO_FONT = pick("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New")


def configure_theme(root: tk.Misc) -> ttk.Style:
    """Apply the SwiftMacro ttk theme + global option defaults."""
    _resolve_fonts(root)

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
    style.configure("App.TFrame", background=COLORS["bg"])

    # --- Cards: hairline border, flat fill -------------------------------
    style.configure(
        "Card.TFrame",
        background=COLORS["surface"],
        borderwidth=1,
        relief="flat",
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
    )
    style.configure(
        "AltCard.TFrame",
        background=COLORS["surface_alt"],
        borderwidth=1,
        relief="flat",
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
    )

    # --- Labels ----------------------------------------------------------
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
    # Eyebrow — uppercase, letter-spaced "kicker" labels above section titles.
    # ttk doesn't expose tracking, so we lean on uppercase + a small font and
    # rely on the eyebrow color to do the visual lift.
    style.configure(
        "Eyebrow.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["eyebrow"],
        font=(FONT_FAMILY, 9, "bold"),
    )
    style.configure(
        "EyebrowDark.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["eyebrow"],
        font=(FONT_FAMILY, 9, "bold"),
    )
    style.configure(
        "EyebrowAlt.TLabel",
        background=COLORS["surface_alt"],
        foreground=COLORS["eyebrow"],
        font=(FONT_FAMILY, 9, "bold"),
    )
    style.configure(
        "HeroTitle.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=(DISPLAY_FONT, 32),
    )
    style.configure(
        "HeroBody.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
        font=(FONT_FAMILY, 11),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        font=(HEADING_FONT, 15),
    )
    style.configure(
        "SectionAltTitle.TLabel",
        background=COLORS["surface_alt"],
        foreground=COLORS["text"],
        font=(HEADING_FONT, 15),
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
        padding=(12, 5),
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

    # --- Buttons ---------------------------------------------------------
    style.configure(
        "TButton",
        padding=(16, 10),
        font=(FONT_FAMILY, 10),
        borderwidth=0,
        focusthickness=0,
    )
    style.map(
        "TButton",
        background=[("active", COLORS["surface_hover"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["accent"],
        foreground=COLORS["accent_text"],
        font=(FONT_FAMILY, 10, "bold"),
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
        background=[("active", COLORS["surface_hover"]), ("disabled", COLORS["surface_soft"])],
    )
    style.configure(
        "Accent2.TButton",
        background=COLORS["accent2"],
        foreground=COLORS["accent2_text"],
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Accent2.TButton",
        background=[("active", COLORS["accent2_active"]), ("disabled", COLORS["surface_soft"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground=COLORS["danger_text"],
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Danger.TButton",
        background=[("active", COLORS["danger_active"]), ("disabled", COLORS["surface_soft"])],
        foreground=[("disabled", COLORS["muted"])],
    )

    # --- Inputs ----------------------------------------------------------
    style.configure(
        "TEntry",
        fieldbackground=COLORS["entry_bg"],
        foreground=COLORS["text"],
        insertcolor=COLORS["accent"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(10, 7),
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", COLORS["accent"])],
        lightcolor=[("focus", COLORS["accent"])],
        darkcolor=[("focus", COLORS["accent"])],
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["entry_bg"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["accent"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["border"],
        darkcolor=COLORS["border"],
        padding=(10, 7),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["entry_bg"])],
        selectbackground=[("readonly", COLORS["entry_bg"])],
        selectforeground=[("readonly", COLORS["text"])],
        bordercolor=[("focus", COLORS["accent"])],
    )
    style.configure("TSeparator", background=COLORS["divider"])

    style.configure(
        "App.Vertical.TScrollbar",
        troughcolor=COLORS["bg"],
        background=COLORS["surface_soft"],
        arrowcolor=COLORS["muted"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["surface_soft"],
        darkcolor=COLORS["surface_soft"],
    )
    style.map(
        "App.Vertical.TScrollbar",
        background=[("active", COLORS["surface_hover"])],
    )
    style.configure(
        "Teal.Horizontal.TProgressbar",
        troughcolor=COLORS["surface_alt"],
        background=COLORS["accent"],
        bordercolor=COLORS["bg"],
        lightcolor=COLORS["accent_glow"],
        darkcolor=COLORS["accent"],
        thickness=6,
    )

    # --- Treeview --------------------------------------------------------
    style.configure(
        "App.Treeview",
        background=COLORS["entry_bg"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["entry_bg"],
        borderwidth=0,
        rowheight=42,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "App.Treeview.Heading",
        background=COLORS["surface_soft"],
        foreground=COLORS["eyebrow"],
        relief="flat",
        font=(FONT_FAMILY, 9, "bold"),
        padding=(12, 10),
    )
    style.map(
        "App.Treeview",
        background=[("selected", COLORS["selection"])],
        foreground=[("selected", COLORS["text"])],
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


def category_color(action: str) -> str:
    """Return the accent color for a given action's category."""
    from swiftmacro.constants import STEP_CATEGORIES
    cat = STEP_CATEGORIES.get(action)
    if cat == "mouse":
        return COLORS["cat_mouse"]
    if cat == "keyboard":
        return COLORS["cat_keyboard"]
    if cat == "timing":
        return COLORS["cat_timing"]
    return COLORS["accent"]


def make_chip(parent, text: str, bg: str, fg: str) -> tk.Label:
    """Create a styled status chip (raw tk.Label with fixed colors)."""
    return tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=(FONT_FAMILY, 9, "bold"),
        padx=14,
        pady=6,
    )


# --- Decorative helpers ------------------------------------------------------
def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def paint_gradient_strip(
    canvas: tk.Canvas,
    width: int,
    height: int,
    stops: list[str],
) -> None:
    """Paint a horizontal gradient on a Canvas using vertical 1px lines.

    ``stops`` is a list of hex color strings — the gradient interpolates
    linearly between consecutive stops. Used for the hero accent strip.
    """
    canvas.delete("gradient")
    if width <= 0 or height <= 0 or len(stops) < 2:
        return
    rgb_stops = [_hex_to_rgb(s) for s in stops]
    segments = len(rgb_stops) - 1
    for x in range(width):
        progress = (x / max(1, width - 1)) * segments
        idx = min(int(progress), segments - 1)
        local_t = progress - idx
        a, b = rgb_stops[idx], rgb_stops[idx + 1]
        color = _rgb_to_hex(
            (_lerp(a[0], b[0], local_t),
             _lerp(a[1], b[1], local_t),
             _lerp(a[2], b[2], local_t))
        )
        canvas.create_line(x, 0, x, height, fill=color, tags="gradient")


def draw_corner_brackets(
    canvas: tk.Canvas,
    width: int,
    height: int,
    color: str,
    length: int = 14,
    thickness: int = 2,
    inset: int = 4,
) -> None:
    """Draw four L-shaped corner brackets on a Canvas.

    A signature accent for the active card — small, sharp, deliberate. Reads
    like a crosshair viewfinder rather than a "rounded box".
    """
    canvas.delete("brackets")
    if width <= 2 * inset or height <= 2 * inset:
        return

    def _l(x1, y1, x2, y2):
        canvas.create_line(x1, y1, x2, y2, fill=color, width=thickness, tags="brackets")

    # Top-left
    _l(inset, inset, inset + length, inset)
    _l(inset, inset, inset, inset + length)
    # Top-right
    _l(width - inset - length, inset, width - inset, inset)
    _l(width - inset, inset, width - inset, inset + length)
    # Bottom-left
    _l(inset, height - inset, inset + length, height - inset)
    _l(inset, height - inset - length, inset, height - inset)
    # Bottom-right
    _l(width - inset - length, height - inset, width - inset, height - inset)
    _l(width - inset, height - inset - length, width - inset, height - inset)
