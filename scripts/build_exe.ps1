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
$version = py -c "from swiftmacro.constants import APP_VERSION; print(APP_VERSION)"
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
