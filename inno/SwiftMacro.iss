; SwiftMacro Inno Setup Script
; AppVersion and GitHubRepo are passed from build_installer.ps1 via /DAppVersion=x.y.z /DGitHubRepo=...

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef GitHubRepo
  #define GitHubRepo "owner/SwiftMacro"
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
