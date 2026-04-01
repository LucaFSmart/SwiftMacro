$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# Read version and repo from constants
$version = py -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
$githubRepo = py -c "from swiftmacro.constants import GITHUB_REPO; print(GITHUB_REPO)"

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
    --notes "$changelog" `
    $exePath `
    $installerPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "gh release create failed. Make sure you are authenticated: gh auth login"
    exit 1
}

Write-Host "Release v$version published to https://github.com/$githubRepo/releases/tag/v$version"
