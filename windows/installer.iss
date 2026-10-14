#define AppName "PT2VHF Mesh Analyzer"
#define AppVersion "0.1.1"
[Setup]
AppId={{8AB1D4E5-9A9C-46DC-8C24-5D89A6D98701}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Alex, PT2VHF
DefaultDirName={localappdata}\Programs\PT2VHF Mesh Analyzer
DefaultGroupName=PT2VHF Mesh Analyzer
OutputDir=..\dist
OutputBaseFilename=PT2VHF-Mesh-Analyzer-Setup-Win11-x64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\PT2VHF-Mesh-Analyzer.exe
WizardStyle=modern
[Files]
Source: "..\dist\PT2VHF-Mesh-Analyzer.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\PT2VHF Mesh Analyzer"; Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"
Name: "{autodesktop}\PT2VHF Mesh Analyzer"; Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Criar atalho na área de trabalho"; Flags: unchecked
[Run]
Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"; Description: "Abrir PT2VHF Mesh Analyzer"; Flags: nowait postinstall skipifsilent