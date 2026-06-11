# Clean-profile installer gate (dev helper — run on a truly clean machine for final sign-off).
# Usage: .\scripts\clean_install_gate.ps1 [-InstallerPath dist\Cleanroom-Setup-1.0.1.exe]

param(
    [string]$InstallerPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
if (-not $InstallerPath) {
    $candidates = Get-ChildItem (Join-Path $root "dist\Cleanroom-Setup-*.exe") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if (-not $candidates) {
        Write-Error "No installer found under dist\Cleanroom-Setup-*.exe"
    }
    $installer = $candidates[0]
} else {
    $installer = Get-Item $InstallerPath -ErrorAction Stop
}

$profile = Join-Path $env:TEMP ("cleanroom-install-gate-" + [guid]::NewGuid().ToString("n"))
$local = Join-Path $profile "LocalAppData"
$installDir = Join-Path $profile "CleanroomApp"
New-Item -ItemType Directory -Force -Path $local | Out-Null

Write-Host "=== Clean install gate ===" -ForegroundColor Cyan
Write-Host "Profile:  $profile"
Write-Host "Installer: $($installer.FullName) ($([math]::Round($installer.Length/1MB,2)) MB)"

$env:LOCALAPPDATA = $local
$args = @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
    "/DIR=$installDir"
)
Write-Host "Running silent install..."
$proc = Start-Process -FilePath $installer.FullName -ArgumentList $args -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Error "Installer exit code $($proc.ExitCode)"
}

$exe = Join-Path $installDir "Cleanroom.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Installed EXE missing: $exe"
}
Write-Host "OK: Installed to $installDir" -ForegroundColor Green

$ctk = Join-Path $installDir "_internal\customtkinter"
if (-not (Test-Path $ctk)) {
    Write-Error "customtkinter assets missing under _internal"
}
Write-Host "OK: customtkinter bundled" -ForegroundColor Green

$p = Start-Process -FilePath $exe -WorkingDirectory $installDir -PassThru
Start-Sleep -Seconds 8
if ($p.HasExited) {
    Write-Error "Cleanroom exited early with code $($p.ExitCode)"
}
Stop-Process -Id $p.Id -Force
Write-Host "OK: Installed EXE launched (8s)" -ForegroundColor Green

$data = Join-Path $local "Cleanroom"
if (Test-Path $data) {
    Write-Host "OK: Data dir created: $data" -ForegroundColor Green
    Get-ChildItem $data -ErrorAction SilentlyContinue | Select-Object Name
} else {
    Write-Host "NOTE: No $data yet (may appear after first action)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Automated clean-profile install gate PASSED." -ForegroundColor Green
Write-Host "Manual still required: Start Menu shortcut, scaling at 150%, full proof-loop clicks." -ForegroundColor Yellow
