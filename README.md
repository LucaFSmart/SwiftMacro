# SwiftMacro

[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow)]()

A Windows desktop utility for creating and running reusable mouse and keyboard automation chains. Build profiles with action steps, assign hotkeys, and execute them with a single keypress.

## Features

- **Profile-based automation** — Create up to 20 profiles, each with up to 100 action steps
- **9 action types** — `move`, `click`, `repeat_click`, `keypress`, `wait`, `lock`, `scroll`, `hold_key`, `random_delay`
- **Global hotkeys** — Trigger profiles from anywhere, with conflict detection
- **Profile repeat/loop** — Run a profile chain multiple times or indefinitely
- **Cursor lock** — Pin the cursor to a position temporarily or permanently
- **Dark theme UI** — Modern Tkinter interface with Treeview, status chips, and progress tracking
- **System tray** — Runs in the background; closing the window minimizes to tray
- **Auto-update checker** — Notifies when a new version is available on GitHub
- **Single instance guard** — Prevents duplicate app launches

## Installation

### Option A: Windows Installer (recommended)

Download the latest `SwiftMacro-Setup.exe` from the [Releases](https://github.com/swiftmacro-app/SwiftMacro/releases) page and run it. No Python required.

### Option B: Run from source

```bash
# Clone the repository
git clone https://github.com/swiftmacro-app/SwiftMacro.git
cd SwiftMacro

# Install dependencies
py -m pip install -r requirements.txt

# Run
py swiftmacro.py

# Or without console window
pyw swiftmacro.pyw

# Or as a module
py -m swiftmacro
```

**Requirements:** Windows 10/11, Python 3.10+, no admin rights needed.

## Usage

### Hotkeys

| Action | Hotkey |
|--------|--------|
| Run active profile | `Ctrl+Alt+R` |
| Stop running chain | `Ctrl+Alt+X` |
| Emergency exit | `Ctrl+Alt+Esc` |

Profiles can also have individual hotkeys assigned in the profile editor.

### Action Steps

| Step | Description |
|------|-------------|
| `move` | Move cursor to (x, y) |
| `click` | Single mouse click (left/right/middle) |
| `repeat_click` | Repeated clicks with interval |
| `keypress` | Press a key or key combination |
| `wait` | Pause for a duration |
| `lock` | Pin cursor to position (duration or permanent) |
| `scroll` | Scroll up/down by amount |
| `hold_key` | Hold a key for a duration |
| `random_delay` | Random pause between min/max |

### System Tray

- Double-click tray icon to open window
- Right-click for Show UI / Exit
- Closing the window minimizes to tray (does not exit)

### Data Storage

Profiles are saved to `~/.swiftmacro/profiles.json` and persist across sessions.

## Building

### Build EXE

```powershell
py -m pip install pyinstaller
.\scripts\build_exe.ps1
# Output: dist\SwiftMacro.exe
```

### Build Installer

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed.

```powershell
.\scripts\build_installer.ps1
# Output: dist\SwiftMacro-Setup.exe
```

### Create GitHub Release

```powershell
.\scripts\release.ps1
# Creates a GitHub Release with EXE + Installer + auto-generated changelog
```

Requires the [GitHub CLI](https://cli.github.com/) (`gh`) authenticated.

## Tests

```bash
py -m pytest tests/ -q
```

## License

[MIT](LICENSE)
