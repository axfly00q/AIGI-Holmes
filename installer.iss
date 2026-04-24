; =============================================================================
;  AIGI-Holmes  —  Inno Setup 6 installer script
; =============================================================================
;
;  Usage (developer machine, Inno Setup 6.2+ must be installed):
;
;      iscc installer.iss
;
;  Prerequisites:
;      1. Run  pyinstaller AIGI_Holmes.spec -y  first.
;         This creates  dist\AIGI-Holmes\  which is the source for this script.
;
;  Output:
;      dist\AIGI-Holmes-Setup-v2.0.0.exe
;
;  What this installer does for the end-user:
;      • Copies all app files to  %LocalAppData%\AIGI-Holmes\   (no UAC needed)
;      • Creates a desktop shortcut  (checked by default)
;      • Creates a Start Menu entry
;      • Registers an Uninstall entry in  "Apps & Features"
;      • Optionally launches the app at the end of setup
; =============================================================================

; ------------- Compile-time defines ------------------------------------------
#define AppName        "AIGI-Holmes"
#define AppVersion     "2.0.0"
#define AppPublisher   "AIGI-Holmes Team"
#define AppDescription "新闻图片 AI 生成检测系统"
#define AppExeName     "AIGI-Holmes.exe"
#define AppURL         "https://github.com/AIGI-Holmes/AIGI-Holmes"
; Source folder produced by PyInstaller  (relative to this .iss file)
#define SourceDir      "dist\AIGI-Holmes"

; =============================================================================
[Setup]
; ------------- Identification -------------------------------------------------
AppId={{F4A87C31-2B5E-4D3A-8F9C-1E6042D5B738}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; ------------- Install / uninstall layout ------------------------------------
; Use %LocalAppData% so no UAC prompt is required on Windows 10/11.
; Equivalent to  C:\Users\<user>\AppData\Local\AIGI-Holmes
DefaultDirName={localappdata}\{#AppName}
DisableDirPage=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; ------------- Output ---------------------------------------------------------
OutputDir=dist
OutputBaseFilename=AIGI-Holmes-Setup-v{#AppVersion}
SetupIconFile=asset\app.ico
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}

; ------------- Compression ----------------------------------------------------
; lzma2/max balances size and reliability; ultra64 can OOM on low-memory machines
; and produce a corrupted archive.  SolidCompression=yes gives best ratio.
Compression=lzma2/max
SolidCompression=yes

; ------------- Visual style ---------------------------------------------------
WizardStyle=modern
WizardImageFile=asset\wizard_image.bmp
WizardSmallImageFile=asset\wizard_small.bmp

; ------------- Requirements ---------------------------------------------------
; Windows 10 version 1809 (build 17763) — minimum for Edge WebView2
MinVersion=10.0.17763

; x64 only (torch ships x64 binaries)
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; ------------- Privileges -----------------------------------------------------
; "lowest" = install per-user without elevation / UAC
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; ------------- Close running processes ----------------------------------------
; Automatically close AIGI-Holmes.exe if it is running so that Inno Setup can
; replace / rename files without getting "Access Denied" (error 5) from Windows.
; Without this, any locked file causes a MoveFile failure on other machines.
CloseApplications=yes
CloseApplicationsFilter=AIGI-Holmes.exe
RestartApplications=no

; ------------- Misc -----------------------------------------------------------
ChangesAssociations=no

; =============================================================================
[Languages]
Name: "chs";     MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; =============================================================================
[Tasks]
; Desktop shortcut — checked by default so judges / reviewers see it
; immediately after installation.
Name: "desktopicon"; Description: "在桌面创建快捷方式 (&D)"; GroupDescription: "额外图标:"; Flags: checkedonce

; =============================================================================
[Files]
; Copy everything produced by PyInstaller into the install dir.
; recursesubdirs + createallsubdirs handles the _internal/ sub-tree and all
; bundled data (templates/, static/, clip/, CLIP models, etc.).
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copy .env file containing API keys (Doubao, Serper) and configuration.
; Using absolute path to ensure Inno Setup finds it regardless of working directory.
Source: "d:\aigi修改\AIGI-Holmes-main\.env"; DestDir: "{app}"; Flags: ignoreversion

; =============================================================================
[Icons]
; Start Menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Comment: "{#AppDescription}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (created only when the task is selected)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExeName}"; Comment: "{#AppDescription}"; Tasks: desktopicon

; =============================================================================
[Run]
; Offer to launch the app right after setup finishes.
Filename: "{app}\{#AppExeName}"; Description: "立即启动 {#AppName}（Loading model: ~15 秒）"; Flags: nowait postinstall skipifsilent

; =============================================================================
[UninstallDelete]
; Clean up the SQLite database and log files that the app creates at runtime.
Type: filesandordirs; Name: "{app}\aigi_holmes.db"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\.env"
; Remove the app directory itself if it is now empty
Type: dirifempty;    Name: "{app}"

; =============================================================================
[Code]
// ---------------------------------------------------------------------------
// Pre-install: warn the user if the app is already running so they can close
// it before setup overwrites the files.
// ---------------------------------------------------------------------------
function IsProcessRunning(const ExeName: String): Boolean;
var
  WbemLocator, WbemServices, WbemObjectSet: Variant;
  Count: Integer;
begin
  Result := False;
  try
    WbemLocator   := CreateOleObject('WbemScripting.SWbemLocator');
    WbemServices  := WbemLocator.ConnectServer('.', 'root\CIMV2', '', '');
    WbemObjectSet := WbemServices.ExecQuery(
      'SELECT * FROM Win32_Process WHERE Name = ''' + ExeName + '''');
    Count := WbemObjectSet.Count;
    Result := Count > 0;
  except
    // WMI not available — assume not running
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if IsProcessRunning('{#AppExeName}') then
  begin
    MsgBox(
      'AIGI-Holmes 正在运行。' + #13#10 +
      '请在继续安装前关闭程序。',
      mbInformation, MB_OK);
    Result := False;
  end;
end;

// ---------------------------------------------------------------------------
// Pre-uninstall: warn the user if the app is currently running.
// ---------------------------------------------------------------------------
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if IsProcessRunning('{#AppExeName}') then
  begin
    MsgBox(
      '请先关闭 AIGI-Holmes，再卸载程序。',
      mbInformation, MB_OK);
    Result := False;
  end;
end;
