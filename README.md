# Mouse Lock Tool

A Windows desktop utility with a modern, profile-first control-center UI for running reusable mouse and keyboard automation chains.

## Setup

```bash
py -m pip install -r requirements.txt
```

## Run

```bash
py mouse_lock.py
# or
py -m mouse_lock
# or without console window on Windows
pyw mouse_lock.pyw
```

The app now starts as a normal desktop window with a generated app icon for the title bar, taskbar, and system tray. Closing the window still minimizes it to the tray when the tray icon is available.

## Build EXE

```powershell
py -m pip install pyinstaller
.\scripts\build_exe.ps1
```

The packaged Windows executable is written to `dist\MouseLock.exe`.

## Usage

| Action | Hotkey | UI / Tray |
|---|---|---|
| Run active profile | CTRL+ALT+R | Run button |
| Stop running chain | CTRL+ALT+X | Stop button |
| Emergency exit | CTRL+ALT+ESC | Tray -> Exit |

**Profiles:** Create profiles in the main window, assign optional hotkeys, and build action chains from `move`, `click`, `repeat_click`, `keypress`, `wait`, and `lock` steps.

**Lock Steps:** A `lock` step temporarily or permanently keeps the cursor pinned during a running profile chain. Manual global lock controls were intentionally removed so the app stays profile-centric.

**UI / UX:** The main window uses a larger desktop layout with status cards, grouped profile actions, a dedicated data panel, and a redesigned profile-builder dialog for faster editing.

**System Tray:**
- Double-click tray icon -> open window
- Right-click -> Show UI / Exit
- Closing the window minimizes to tray (does not exit)

## Run Tests

```bash
py -m pytest tests/ -q
```

## Requirements

- Windows 10 or 11
- Python 3.10+
- Run as standard user (no admin rights needed for most hotkey registrations)
