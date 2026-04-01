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

`swiftmacro/constants.py` gains two new constants:

```python
APP_VERSION = "1.0.0"
GITHUB_REPO = "owner/SwiftMacro"   # replace "owner" with actual GitHub username before first release
```

> **Note on `GITHUB_REPO`:** The placeholder `"owner/SwiftMacro"` must be replaced with the real repository path before publishing the first release. `test_constants.py` asserts that `"owner"` is not present in `GITHUB_REPO` to prevent accidentally shipping with the placeholder. `release.ps1` also checks this and exits with an error if the placeholder is still present.

All build scripts read `APP_VERSION` via a Python one-liner:

```powershell
$version = python -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
```

No manual version maintenance across multiple files.

---

## Build Pipeline

### `scripts/build_exe.ps1` (modified)

Extends the existing PyInstaller script to embed version metadata in the EXE:

1. Reads `APP_VERSION` from `constants.py`
2. Splits the version into `(major, minor, patch, 0)` integers and generates a PyInstaller version-info file at `build/version_info.txt` using the following structure:

```python
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),   # filled from APP_VERSION tuple
    prodvers=(1, 0, 0, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1,
    subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([StringTable("040904B0", [
      StringStruct("CompanyName", ""),
      StringStruct("FileDescription", "SwiftMacro"),
      StringStruct("FileVersion", APP_VERSION),
      StringStruct("ProductName", "SwiftMacro"),
      StringStruct("ProductVersion", APP_VERSION),
    ])]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])])
  ]
)
```

3. Passes `--version-file build/version_info.txt` to PyInstaller

Output: `dist\SwiftMacro.exe` with correct File Version and Product Name in Windows Properties.

### `scripts/build_installer.ps1` (new)

Builds the Inno Setup installer:

1. Reads `APP_VERSION` from `constants.py`
2. Locates `ISCC.exe` — tries `${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe` and `${env:ProgramFiles}\Inno Setup 6\ISCC.exe`; exits with a clear error message if not found
3. Asserts `dist\SwiftMacro.exe` exists (must run `build_exe.ps1` first)
4. Calls `ISCC.exe /DAppVersion=$version inno\SwiftMacro.iss`

Output: `dist\SwiftMacro-Setup.exe`

### `scripts/release.ps1` (new)

Orchestrates the full GitHub Release:

1. Reads `APP_VERSION` and `GITHUB_REPO`; exits with error if `GITHUB_REPO` still contains the placeholder `"owner"`
2. Asserts both `dist\SwiftMacro.exe` and `dist\SwiftMacro-Setup.exe` exist
3. Determines previous tag via `git describe --tags --abbrev=0`; if that fails (no tags yet), falls back to the first commit SHA via `git rev-list --max-parents=0 HEAD`
4. Generates changelog: `git log --pretty="- %s" <prev-tag-or-sha>..HEAD` filtered to lines starting with `feat:` or `fix:`, with those prefixes stripped
5. If the filtered changelog is empty (e.g., only `chore:` commits), substitutes the note `"No feat: or fix: commits since previous release."` Example transformation: raw log line `- feat: add auto-update` → filtered output `- add auto-update` (the `- ` bullet is preserved, only the `feat: ` prefix is stripped)
6. Calls `gh release create v$version --title "SwiftMacro v$version" --notes <changelog> dist\SwiftMacro.exe dist\SwiftMacro-Setup.exe`

Fails loudly if `gh` CLI is not authenticated.

---

## Inno Setup Script: `inno/SwiftMacro.iss`

Key configuration:

| Setting | Value |
|---------|-------|
| `AppName` | SwiftMacro |
| `AppVersion` | `{#AppVersion}` (passed via `/DAppVersion`) |
| `DefaultDirName` | `{autopf}\SwiftMacro` |
| `PrivilegesRequired` | `admin` (UAC elevation required for `{autopf}` install path — the app itself runs without admin rights after installation) |
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
- Parses `tag_name` (strips leading `v` if present — handles both `"v1.1.0"` and `"1.1.0"` forms)
- Compares versions using `packaging.version.Version` (see Dependencies section)
- Returns `(False, "")` on: network error, timeout, HTTP non-200, malformed JSON, missing `tag_name` key, or any other exception

### `swiftmacro/state.py` (modified)

Two new fields on `AppState`, declared **after** the existing `chain_progress` field (all `field(default=...)` declarations must follow non-default fields in the dataclass):

```python
update_available: bool = field(default=False)
update_url: str = field(default="")
```

New methods:
- `set_update_available(url: str)` — sets both fields atomically under the existing lock
- `get_update_available() -> tuple[bool, str]` — returns both fields

`make_state()` passes these explicitly for consistency with the existing `chain_progress=(0, 0)` pattern — add them to the `AppState(...)` call inside `make_state()`:
```python
# inside make_state(), in the AppState(...) constructor call:
return AppState(
    ...,
    update_available=False,
    update_url="",
)
```

### `swiftmacro/app.py` (modified)

`_check_update_bg` is a **module-level** private function (consistent with `make_shutdown`). Add `import threading` to `app.py`'s module-level imports:

```python
def _check_update_bg(state: AppState) -> None:
    available, url = updater.check_for_update(GITHUB_REPO, APP_VERSION)
    if available:
        state.set_update_available(url)
```

After the main window is created and shown, `main()` starts the thread:

```python
threading.Thread(target=_check_update_bg, args=(state,), daemon=True).start()
```

### `swiftmacro/ui/main_window.py` (modified)

Add `import webbrowser` to `main_window.py`'s module-level imports.

**New COLORS tokens** in `theme.py` — following the existing dark-chip convention:

```python
"chip_update_bg": "#3d2600",   # dark amber background
"chip_update_fg": "#f6c177",   # warm foreground (matches existing warning color)
```

**Update chip:** Created via `make_chip(chip_row, "↑ Update available", COLORS["chip_update_bg"], COLORS["chip_update_fg"])`. Initially hidden. Stored as `self._update_chip`.

**Placement:** Packed into `chip_row` with `side="left"` and `padx=(10, 0)`, immediately after `_tray_chip`. Use `.pack_forget()` to hide and `.pack(side="left", padx=(10, 0))` to show (consistent with the pack geometry used by the existing chips).

**Binding:** `self._update_chip.bind("<Button-1>", lambda _: webbrowser.open(self._state.get_update_available()[1]))`

**`_poll()` addition** (single guard, placed with the other chip updates):

```python
available, _ = self._state.get_update_available()
if available:
    self._update_chip.pack(side="left", padx=(10, 0))
else:
    self._update_chip.pack_forget()
```

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
  test_constants.py   # + APP_VERSION, GITHUB_REPO assertions
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
| `test_no_update_on_malformed_json` | Response body is not valid JSON | `(False, "")`, no exception raised |
| `test_no_update_on_missing_tag_name` | Valid JSON but no `tag_name` key | `(False, "")`, no exception raised |
| `test_no_update_on_http_404` | `urlopen` raises `HTTPError(404)` | `(False, "")`, no exception raised |
| `test_tag_without_v_prefix` | API returns `1.1.0` (no leading `v`), current `1.0.0` | `(True, <release_url>)` |
| `test_no_update_two_digit_minor` | API returns `v1.10.0`, current `1.9.0` | `(True, <release_url>)` — verifies integer comparison, not string |

### `tests/test_state.py` (extended)

- `test_update_available_initial` — `state.update_available == False`, `state.update_url == ""`
- `test_set_update_available` — after `set_update_available("https://...")`, `get_update_available()` returns `(True, "https://...")`

### `tests/test_constants.py` (extended)

- `test_app_version_defined` — `APP_VERSION` is a non-empty string matching `\d+\.\d+\.\d+`
- `test_github_repo_defined` — `GITHUB_REPO` is a non-empty string containing `"/"` and **not** containing `"owner"` (placeholder sentinel check)

---

## Release Workflow (Manual Steps)

1. Set real GitHub username in `GITHUB_REPO` in `constants.py` (one-time)
2. Bump `APP_VERSION` in `constants.py`
3. `.\scripts\build_exe.ps1`
4. `.\scripts\build_installer.ps1` (requires Inno Setup 6 installed)
5. `.\scripts\release.ps1`
6. Verify GitHub Release page has both artifacts and changelog

---

## Dependencies

**New runtime dependency:** `packaging>=21.0` added to `requirements.txt`. `updater.py` uses `packaging.version.Version` for correct semantic version comparison (avoids lexicographic bugs with two-digit components like `1.10.0` vs `1.9.0`). `packaging` must also be collected by PyInstaller (`--collect-submodules packaging` in `build_exe.ps1`).

`updater.py` uses `urllib.request` from stdlib for HTTP — no additional HTTP library needed.

Inno Setup 6 is a build-time tool only — not shipped, not in `requirements.txt`.
