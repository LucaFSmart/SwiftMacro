# Mouse Lock Tool

A Windows desktop tray utility to save a mouse position and snap or lock the cursor to it.

## Setup

```bash
pip install keyboard pystray Pillow
```

## Run

```bash
python mouse_lock.py
```

The app starts minimized to the system tray (notification area, bottom-right).

## Usage

| Action | Hotkey | UI / Tray |
|---|---|---|
| Save current cursor position | CTRL+ALT+S | Save Position button |
| Move cursor to saved position | CTRL+ALT+M | Move Now button |
| Toggle cursor lock on/off | CTRL+ALT+T | Toggle Lock button |
| Emergency exit | CTRL+ALT+ESC | Tray → Exit |

**Cursor Lock:** When active, the cursor is continuously forced back to the saved position (~15ms interval). Toggle lock off to move freely again.

**System Tray:**
- Double-click tray icon → open window
- Right-click → Show UI / Lock / Exit
- Closing the window minimizes to tray (does not exit)

## Run Tests

```bash
pytest tests/ -v
```

## Requirements

- Windows 10 or 11
- Python 3.10+
- Run as standard user (no admin rights needed for most hotkey registrations)
