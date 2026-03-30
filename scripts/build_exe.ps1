$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$iconPath = Join-Path $repoRoot "build\swiftmacro.ico"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $iconPath) | Out-Null

@'
from pathlib import Path
from swiftmacro.icon import ensure_windows_icon_file

source = Path(ensure_windows_icon_file())
target = Path("build/swiftmacro.ico")
target.write_bytes(source.read_bytes())
print(target)
'@ | py -

py -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --noconsole `
    --name SwiftMacro `
    --specpath build `
    --icon "$iconPath" `
    --collect-submodules pystray `
    --collect-submodules PIL `
    --hidden-import PIL._tkinter_finder `
    swiftmacro.pyw
