# Phase 4 – Distribution & Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship SwiftMacro as a versioned Windows installer with in-app update notifications and a one-command GitHub Release workflow.

**Architecture:** Version number lives solely in `constants.py`; all scripts read it via a Python one-liner. `updater.py` checks the GitHub Releases API on app startup in a daemon thread and writes the result to `AppState`; `main_window._poll()` surfaces a chip when an update is available. Three PowerShell scripts handle EXE build, installer build, and GitHub Release creation respectively.

**Tech Stack:** PyInstaller (EXE), Inno Setup 6 (installer), `packaging` library (semver comparison), `urllib.request` stdlib (HTTP), `gh` CLI (GitHub Release), PowerShell (scripts).

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `swiftmacro/constants.py` | Add `APP_VERSION`, `GITHUB_REPO` |
| Modify | `requirements.txt` | Add `packaging>=21.0` |
| Create | `swiftmacro/updater.py` | `check_for_update()` — GitHub Releases API |
| Modify | `swiftmacro/state.py` | Add `update_available`, `update_url` fields + methods |
| Modify | `swiftmacro/ui/theme.py` | Add `chip_update_bg`, `chip_update_fg` tokens |
| Modify | `swiftmacro/ui/main_window.py` | Add update chip to `chip_row`, `_poll()` guard |
| Modify | `swiftmacro/app.py` | Add `_check_update_bg` + daemon thread |
| Modify | `scripts/build_exe.ps1` | Add version-info file generation |
| Create | `inno/SwiftMacro.iss` | Inno Setup installer script |
| Create | `scripts/build_installer.ps1` | Calls `ISCC.exe` with version |
| Create | `scripts/release.ps1` | Generates changelog + `gh release create` |
| Modify | `tests/test_constants.py` | Assert `APP_VERSION`, `GITHUB_REPO` |
| Modify | `tests/test_state.py` | Assert update fields + methods |
| Modify | `tests/test_ui.py` | Assert update chip tokens + chip behavior |
| Create | `tests/test_updater.py` | Nine tests for `check_for_update()` |

---

### Task 1: Version constants and `packaging` dependency

**Files:**
- Modify: `swiftmacro/constants.py`
- Modify: `requirements.txt`
- Modify: `tests/test_constants.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_constants.py`:

```python
import re

def test_app_version_defined():
    from swiftmacro.constants import APP_VERSION
    assert APP_VERSION
    assert re.match(r"^\d+\.\d+\.\d+$", APP_VERSION), f"APP_VERSION must be semver, got: {APP_VERSION!r}"


def test_github_repo_defined():
    from swiftmacro.constants import GITHUB_REPO
    assert GITHUB_REPO
    assert "/" in GITHUB_REPO
    assert "owner" not in GITHUB_REPO, (
        "Replace the 'owner' placeholder in GITHUB_REPO with your actual GitHub username"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_constants.py::test_app_version_defined tests/test_constants.py::test_github_repo_defined -v
```

Expected: FAIL with `ImportError: cannot import name 'APP_VERSION'`

- [ ] **Step 3: Add constants to `swiftmacro/constants.py`**

Add after the `SYSTEM_HOTKEYS` block at the bottom of the file:

```python
# Version and update
APP_VERSION = "1.0.0"
GITHUB_REPO = "your-github-username/SwiftMacro"   # ← replace with real GitHub username
```

> **Important:** Replace `"your-github-username"` with your actual GitHub username. The test will fail if `"owner"` appears anywhere in this string.

- [ ] **Step 4: Add `packaging` to `requirements.txt`**

Add a new line at the end of `requirements.txt`:

```
packaging>=21.0
```

- [ ] **Step 5: Install the new dependency**

```
py -m pip install packaging>=21.0
```

- [ ] **Step 6: Run tests to verify they pass**

```
py -m pytest tests/test_constants.py::test_app_version_defined tests/test_constants.py::test_github_repo_defined -v
```

Expected: PASS (both tests green)

- [ ] **Step 7: Run the full test suite to check no regressions**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 8: Commit**

```
git add swiftmacro/constants.py requirements.txt tests/test_constants.py
git commit -m "feat: add APP_VERSION and GITHUB_REPO constants, add packaging dependency"
```

---

### Task 2: `updater.py` — GitHub Releases version check

**Files:**
- Create: `swiftmacro/updater.py`
- Create: `tests/test_updater.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_updater.py`:

```python
"""Tests for the GitHub Releases update checker."""
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError


def _make_urlopen_mock(tag_name="v1.1.0", html_url="https://github.com/releases/v1.1.0"):
    """Return a context-manager-compatible mock for urllib.request.urlopen."""
    payload = json.dumps({"tag_name": tag_name, "html_url": html_url}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_update_available_when_newer_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.1.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is True
    assert url == "https://github.com/releases/v1.1.0"


def test_no_update_when_same_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.0.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_when_older_version():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v0.9.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_network_error():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", side_effect=URLError("no network")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_malformed_json():
    from swiftmacro.updater import check_for_update
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not-json"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_missing_tag_name():
    from swiftmacro.updater import check_for_update
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"html_url": "https://example.com"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_no_update_on_http_404():
    from swiftmacro.updater import check_for_update
    with patch(
        "urllib.request.urlopen",
        side_effect=HTTPError("url", 404, "Not Found", {}, None),
    ):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is False
    assert url == ""


def test_tag_without_v_prefix():
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("1.1.0")):
        available, url = check_for_update("owner/repo", "1.0.0")
    assert available is True


def test_no_update_two_digit_minor():
    """Integer comparison: 1.10.0 > 1.9.0 must be True (not False via string sort)."""
    from swiftmacro.updater import check_for_update
    with patch("urllib.request.urlopen", return_value=_make_urlopen_mock("v1.10.0")):
        available, url = check_for_update("owner/repo", "1.9.0")
    assert available is True, "1.10.0 must be newer than 1.9.0"
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_updater.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'swiftmacro.updater'`

- [ ] **Step 3: Implement `swiftmacro/updater.py`**

Create `swiftmacro/updater.py`:

```python
"""GitHub Releases update checker."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import URLError

from packaging.version import Version


def check_for_update(repo: str, current_version: str) -> tuple[bool, str]:
    """
    Check GitHub Releases API for a newer version.

    Returns (update_available, release_html_url).
    Returns (False, "") on any network, HTTP, or parse error — never raises.

    Args:
        repo: GitHub repository in "owner/name" form (e.g. "alice/SwiftMacro")
        current_version: Semver string of the running app (e.g. "1.0.0")
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "SwiftMacro-updater"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        tag = data["tag_name"].lstrip("v")
        html_url = data.get("html_url", "")
        if Version(tag) > Version(current_version):
            return True, html_url
        return False, ""
    except Exception:
        return False, ""
```

- [ ] **Step 4: Run tests to verify they pass**

```
py -m pytest tests/test_updater.py -v
```

Expected: all 9 tests PASS

- [ ] **Step 5: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```
git add swiftmacro/updater.py tests/test_updater.py
git commit -m "feat: add updater module with GitHub Releases version check"
```

---

### Task 3: `state.py` — update availability fields

**Files:**
- Modify: `swiftmacro/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_state.py`:

```python
def test_update_available_initial():
    s = make_state()
    assert s.update_available is False
    assert s.update_url == ""


def test_set_update_available():
    s = make_state()
    s.set_update_available("https://github.com/releases/v1.1.0")
    available, url = s.get_update_available()
    assert available is True
    assert url == "https://github.com/releases/v1.1.0"
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_state.py::test_update_available_initial tests/test_state.py::test_set_update_available -v
```

Expected: FAIL with `AttributeError: 'AppState' object has no attribute 'update_available'`

- [ ] **Step 3: Add fields and methods to `swiftmacro/state.py`**

Add two new fields after the `chain_progress` line in the `AppState` dataclass (the fields with defaults must stay after non-default fields; `chain_progress` is currently the last field):

```python
    chain_progress: tuple[int, int] = field(default=(0, 0))  # (current_step, total_steps)
    update_available: bool = field(default=False)
    update_url: str = field(default="")
```

Add two new methods after `get_chain_progress()` at the end of the `AppState` class:

```python
    # --- update availability ---
    def set_update_available(self, url: str) -> None:
        with self._lock:
            self.update_available = True
            self.update_url = url

    def get_update_available(self) -> tuple[bool, str]:
        with self._lock:
            return self.update_available, self.update_url
```

Update `make_state()` to pass the new fields explicitly (add to the `AppState(...)` call, after `chain_progress=(0, 0)`):

```python
    return AppState(
        stop_event=threading.Event(),
        hotkey_errors=[],
        status_message="",
        active_profile_id=None,
        runner_busy=False,
        chain_lock_active=False,
        chain_lock_pos=None,
        chain_progress=(0, 0),
        update_available=False,
        update_url="",
        _lock=threading.Lock(),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```
py -m pytest tests/test_state.py::test_update_available_initial tests/test_state.py::test_set_update_available -v
```

Expected: PASS

- [ ] **Step 5: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```
git add swiftmacro/state.py tests/test_state.py
git commit -m "feat: add update_available and update_url fields to AppState"
```

---

### Task 4: Update chip — `theme.py` tokens + `main_window.py` chip

**Files:**
- Modify: `swiftmacro/ui/theme.py`
- Modify: `swiftmacro/ui/main_window.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ui.py`:

```python
def test_update_chip_color_tokens_present():
    from swiftmacro.ui.theme import COLORS
    assert "chip_update_bg" in COLORS
    assert "chip_update_fg" in COLORS
    assert COLORS["chip_update_bg"]  # non-empty
    assert COLORS["chip_update_fg"]  # non-empty


def test_update_chip_hidden_when_no_update(monkeypatch):
    """Update chip must not be visible when update_available is False."""
    import tkinter as tk
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    root = tk.Tk()
    root.withdraw()
    try:
        state = make_state()
        # update_available starts False
        win = MainWindow(root, state, tray_available=False)
        root.update_idletasks()
        # chip should not be pack-managed (pack_info raises TclError when not packed)
        import pytest
        with pytest.raises(tk.TclError):
            win._update_chip.pack_info()
    finally:
        root.destroy()


def test_update_chip_shown_when_update_available(monkeypatch):
    """Update chip must become visible after set_update_available is called."""
    import tkinter as tk
    from swiftmacro.state import make_state
    from swiftmacro.ui.main_window import MainWindow

    root = tk.Tk()
    root.withdraw()
    try:
        state = make_state()
        win = MainWindow(root, state, tray_available=False)
        state.set_update_available("https://github.com/releases/v1.1.0")
        # trigger _poll manually
        win._poll()
        root.update_idletasks()
        info = win._update_chip.pack_info()
        assert info  # truthy dict means chip is pack-managed (visible)
    finally:
        root.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_ui.py::test_update_chip_color_tokens_present tests/test_ui.py::test_update_chip_hidden_when_no_update tests/test_ui.py::test_update_chip_shown_when_update_available -v
```

Expected: FAIL — `AssertionError` for missing color keys, `AttributeError` for missing `_update_chip`

- [ ] **Step 3: Add color tokens to `swiftmacro/ui/theme.py`**

In the `COLORS` dict, add after `"chip_offline_bg"`:

```python
    "chip_offline_bg": "#35221a",
    "chip_update_bg":  "#3d2600",   # dark amber — update available
    "chip_update_fg":  "#f6c177",   # warm foreground (same as "warning")
```

- [ ] **Step 4: Add update chip to `swiftmacro/ui/main_window.py`**

**4a — Add imports** at the top of `main_window.py` (two new stdlib imports):

```python
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
```

**4b — Create the chip** in `_build_hero()`, immediately after the `self._tray_chip.pack(...)` call:

```python
        self._tray_chip.pack(side="left", padx=(10, 0))
        self._update_chip = make_chip(
            chip_row,
            text="↑ Update available",
            bg=COLORS["chip_update_bg"],
            fg=COLORS["chip_update_fg"],
        )
        self._update_chip.bind(
            "<Button-1>",
            lambda _: webbrowser.open(self._state.get_update_available()[1]),
        )
        # Note: _update_chip is intentionally NOT packed here — _poll() controls visibility
```

**4c — Add guard to `_poll()`** alongside the existing chip update block. Find the section in `_poll()` that updates `_runner_chip` config and add the following block right after it:

```python
        available, _ = self._state.get_update_available()
        if available:
            self._update_chip.pack(side="left", padx=(10, 0))
        else:
            self._update_chip.pack_forget()
```

- [ ] **Step 5: Run tests to verify they pass**

```
py -m pytest tests/test_ui.py::test_update_chip_color_tokens_present tests/test_ui.py::test_update_chip_hidden_when_no_update tests/test_ui.py::test_update_chip_shown_when_update_available -v
```

Expected: all 3 PASS

- [ ] **Step 6: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```
git add swiftmacro/ui/theme.py swiftmacro/ui/main_window.py tests/test_ui.py
git commit -m "feat: add update-available chip to main window header"
```

---

### Task 5: `app.py` — background update check thread

**Files:**
- Modify: `swiftmacro/app.py`

> There are no isolated unit tests for this wiring task — the updater itself is fully tested in Task 2, and AppState in Task 3. Manual smoke-test instructions are provided below.

- [ ] **Step 1: Add module-level imports to `swiftmacro/app.py`**

At the top of `app.py`, the existing imports are all `from swiftmacro...` style. Add two new module-level imports after the existing block:

```python
import threading

from swiftmacro.action_runner import ActionRunner
# ... existing imports ...
from swiftmacro.ui.main_window import MainWindow
```

So the final imports section looks like:

```python
"""Application startup and shutdown wiring."""
from __future__ import annotations

import threading

from swiftmacro.action_runner import ActionRunner
from swiftmacro.constants import APP_ID, APP_MUTEX_NAME
from swiftmacro.dpi import init_dpi_awareness
from swiftmacro.hotkeys import HotkeyManager, _shutdown_ref
from swiftmacro.icon import apply_window_icon, set_windows_app_id
from swiftmacro.lock_loop import LockLoop
from swiftmacro.profile_store import ProfileStore
from swiftmacro.single_instance import SingleInstanceGuard, acquire_single_instance
from swiftmacro.state import AppState, make_state
from swiftmacro.tray import TrayManager
from swiftmacro.ui.main_window import MainWindow
```

- [ ] **Step 2: Add `_check_update_bg` as a module-level function**

Add after `make_shutdown()` and before `main()` (i.e., between the two functions):

```python
def _check_update_bg(state: AppState) -> None:
    """Background thread: check GitHub for a newer release and update AppState."""
    from swiftmacro import updater
    from swiftmacro.constants import APP_VERSION, GITHUB_REPO
    available, url = updater.check_for_update(GITHUB_REPO, APP_VERSION)
    if available:
        state.set_update_available(url)
```

- [ ] **Step 3: Start the thread in `main()`**

In `main()`, find the line where `MainWindow(...)` is called and add the thread start immediately after it:

```python
    MainWindow(
        root,
        state,
        tray_available,
        profile_store=profile_store,
        hotkey_mgr=hotkey_mgr,
        action_runner=action_runner,
    )

    threading.Thread(target=_check_update_bg, args=(state,), daemon=True).start()
```

- [ ] **Step 4: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass (no new tests for this task — integration tested by running the app)

- [ ] **Step 5: Commit**

```
git add swiftmacro/app.py
git commit -m "feat: start background update check thread on app startup"
```

---

### Task 6: `build_exe.ps1` — embed version metadata in EXE

**Files:**
- Modify: `scripts/build_exe.ps1`

> This task modifies a build script — no Python unit tests. Verification is checking the built EXE's Windows Properties.

- [ ] **Step 1: Update `scripts/build_exe.ps1`**

Replace the entire content of `scripts/build_exe.ps1` with:

```powershell
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$iconPath = Join-Path $repoRoot "build\swiftmacro.ico"
$versionInfoPath = Join-Path $repoRoot "build\version_info.txt"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $iconPath) | Out-Null

# Export icon
@'
from pathlib import Path
from swiftmacro.icon import ensure_windows_icon_file

source = Path(ensure_windows_icon_file())
target = Path("build/swiftmacro.ico")
target.write_bytes(source.read_bytes())
print(target)
'@ | py -

# Read version from constants and generate Windows VERSIONINFO file
$version = python -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
Write-Host "Building SwiftMacro v$version"

$parts = $version -split '\.'
$major = [int]$parts[0]
$minor = [int]$parts[1]
$patch = [int]$parts[2]

$versionInfoContent = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($major, $minor, $patch, 0),
    prodvers=($major, $minor, $patch, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1,
    subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', ''),
      StringStruct('FileDescription', 'SwiftMacro'),
      StringStruct('FileVersion', '$version'),
      StringStruct('ProductName', 'SwiftMacro'),
      StringStruct('ProductVersion', '$version'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@

Set-Content -Path $versionInfoPath -Value $versionInfoContent -Encoding UTF8

py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --noconsole `
    --name SwiftMacro `
    --specpath build `
    --icon "$iconPath" `
    --version-file "$versionInfoPath" `
    --collect-submodules pystray `
    --collect-submodules PIL `
    --collect-submodules packaging `
    --hidden-import PIL._tkinter_finder `
    swiftmacro.pyw

Write-Host "Build complete: dist\SwiftMacro.exe"
```

- [ ] **Step 2: Run the full test suite to verify nothing broke**

```
py -m pytest tests/ -q
```

Expected: all tests pass (build_exe.ps1 is not executed during tests)

- [ ] **Step 3: Commit**

```
git add scripts/build_exe.ps1
git commit -m "feat: embed APP_VERSION in EXE Windows metadata via PyInstaller version-info"
```

---

### Task 7: `inno/SwiftMacro.iss` — Inno Setup installer script

**Files:**
- Create: `inno/SwiftMacro.iss`

> No Python unit tests. Verification is running the installer script manually (requires Inno Setup 6).

- [ ] **Step 1: Create the `inno/` directory and `SwiftMacro.iss`**

```
mkdir inno
```

Create `inno/SwiftMacro.iss`:

```iss
; SwiftMacro Inno Setup Script
; AppVersion is passed from build_installer.ps1 via /DAppVersion=x.y.z

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=SwiftMacro
AppVersion={#AppVersion}
AppPublisher=SwiftMacro
AppPublisherURL=https://github.com/{#GitHubRepo}
DefaultDirName={autopf}\SwiftMacro
DefaultGroupName=SwiftMacro
OutputDir=..\dist
OutputBaseFilename=SwiftMacro-Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
SetupIconFile=..\build\swiftmacro.ico
UninstallDisplayIcon={app}\SwiftMacro.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\SwiftMacro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SwiftMacro"; Filename: "{app}\SwiftMacro.exe"
Name: "{group}\Uninstall SwiftMacro"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SwiftMacro"; Filename: "{app}\SwiftMacro.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SwiftMacro.exe"; Description: "Launch SwiftMacro"; Flags: nowait postinstall skipifsilent
```

> **Note on `{#GitHubRepo}`:** The Inno Setup script references `GitHubRepo` for the publisher URL. Pass it alongside `AppVersion` in `build_installer.ps1` (Task 8). If you haven't set a real GitHub URL yet, the URL will default gracefully.

- [ ] **Step 2: Commit**

```
git add inno/SwiftMacro.iss
git commit -m "feat: add Inno Setup installer script for SwiftMacro"
```

---

### Task 8: `scripts/build_installer.ps1`

**Files:**
- Create: `scripts/build_installer.ps1`

- [ ] **Step 1: Create `scripts/build_installer.ps1`**

```powershell
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Read version from constants
$version = python -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
$githubRepo = python -c "from swiftmacro.constants import GITHUB_REPO; print(GITHUB_REPO)"
Write-Host "Building installer for SwiftMacro v$version"

# Assert EXE exists
$exePath = Join-Path $repoRoot "dist\SwiftMacro.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "dist\SwiftMacro.exe not found. Run scripts\build_exe.ps1 first."
    exit 1
}

# Assert icon exists (needed by .iss)
$iconPath = Join-Path $repoRoot "build\swiftmacro.ico"
if (-not (Test-Path $iconPath)) {
    Write-Error "build\swiftmacro.ico not found. Run scripts\build_exe.ps1 first."
    exit 1
}

# Locate Inno Setup 6 compiler
$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Error "ISCC.exe not found. Install Inno Setup 6 from https://jrsoftware.org/isdl.php"
    exit 1
}

# Build installer
$issPath = Join-Path $repoRoot "inno\SwiftMacro.iss"
& $iscc /DAppVersion=$version /DGitHubRepo=$githubRepo $issPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "ISCC.exe failed with exit code $LASTEXITCODE"
    exit 1
}

Write-Host "Installer built: dist\SwiftMacro-Setup.exe"
```

- [ ] **Step 2: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 3: Commit**

```
git add scripts/build_installer.ps1
git commit -m "feat: add build_installer.ps1 to produce SwiftMacro-Setup.exe via Inno Setup"
```

---

### Task 9: `scripts/release.ps1` — GitHub Release orchestration

**Files:**
- Create: `scripts/release.ps1`

- [ ] **Step 1: Create `scripts/release.ps1`**

```powershell
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Read version and repo from constants
$version = python -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
$githubRepo = python -c "from swiftmacro.constants import GITHUB_REPO; print(GITHUB_REPO)"

# Guard against unfilled placeholder
if ($githubRepo -match "owner") {
    Write-Error "GITHUB_REPO still contains the 'owner' placeholder. Set your real GitHub username in swiftmacro/constants.py first."
    exit 1
}

Write-Host "Releasing SwiftMacro v$version to $githubRepo"

# Assert both artifacts exist
$exePath = Join-Path $repoRoot "dist\SwiftMacro.exe"
$installerPath = Join-Path $repoRoot "dist\SwiftMacro-Setup.exe"
if (-not (Test-Path $exePath))      { Write-Error "dist\SwiftMacro.exe missing. Run build_exe.ps1.";       exit 1 }
if (-not (Test-Path $installerPath)) { Write-Error "dist\SwiftMacro-Setup.exe missing. Run build_installer.ps1."; exit 1 }

# Determine previous tag or first commit SHA
$prevTag = git describe --tags --abbrev=0 2>$null
if ($LASTEXITCODE -ne 0 -or -not $prevTag) {
    $prevTag = git rev-list --max-parents=0 HEAD
    Write-Host "No previous tag found, using first commit: $prevTag"
}

# Generate changelog from feat:/fix: commits
$rawLog = git log --pretty="- %s" "${prevTag}..HEAD"
$changelog = ($rawLog -split "`n" | Where-Object {
    $_ -match "^- feat:" -or $_ -match "^- fix:"
} | ForEach-Object {
    $_ -replace "^- feat: ?", "- " -replace "^- fix: ?", "- "
}) -join "`n"

if (-not $changelog.Trim()) {
    $changelog = "No feat: or fix: commits since previous release."
}

Write-Host "Changelog:"
Write-Host $changelog

# Create GitHub Release
gh release create "v$version" `
    --title "SwiftMacro v$version" `
    --notes $changelog `
    $exePath `
    $installerPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "gh release create failed. Make sure you are authenticated: gh auth login"
    exit 1
}

Write-Host "Release v$version published to https://github.com/$githubRepo/releases/tag/v$version"
```

- [ ] **Step 2: Run the full test suite**

```
py -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 3: Commit**

```
git add scripts/release.ps1
git commit -m "feat: add release.ps1 — changelog generation and GitHub Release creation"
```

---

## Final Verification

- [ ] **Run complete test suite one last time**

```
py -m pytest tests/ -q
```

Expected: all tests pass, zero failures

- [ ] **Verify no bare hex strings were introduced**

```
python -c "
import re, sys
files = ['swiftmacro/ui/main_window.py', 'swiftmacro/ui/step_builder.py']
for f in files:
    text = open(f).read()
    hits = re.findall(r'\"#[0-9a-fA-F]{3,8}\"', text)
    if hits:
        print(f'FAIL {f}: bare hex {hits}')
        sys.exit(1)
print('OK: no bare hex strings in UI files')
"
```

Expected: `OK: no bare hex strings in UI files`

- [ ] **Commit final check**

```
git log --oneline -10
```

Confirm all Phase 4 commits are present on master.
