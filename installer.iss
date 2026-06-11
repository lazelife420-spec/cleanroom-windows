; Inno Setup script for Cleanroom
; Build with: build_installer.ps1 (or ISCC.exe installer.iss)
; Requires dist\Cleanroom\Cleanroom.exe (run build_exe.ps1 first)

#define AppName "Cleanroom"
#define AppVersion "1.0.1"
#define AppPublisher "Cleanroom"
#define AppExeName "Cleanroom.exe"

[Setup]
AppId={{8B1F1A1E-5C3D-4D2A-9F6B-3A7C42D91E06}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Cleanroom-Setup-{#AppVersion}
SetupIconFile=assets\brand\cleanroom-icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Cleanroom\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Cleanroom\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "register_task.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "run_scheduled.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
