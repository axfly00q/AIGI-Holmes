; AIGI-Holmes Inno Setup Installer Script
; Build with Inno Setup 6 (https://jrsoftware.org/isinfo.php)
;
; Prerequisites:
;   1. Run `pyinstaller AIGI_Holmes.spec` first to populate dist\AIGI-Holmes\
;   2. Open this file in Inno Setup Compiler (or run `iscc installer.iss`)
;   3. The installer is written to dist\AIGI-Holmes-Setup.exe

#define AppName      "AIGI-Holmes"
#define AppVersion   "1.0"
#define AppPublisher "AIGI-Holmes Contributors"
#define AppURL       "https://github.com/axfly00q/AIGI-Holmes"
#define AppExeName   "AIGI-Holmes.exe"
#define SourceDir    "dist\AIGI-Holmes"

[Setup]
AppId={{E4A2F3B1-7C9D-4E5F-A8B6-2D1C0F3E9A7B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Output location relative to the script file (repository root)
OutputDir=dist
OutputBaseFilename=AIGI-Holmes-Setup
SetupIconFile=asset\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Require Windows 10 or later (needed for the WebView2 backend used by pywebview)
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Copy the entire PyInstaller output directory
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu entry
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\asset\app.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut (created only when the user selects the task above)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\asset\app.ico"; Tasks: desktopicon

[Run]
; Offer to launch the app immediately after installation
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName,'&','&&')}}"; Flags: nowait postinstall skipifsilent
