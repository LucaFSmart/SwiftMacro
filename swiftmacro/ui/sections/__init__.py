"""UI section sub-modules. Each module owns one self-contained panel.

Sections are deliberately small classes with two responsibilities:
1. ``build()`` — construct widgets inside a parent frame.
2. ``update(...)`` — refresh widget contents from application state.

The main window orchestrates them and routes its periodic ``_poll()`` ticks
into the right ``update()`` calls.
"""
from swiftmacro.ui.sections.hero import HeroSection
from swiftmacro.ui.sections.profiles_panel import ProfilesPanel
from swiftmacro.ui.sections.sidebar import Sidebar

__all__ = ["HeroSection", "ProfilesPanel", "Sidebar"]
