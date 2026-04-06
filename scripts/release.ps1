$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Read version and repo from constants
$version = py -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
if ($LASTEXITCODE -ne 0 -or -not $version) { Write-Error "Failed to read APP_VERSION"; exit 1 }
$githubRepo = py -c "from swiftmacro.constants import GITHUB_REPO; print(GITHUB_REPO)"
if ($LASTEXITCODE -ne 0 -or -not $githubRepo) { Write-Error "Failed to read GITHUB_REPO"; exit 1 }

# Guard against dirty working tree
$status = git status --porcelain
if ($status) {
    Write-Error "Working tree is dirty. Commit or stash changes before releasing."
    exit 1
}

# Guard against duplicate tag
$existingTag = git tag -l "v$version"
if ($existingTag) {
    Write-Error "Tag v$version already exists. Bump APP_VERSION first."
    exit 1
}

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

# Determine previous tag or first commit SHA.
# `git describe` errors (and PowerShell's Stop preference would abort the
# script) when no reachable tag exists, so temporarily drop to Continue for
# this probe and swallow both stderr and native errors.
$prevTag = $null
$savedPref = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $prevTag = git describe --tags --abbrev=0 2>$null
} catch {
    $prevTag = $null
}
$ErrorActionPreference = $savedPref
$global:LASTEXITCODE = 0
if (-not $prevTag) {
    $prevTag = git rev-list --max-parents=0 HEAD
    Write-Host "No reachable tag found, using first commit: $prevTag"
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
    --repo "$githubRepo" `
    --title "SwiftMacro v$version" `
    --notes "$changelog" `
    $exePath `
    $installerPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "gh release create failed. Make sure you are authenticated: gh auth login"
    exit 1
}

Write-Host "Release v$version published to https://github.com/$githubRepo/releases/tag/v$version"
