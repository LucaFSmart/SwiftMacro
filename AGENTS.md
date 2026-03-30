# Repository Guidelines

## Project Structure & Module Organization
`swiftmacro.py` is the current Windows tray app entry point. Core logic is being split into the [`swiftmacro/`](D:\Projekte\Coding\Auto\swiftmacro) package, which holds focused modules such as `cursor.py`, `hotkeys.py`, `lock_loop.py`, and `profile_store.py`. Tests live in [`tests/`](D:\Projekte\Coding\Auto\tests) and generally mirror package modules with `test_<module>.py` names. Design notes and implementation plans are kept in [`docs/superpowers/`](D:\Projekte\Coding\Auto\docs\superpowers). The tray icon is generated in code; there is no separate assets directory.

## Build, Test, and Development Commands
Install dependencies with `py -m pip install -r requirements.txt`. Run the desktop app with `py swiftmacro.py`. Run the full test suite with `py -m pytest tests/ -q`; use `py -m pytest tests/test_hotkeys.py -v` when iterating on one module. There is no separate build step in this repository.

## Coding Style & Naming Conventions
Target Python 3.10+ and keep 4-space indentation. Follow existing patterns: `snake_case` for modules, functions, and variables; `PascalCase` for classes; `UPPER_CASE` for shared constants in `constants.py`. Prefer small, typed functions and dataclasses where state needs structure. Keep Windows-specific side effects isolated in focused modules so tests can mock them cleanly.

## Testing Guidelines
Tests use `pytest` with `unittest.mock` and local fixtures from `conftest.py`. Add or update tests with every behavior change, especially around hotkeys, cursor movement, profile persistence, and lock-loop timing. Name tests `test_<behavior>` and mock OS-facing calls (`keyboard`, `ctypes`, file writes) instead of relying on real desktop state.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit style, for example `feat: HotkeyManager with profile hotkeys and conflict detection`. Keep commit subjects short, imperative, and scoped. PRs should explain the user-visible change, list the verification command you ran, and include screenshots when UI or tray behavior changes. Keep generated files such as `__pycache__/` and local profile data from `~/.swiftmacro/` out of commits.

## Configuration Notes
This project is Windows-specific and depends on global hotkeys and Win32 cursor behavior. When changing persisted profile data, preserve backward compatibility for `profiles.json` and keep writes atomic.
