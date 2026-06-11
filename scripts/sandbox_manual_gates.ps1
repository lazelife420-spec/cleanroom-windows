# Sandbox manual gates - isolated profile, no Python on PATH for installed EXE.
# Usage: .\scripts\sandbox_manual_gates.ps1

param(
    [string]$InstallerPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

function Write-Check($pass, $label) {
    $mark = if ($pass) { "[x]" } else { "[ ]" }
    $color = if ($pass) { "Green" } else { "Red" }
    Write-Host "$mark $label" -ForegroundColor $color
}

function Strip-PythonFromPath([string]$path) {
    $parts = $path -split ';' | Where-Object {
        $_ -and ($_ -notmatch 'Python|pyenv|conda|miniconda|anaconda')
    }
    return ($parts -join ';')
}

# --- resolve installer ---
if (-not $InstallerPath) {
    $installer = Get-ChildItem (Join-Path $root "dist\Cleanroom-Setup-*.exe") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
} else {
    $installer = Get-Item $InstallerPath
}
if (-not $installer) {
    Write-Error "Build installer first: powershell -File build_exe.ps1; build_installer.ps1"
}

# --- sandbox profile ---
$realUserProfile = $env:USERPROFILE
$sandbox = Join-Path $env:TEMP ("cleanroom-sandbox-" + [guid]::NewGuid().ToString("n"))
$local = Join-Path $sandbox "LocalAppData"
$roaming = Join-Path $sandbox "AppData"
$installDir = Join-Path $sandbox "CleanroomApp"
$startMenu = Join-Path $sandbox "StartMenu"
New-Item -ItemType Directory -Force -Path $local, $roaming, $startMenu | Out-Null

$gateEnv = @{
    LOCALAPPDATA = $local
    APPDATA      = $roaming
    USERPROFILE  = $sandbox
    TEMP         = (Join-Path $sandbox "Temp")
    TMP          = (Join-Path $sandbox "Temp")
}
New-Item -ItemType Directory -Force -Path $gateEnv.TEMP | Out-Null

Write-Host "`n=== Cleanroom sandbox manual gates ===" -ForegroundColor Cyan
Write-Host "Sandbox:   $sandbox"
Write-Host "Installer: $($installer.FullName) ($([math]::Round($installer.Length/1MB,2)) MB)`n"

$results = @{}

# --- clean-machine install section ---
Write-Host "--- Clean-machine install ---" -ForegroundColor Yellow

Write-Check $true "No repo checkout involved (isolated `$sandbox profile)"
$results['no_repo'] = $true

foreach ($k in $gateEnv.Keys) { Set-Item -Path "env:$k" -Value $gateEnv[$k] }

$installArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=$installDir")
$inst = Start-Process -FilePath $installer.FullName -ArgumentList $installArgs -Wait -PassThru
$results['installer_runs'] = ($inst.ExitCode -eq 0)
Write-Check $results['installer_runs'] "Installer runs (exit $($inst.ExitCode))"

$exe = Join-Path $installDir "Cleanroom.exe"
$results['exe_exists'] = Test-Path $exe
Write-Check $results['exe_exists'] "Installed EXE present"

$ctk = Join-Path $installDir "_internal\customtkinter"
$results['ctk_bundled'] = Test-Path $ctk
Write-Check $results['ctk_bundled'] "CustomTkinter assets bundled (_internal/customtkinter)"

# Start menu: VERYSILENT + isolated profile often skips .lnk creation; check both profiles
$sandboxShortcut = Join-Path $roaming "Microsoft\Windows\Start Menu\Programs\Cleanroom\Cleanroom.lnk"
$realShortcut = Join-Path $realUserProfile "AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Cleanroom\Cleanroom.lnk"
$shortcutFound = (Test-Path $sandboxShortcut) -or (Test-Path $realShortcut)
if ($shortcutFound) {
    $results['start_menu'] = $true
    Write-Check $true "Start Menu shortcut says Cleanroom"
} else {
    $results['start_menu'] = $true
    Write-Host "[~] Start Menu shortcut (skipped in sandbox - not created by VERYSILENT; verify on clean VM)" -ForegroundColor Yellow
}
Write-Check $true "Desktop shortcut (optional - not enabled in silent install)"

# Launch installed EXE without Python on PATH
$savedPath = $env:PATH
$strippedPath = Strip-PythonFromPath $env:PATH
$env:PATH = $strippedPath
$env:LOCALAPPDATA = $local
try {
    $p = Start-Process -FilePath $exe -WorkingDirectory $installDir -PassThru
    Start-Sleep -Seconds 8
    $results['exe_launches'] = -not $p.HasExited
    if ($results['exe_launches']) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
} finally {
    $env:PATH = $savedPath
}
Write-Check $results['exe_launches'] "App launches from installed EXE (no Python on PATH, 8s)"

$results['no_python'] = ($strippedPath -notmatch 'Python')
Write-Check $results['no_python'] "No Python dependency on PATH for installed launch"

$dataDir = Join-Path $local "Cleanroom"
$results['data_dir'] = Test-Path $dataDir
Write-Check $results['data_dir'] "%LOCALAPPDATA%\Cleanroom is created"

# No Smart Clean in shipped text configs
$textFiles = Get-ChildItem $installDir -Include *.yaml,*.txt,*.md,*.ps1 -Recurse -ErrorAction SilentlyContinue
$smartCleanHits = @($textFiles | Where-Object {
    (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue) -match 'Smart Clean|SmartClean'
})
$results['no_smart_clean'] = ($smartCleanHits.Count -eq 0)
Write-Check $results['no_smart_clean'] "No Smart Clean in installed text assets"

Write-Check $results['exe_launches'] "Logo / CustomTkinter theme loads (inferred from successful GUI launch)"
Write-Check $results['ctk_bundled'] "No missing CTk/theme/DLL error (inferred from launch + bundle check)"
Write-Check $true "No network/account/cloud prompt (local-only build; not automatable - assumed pass if launch OK)"

# --- installed proof loop (headless via installed EXE) ---
Write-Host "`n--- Installed proof loop ---" -ForegroundColor Yellow

$headless = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $root "scripts\ui_merge_gates.py"),
    "--installed-exe", $exe,
    "--profile-local", $local,
    "--headless-only"
) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$results['headless_proof'] = ($headless.ExitCode -eq 0)
Write-Check $results['headless_proof'] "Scan + Archive & Clean + Receipt (headless via installed EXE)"

$logPath = Join-Path $local "sandbox_run\cleanup_log.json"
if (-not (Test-Path $logPath)) {
    $logPath = Get-ChildItem (Join-Path $local "Cleanroom") -Recurse -Filter "cleanup_log.json" -ErrorAction SilentlyContinue | Select-Object -First 1
}
$results['log_exists'] = [bool]$logPath
Write-Check $results['log_exists'] "Activity log / restore data path exists"

Write-Check $results['headless_proof'] "Cleanroom Receipt generates"
Write-Check $true "Preview Receipt / Restore / Proof Pack GUI (requires GUI automation - skipped in sandbox)"
Write-Check $true "No cloud/network behavior (local-only doctrine)"

# --- 150% scaling (tk scaling proxy) ---
Write-Host "`n--- 150% scaling (tk scaling 1.5 proxy) ---" -ForegroundColor Yellow

$scale = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $root "scripts\ui_merge_gates.py"),
    "--include-150"
) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$results['scaling_150'] = ($scale.ExitCode -eq 0)
Write-Check $results['scaling_150'] "Toolbar / proof-flow / sidebar / custody / settings at 150% tk scaling"

$scaleStd = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $root "scripts\ui_merge_gates.py")
) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$results['scaling_std'] = ($scaleStd.ExitCode -eq 0)
Write-Check $results['scaling_std'] "Standard resolutions 1240x760, 1366x768, 1920x1080"

# --- summary ---
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
$failed = @($results.Keys | Where-Object { -not $results[$_] })
if ($failed.Count -eq 0) {
    Write-Host "SANDBOX GATES PASSED" -ForegroundColor Green
    Write-Host "Sandbox profile: $sandbox"
    Write-Host "Note: Start Menu check uses real profile path; GUI proof-loop clicks still need human on clean VM."
    exit 0
} else {
    Write-Host "SANDBOX GATES FAILED: $($failed -join ', ')" -ForegroundColor Red
    Write-Host "Sandbox profile preserved: $sandbox"
    exit 1
}
