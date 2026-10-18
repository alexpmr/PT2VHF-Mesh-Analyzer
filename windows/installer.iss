#define AppName "PT2VHF Mesh Analyzer"
#define AppVersion "0.6.31"
[Setup]
AppId={{8AB1D4E5-9A9C-46DC-8C24-5D89A6D98701}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Alex, PT2VHF
DefaultDirName={localappdata}\Programs\PT2VHF Mesh Analyzer
DefaultGroupName=PT2VHF Mesh Analyzer
OutputDir=..\dist
OutputBaseFilename=PT2VHF-Mesh-Analyzer-Setup-Win10-Win11-x64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
; Windows 10 1809 (build 17763) / Windows 11 x64. Inno compiler should reject older systems.
MinVersion=10.0.17763
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\branding\mesh-analyzer.ico
WizardStyle=modern
SetupIconFile=..\branding\mesh-analyzer.ico
CloseApplications=no
RestartApplications=no

[Files]
Source: "..\dist\PT2VHF-Mesh-Analyzer.exe"; DestDir: "{app}"; Flags: ignoreversion
; Icon stored separately at a stable path, independent of onefile exe resource cache.
Source: "..\branding\mesh-analyzer.ico"; DestDir: "{app}\branding"; Flags: ignoreversion
Source: "..\windows\close_running_mesh.ps1"; Flags: dontcopy

[Icons]
Name: "{group}\PT2VHF Mesh Analyzer"; Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"; IconFilename: "{app}\branding\mesh-analyzer.ico"; AppUserModelID: "PT2VHF.MeshAnalyzer"
Name: "{autodesktop}\PT2VHF Mesh Analyzer"; Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"; IconFilename: "{app}\branding\mesh-analyzer.ico"; AppUserModelID: "PT2VHF.MeshAnalyzer"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Criar atalho na área de trabalho"; Flags: unchecked
[Run]
Filename: "{app}\PT2VHF-Mesh-Analyzer.exe"; Description: "Abrir PT2VHF Mesh Analyzer"; Flags: nowait postinstall skipifsilent
[Code]
{ The Restart Manager cannot reliably stop both PyInstaller one-file
  bootloader and its GUI child. Explicitly close only same-user instances
  whose full executable path equals this installation target. }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ScriptName, TargetName, Params: String;
begin
  if CurStep <> ssInstall then
    Exit;
  ExtractTemporaryFile('close_running_mesh.ps1');
  ScriptName := ExpandConstant('{tmp}\close_running_mesh.ps1');
  TargetName := ExpandConstant('{app}\PT2VHF-Mesh-Analyzer.exe');
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ScriptName + '" -TargetExe "' + TargetName + '"';
  Log('Preparing to stop existing Mesh Analyzer process for: ' + TargetName);
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
     Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Falha ao executar a verificação de processos antigos. A instalação não continuará.', mbError, MB_OK);
    Abort;
  end;
  if ResultCode <> 0 then
  begin
    MsgBox('Não foi possível encerrar com segurança a versão anterior. ' +
      'A instalação foi interrompida para proteger os dados. ' +
      'Consulte installer-close.log na pasta de dados do Mesh Analyzer. Código: ' +
       IntToStr(ResultCode), mbError, MB_OK);
    Abort;
  end;
end;
