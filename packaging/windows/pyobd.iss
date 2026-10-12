#define AppName "pyOBD"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{26A2A40D-D046-4E9B-80BA-5E36B39D6807}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=FareBrothers, LLC
AppPublisherURL=https://farebros.com
AppSupportURL=https://github.com/alexfare/pyobd/issues
DefaultDirName={autopf}\pyOBD
DefaultGroupName=pyOBD
DisableProgramGroupPage=yes
LicenseFile=..\..\COPYING
OutputDir=..\..\installer-dist
OutputBaseFilename=pyOBD-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\..\pyobd.ico
UninstallDisplayIcon={app}\pyOBD.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\..\dist\pyOBD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\pyOBD"; Filename: "{app}\pyOBD.exe"
Name: "{autodesktop}\pyOBD"; Filename: "{app}\pyOBD.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\pyOBD.exe"; Description: "Launch pyOBD"; Flags: nowait postinstall skipifsilent
