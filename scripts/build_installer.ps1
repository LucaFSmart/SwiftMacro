$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Read version from constants
$version = py -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
$githubRepo = py -c "from swiftmacro.constants import GITHUB_REPO; print(GITHUB_REPO)"
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
& $iscc "/DAppVersion=$version" "/DGitHubRepo=$githubRepo" "$issPath"

if ($LASTEXITCODE -ne 0) {
    Write-Error "ISCC.exe failed with exit code $LASTEXITCODE"
    exit 1
}

Write-Host "Installer built: dist\SwiftMacro-Setup.exe"
