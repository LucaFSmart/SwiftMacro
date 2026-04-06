"""Profile editor package — re-exports the public dialog API.

The dialog used to live in a single 500-line module. It is now split into
``forms`` (pure data) and ``dialog`` (Tkinter glue). External callers and
tests still import from ``swiftmacro.ui.step_builder`` directly, so all the
public names — and the underscore-prefixed ones the test suite reaches into
— are re-exported here.
"""
from swiftmacro.ui.step_builder.dialog import StepBuilderDialog
from swiftmacro.ui.step_builder.forms import (
    _ACTION_HINTS,
    _COMBO_VALUES,
    _INT_PARAMS,
    _NEEDS_POSITION,
    _PARAM_FIELDS,
    COMMON_KEYS,
    format_step_label,
)

__all__ = [
    "StepBuilderDialog",
    "format_step_label",
    "COMMON_KEYS",
    "_PARAM_FIELDS",
    "_NEEDS_POSITION",
    "_INT_PARAMS",
    "_COMBO_VALUES",
    "_ACTION_HINTS",
]
