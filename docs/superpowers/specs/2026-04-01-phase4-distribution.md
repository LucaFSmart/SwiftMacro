# Phase 4 – Distribution & Auto-Update

**Date:** 2026-04-01
**Status:** Draft
**Scope:** Packaging SwiftMacro for end-user distribution — versioned EXE, Inno Setup installer, GitHub Release, and in-app update notifications.

---

## Goals

1. Produce a professional Windows installer (`SwiftMacro-Setup.exe`) backed by a standalone EXE (`SwiftMacro.exe`)
2. Publish versioned GitHub Releases with both artifacts and an auto-generated changelog
3. Notify users inside the app when a newer version is available, without blocking startup

---

## Non-Goals

- Code signing / Authenticode certificates (future phase)
- Auto-downloading or auto-installing updates (user clicks link, downloads manually)
- CI/CD pipeline (GitHub Actions) — local scripts only for now
- Portable ZIP distribution

---

## Version Source of Truth

`swiftmacro/constants.py` gains one new constant:

```python
APP_VERSION = "1.0.0"
```

All build scripts read this value via a Python one-liner:

```powershell
$version = python -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
```

No manual version maintenance across multiple files.

---

## Build Pipeline

### `scripts/build_exe.ps1` (modified)

Extends the existing PyInstaller script to embed version metadata in the EXE:

1. Reads `APP_VERSION` from `constants.py`
2. Generates a PyInstaller version-info file at `build/version_info.txt` (standard Windows `VERSIONINFO` format) with `APP_VERSION`, `APP_NAME = "SwiftMacro"`, and company/description fields
3. Passes `--version-file build/version_info.txt` to PyInstaller

Output: `dist\SwiftMacro.exe` with correct File Version and Product Name in Windows Properties.

### `scripts/build_installer.ps1` (new)

Builds the Inno Setup installer:

1. Reads `APP_VERSION` from `constants.py`
2. Locates `ISCC.exe` — tries `${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe` and `${env:ProgramFiles}\Inno Setup 6\ISCC.exe`; exits with error if not found
3. Asserts `dist\SwiftMacro.exe` exists (must run `build_exe.ps1` first)
4. Calls `ISCC.exe /DAppVersion=$version inno\SwiftMacro.iss`

Output: `dist\SwiftMacro-Setup.exe`

### `scripts/release.ps1` (new)

Orchestrates the full GitHub Release:

1. Reads `APP_VERSION`
2. Asserts both `dist\SwiftMacro.exe` and `dist\SwiftMacro-Setup.exe` exist
3. Determines previous tag via `git describe --tags --abbrev=0` (falls back to first commit if no tags exist)
4. Generates changelog: `git log --pretty="- %s" <prev-tag>..HEAD` filtered to lines starting with `feat:` or `fix:`, with those prefixes stripped
5. Calls `gh release create v$version --title "SwiftMacro v$version" --notes <changelog> dist\SwiftMacro.exe dist\SwiftMacro-Setup.exe`

Fails loudly if `gh` CLI is not authenticated.

---

## Inno Setup Script: `inno/SwiftMacro.iss`

Key configuration:

| Setting | Value |
|---------|-------|
| `AppName` | SwiftMacro |
| `AppVersion` | `{#AppVersion}` (passed via `/DAppVersion`) |
| `DefaultDirName` | `{autopf}\SwiftMacro` |
| `PrivilegesRequired` | `admin` (UAC elevation) |
| `OutputBaseFilename` | `SwiftMacro-Setup` |
| `Compression` | `lzma2/ultra64` |

**Shortcuts:**
- Start Menu entry: always created under `{group}\SwiftMacro`
- Desktop shortcut: optional, controlled by a `Tasks` entry (`desktopicon`) with a checkbox shown during install

**Uninstaller:** Inno Setup generates one automatically; it appears in Windows "Add or Remove Programs".

**Files section:** Installs `dist\SwiftMacro.exe` → `{app}\SwiftMacro.exe`.

---

## In-App Update Checker

### `swiftmacro/updater.py` (new)

Single public function:

```python
def check_for_update(repo: str, current_version: str) -> tuple[bool, str]:
    """
    Queries the GitHub Releases API for the latest release.
    Returns (update_available, release_html_url).
    Returns (False, "") on any network or parse error — never raises.
    Timeout: 5 seconds.
    """
```

- Calls `https://api.github.com/repos/{repo}/releases/latest`
- Parses `tag_name` (strips leading `v`) and compares with `current_version` using `packaging.version.Version` — falls back to string comparison if `packaging` is unavailable
- `repo` constant defined in `constants.py` as `GITHUB_REPO = "owner/SwiftMacro"` (to be filled in at release time)

### `swiftmacro/state.py` (modified)

Two new fields on `AppState`:

```python
update_available: bool = field(default=False)
update_url: str = field(default="")
```

New methods:
- `set_update_available(url: str)` — sets both fields atomically under the existing lock
- `get_update_available() -> tuple[bool, str]` — returns both fields

`make_state()` includes `update_available=False, update_url=""`.

### `swiftmacro/app.py` (modified)

After the main window is created and shown, starts a daemon thread:

```python
threading.Thread(target=_check_update_bg, args=(state,), daemon=True).start()
```

`_check_update_bg` calls `updater.check_for_update(GITHUB_REPO, APP_VERSION)` and writes the result to `state`.

### `swiftmacro/ui/main_window.py` (modified)

**New COLORS token** in `theme.py`: `chip_update_bg` (amber, e.g. `#B45309`), `chip_update_fg` (`#FFF7ED`).

**Update chip:** Created (not gridded) in the header row alongside the existing runner/tray chips. Label: `"↑ Update available"`. Clicking calls `webbrowser.open(state.get_update_available()[1])`.

**`_poll()` addition:** Shows the chip if `state.get_update_available()[0]` is `True`, hides it otherwise. This is the only UI change needed — the background thread writes to state, `_poll()` reads it.

---

## File Layout After Phase 4

```
swiftmacro/
  updater.py          # GitHub Releases API check — new
  constants.py        # + APP_VERSION, GITHUB_REPO
  state.py            # + update_available, update_url fields
  ui/
    main_window.py    # + update chip in header
    theme.py          # + chip_update_bg, chip_update_fg tokens
inno/
  SwiftMacro.iss      # Inno Setup script — new
scripts/
  build_exe.ps1       # + version-info embedding
  build_installer.ps1 # new
  release.ps1         # new
tests/
  test_updater.py     # new
  test_constants.py   # + APP_VERSION assertion
  test_state.py       # + update_available fields
```

---

## Tests

### `tests/test_updater.py` (new)

Uses `unittest.mock.patch` to mock `urllib.request.urlopen`:

| Test | Scenario | Expected |
|------|----------|----------|
| `test_update_available_when_newer_version` | API returns `v1.1.0`, current `1.0.0` | `(True, <release_url>)` |
| `test_no_update_when_same_version` | API returns `v1.0.0`, current `1.0.0` | `(False, "")` |
| `test_no_update_when_older_version` | API returns `v0.9.0`, current `1.0.0` | `(False, "")` |
| `test_no_update_on_network_error` | `urlopen` raises `URLError` | `(False, "")`, no exception raised |
| `test_no_update_on_malformed_json` | Response is not valid JSON | `(False, "")`, no exception raised |

### `tests/test_state.py` (extended)

- `test_update_available_initial` — `state.update_available == False`, `state.update_url == ""`
- `test_set_update_available` — after `set_update_available("https://...")`, `get_update_available()` returns `(True, "https://...")`

### `tests/test_constants.py` (extended)

- `test_app_version_defined` — `APP_VERSION` is a non-empty string matching `\d+\.\d+\.\d+`
- `test_github_repo_defined` — `GITHUB_REPO` is a non-empty string containing `"/"`

---

## Release Workflow (Manual Steps)

1. Bump `APP_VERSION` in `constants.py`
2. `.\scripts\build_exe.ps1`
3. `.\scripts\build_installer.ps1` (requires Inno Setup 6 installed)
4. `.\scripts\release.ps1`
5. Verify GitHub Release page has both artifacts and changelog

---

## Dependencies

No new runtime dependencies. `updater.py` uses only `urllib.request` (stdlib). Version comparison uses `packaging` if present (already a transitive dependency of pip), otherwise falls back to naive string split comparison.

Inno Setup 6 is a build-time tool only — not shipped, not in `requirements.txt`.
