#define AppName "RetroMind Player"
#define AppVersion "0.1.1"
#define AppDisplayVersion "0.1.1 Beta"
#ifndef BundleDir
  #define BundleDir "..\dist\0.1.1-beta\RetroMindPlayer"
#endif
#ifndef ReleaseDir
  #define ReleaseDir "..\release"
#endif
[Setup]
AppId={{5C759A24-7B4C-4EE4-AB17-1E46217E6227}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppDisplayVersion}
AppPublisher=Wilfred Bancairen
VersionInfoVersion=0.1.1.0
VersionInfoTextVersion={#AppDisplayVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion=0.1.1.0
VersionInfoProductTextVersion={#AppDisplayVersion}
DefaultDirName={localappdata}\Programs\RetroMindPlayer
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
UsePreviousAppDir=yes
UsePreviousTasks=yes
DisableProgramGroupPage=yes
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
Uninstallable=yes
UninstallDisplayName={#AppName} {#AppDisplayVersion}
UninstallDisplayIcon={app}\RetroMindPlayer.exe
SetupIconFile=..\retromind\assets\retromind.ico
InfoBeforeFile=RELEASE_NOTES.md
OutputDir={#ReleaseDir}
OutputBaseFilename=RetroMindPlayer-0.1.1-Beta-win64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\RetroMindPlayer.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\RetroMindPlayer.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\RetroMindPlayer.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
; Deliberately no user-data, media, AppData or wildcard UninstallDelete entries.

[Code]
function CloseRetroMind(): String;
var
  ResultCode: Integer;
  ProgramPath: String;
begin
  Result := '';
  ProgramPath := ExpandConstant('{app}\RetroMindPlayer.exe');
  if FileExists(ProgramPath) then begin
    if not Exec(ProgramPath, '--quit-for-update', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      Result := 'Please close RetroMind Player and retry. Setup could not request orderly shutdown.'
    else if ResultCode <> 0 then
      Result := 'Please close RetroMind Player and retry. It may still be finishing a media operation.';
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := CloseRetroMind();
end;

function InitializeUninstall(): Boolean;
var
  MessageText: String;
begin
  MessageText := CloseRetroMind();
  Result := MessageText = '';
  if not Result then
    SuppressibleMsgBox(MessageText, mbError, MB_OK, IDOK);
end;
