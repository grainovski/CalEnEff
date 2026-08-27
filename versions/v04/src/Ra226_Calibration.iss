; Ra226_Calibration.iss — Inno Setup script
; Build: ISCC Ra226_Calibration.iss
; Output: dist\WinInstaller\CalEnEff_Setup.exe

; AppVersion is the single source of truth for the whole project: build.ps1
; reads it to stamp build_info.py, and the Linux packaging scripts read it to
; version the DEB and RPM.  Bump it here and nowhere else.
#define AppName    "CalEnEff"
#define AppVersion "4.0"
#define AppExe     "CalEnEff.exe"
#define AppDir     "dist\CalEnEff"

[Setup]
AppId={{03EF4FFE-CEFE-49CF-B421-1B94DAC9CB54}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
DefaultDirName={autopf}\CalEnEff
DefaultGroupName=CalEnEff
OutputDir=dist\WinInstaller
OutputBaseFilename=CalEnEff_Setup
SetupIconFile=CalEnEff.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=zip
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
; Allow non-admin install to user's AppData\Local\Programs;
; or admin install to Program Files — user picks at launch.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
; App is 64-bit — install to Program Files, not Program Files (x86)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Close the app gracefully if it is running during (re)install
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#AppDir}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

; ── Uninstall-previous-version logic ────────────────────────────────────────
; When the installer detects an existing installation (via the AppId registry
; key), it asks the user whether to uninstall the old version first.
; Choosing Yes runs the previous uninstaller silently, leaving a clean slate;
; choosing No installs over the top (files are still replaced — ignoreversion).
[Code]
function GetUninstallString(Hive: Integer): String;
var
  RegPath: String;
  UninstStr: String;
begin
  RegPath   := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{03EF4FFE-CEFE-49CF-B421-1B94DAC9CB54}_is1';
  UninstStr := '';
  RegQueryStringValue(Hive, RegPath, 'UninstallString', UninstStr);
  Result := UninstStr;
end;

function FindPreviousUninstaller(): String;
var
  S: String;
begin
  S := GetUninstallString(HKLM);
  if S = '' then S := GetUninstallString(HKCU);
  Result := S;
end;

function InitializeSetup(): Boolean;
var
  UninstStr:  String;
  UninstExe:  String;
  ResultCode: Integer;
  Answer:     Integer;
begin
  Result   := True;
  UninstStr := FindPreviousUninstaller();
  if UninstStr = '' then Exit;

  Answer := MsgBox(
    'A previous installation of {#AppName} was found.'  + #13#10 +
    'It is recommended to remove it before installing a new version.' + #13#10#13#10 +
    'Do you want to uninstall the previous version now?',
    mbConfirmation, MB_YESNO);

  if Answer = IDYES then begin
    UninstExe := RemoveQuotes(UninstStr);
    if not Exec(UninstExe, '/SILENT /NORESTART', '', SW_SHOW,
                ewWaitUntilTerminated, ResultCode) then begin
      MsgBox('The uninstaller could not be launched: ' + SysErrorMessage(ResultCode),
             mbError, MB_OK);
    end;
  end;
end;
