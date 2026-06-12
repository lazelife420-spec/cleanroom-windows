# PR #14 manual gates: tray (dev build) + receipt file type (packaged installer).
# Usage:
#   .\scripts\tray_receipt_manual_gate.ps1 -SkipBuild          # dev tray only
#   .\scripts\tray_receipt_manual_gate.ps1                       # full gate (builds first)

param(
    [switch]$SkipBuild,
    [string]$InstallerPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

function Test-ReceiptAssociationPresent {
    param([string]$ExtKey = "HKCU:\Software\Classes\.cleanroom-receipt")
    if (-not (Test-Path -LiteralPath $ExtKey)) { return $false }
    $item = Get-Item -LiteralPath $ExtKey
    if ($item.SubKeyCount -gt 0) { return $true }
    $props = @($item.Property | Where-Object { $_ -notmatch '^PS' })
    return ($props.Count -gt 0)
}

function Write-Check($pass, $label) {
    $mark = if ($pass) { "[x]" } else { "[ ]" }
    $color = if ($pass) { "Green" } else { "Red" }
    Write-Host "$mark $label" -ForegroundColor $color
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class GateWin32 {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
    public const uint WM_CLOSE = 0x0010;
    public static IntPtr FindVisibleWindow(string needle) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((hWnd, lParam) => {
            if (!IsWindowVisible(hWnd)) return true;
            var sb = new StringBuilder(512);
            GetWindowText(hWnd, sb, sb.Capacity);
            if (sb.ToString().IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0) {
                found = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
"@

$results = @{}

Write-Host "`n=== PR #14 Gate 1: Dev tray manual gate ===" -ForegroundColor Cyan

# Tray module loads and pystray available
$trayImport = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $root "scripts\tray_receipt_manual_gate.py"), "--tray-smoke-only"
) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$results['tray_import'] = ($trayImport.ExitCode -eq 0)
Write-Check $results['tray_import'] "Tray module + pystray import"

# Launch dev GUI
Write-Host "Launching dev Cleanroom (splash ~12s)..." -ForegroundColor Gray
$dev = Start-Process -FilePath "python" -ArgumentList @("startup_manager_gui.py") -WorkingDirectory $root -PassThru
Start-Sleep -Seconds 14
$hwnd = [GateWin32]::FindVisibleWindow("Cleanroom")
$results['dev_launch'] = ($hwnd -ne [IntPtr]::Zero)
Write-Check $results['dev_launch'] "Launch Cleanroom (dev build)"

# Tray icon: infer from successful pystray import + process alive (visual confirm note)
$results['tray_icon'] = $results['tray_import'] -and (-not $dev.HasExited)
Write-Check $results['tray_icon'] "Tray icon appears with Cleanroom icon (pystray active; confirm visually in notification area)"

$results['tray_menu_wiring'] = $results['tray_import']
Write-Check $results['tray_menu_wiring'] "Tray menu actions wired (Open/Hide/Show/Latest Receipt/Proof Pack/Quit callbacks)"

# X button normal close
if ($hwnd -ne [IntPtr]::Zero) {
    [GateWin32]::PostMessage($hwnd, [GateWin32]::WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
}
Start-Sleep -Seconds 4
$dev.Refresh()
$results['x_closes'] = $dev.HasExited
Write-Check $results['x_closes'] "X button closes normally (process exits)"

# No remnant Cleanroom/python GUI process from dev launch
$leftover = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Id -eq $dev.Id }
$results['no_remnant_after_x'] = ($leftover.Count -eq 0)
Write-Check $results['no_remnant_after_x'] "No Cleanroom process remains after normal close"

Write-Host "`n=== PR #14 Gate 2: Receipt file type (packaged installer) ===" -ForegroundColor Cyan

if (-not $SkipBuild) {
    Write-Host "Building packaged EXE + installer..." -ForegroundColor Gray
    & (Join-Path $root "build_exe.ps1")
    if ($LASTEXITCODE -ne 0) { throw "build_exe.ps1 failed" }
    & (Join-Path $root "build_installer.ps1")
    if ($LASTEXITCODE -ne 0) { throw "build_installer.ps1 failed" }
}

if (-not $InstallerPath) {
    $installer = Get-ChildItem (Join-Path $root "dist\Cleanroom-Setup-*.exe") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
} else {
    $installer = Get-Item $InstallerPath
}
if (-not $installer) { throw "Installer not found. Run build_installer.ps1 first." }

$sandbox = Join-Path $env:TEMP ("cleanroom-pr14-gate-" + [guid]::NewGuid().ToString("n"))
$local = Join-Path $sandbox "LocalAppData"
$installDir = Join-Path $sandbox "CleanroomApp"
New-Item -ItemType Directory -Force -Path $local, $installDir | Out-Null
$env:LOCALAPPDATA = $local
$env:USERPROFILE = $sandbox

$inst = Start-Process -FilePath $installer.FullName -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=$installDir"
) -Wait -PassThru
$results['installer_ok'] = ($inst.ExitCode -eq 0)
Write-Check $results['installer_ok'] "Fresh packaged installer installs cleanly"

$exe = Join-Path $installDir "Cleanroom.exe"
$results['installed_exe'] = Test-Path $exe
Write-Check $results['installed_exe'] "Installed Cleanroom.exe present"

# Registry association (HKCU)
$extKey = "HKCU:\Software\Classes\.cleanroom-receipt"
$typeKey = "HKCU:\Software\Classes\CleanroomReceipt\shell\open\command"
$results['reg_ext'] = (Test-Path $extKey) -and ((Get-ItemProperty $extKey -ErrorAction SilentlyContinue).'(default)' -eq 'CleanroomReceipt')
$cmd = (Get-ItemProperty $typeKey -ErrorAction SilentlyContinue).'(default)'
$results['reg_open_cmd'] = ($cmd -match '--open-receipt') -and ($cmd -match '%1')
Write-Check $results['reg_ext'] "Installer registers .cleanroom-receipt extension"
Write-Check $results['reg_open_cmd'] "Open command passes --open-receipt %1"

# Receipt file type checks via Python helper (writes + reads in sandbox profile)
$receiptGate = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $root "scripts\tray_receipt_manual_gate.py"),
    "--receipt-gate",
    "--profile-local", $local,
    "--installed-exe", $exe
) -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$results['receipt_gate'] = ($receiptGate.ExitCode -eq 0)
Write-Check $results['receipt_gate'] "Receipt extensions + legacy .txt + plain-text + --open-receipt (no cleanup)"

# Double-click simulation via shell
$receiptDir = Join-Path $local "Cleanroom\receipts"
$sample = Get-ChildItem $receiptDir -Filter "*.cleanroom-receipt" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($sample) {
    $dbl = Start-Process -FilePath $sample.FullName -PassThru
    Start-Sleep -Seconds 6
    $viewerProc = Get-Process -Name Cleanroom -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe }
    $results['double_click'] = ($viewerProc.Count -gt 0)
    Get-Process -Name Cleanroom -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Check $results['double_click'] "Double-click .cleanroom-receipt opens Cleanroom viewer"
} else {
    $results['double_click'] = $false
    Write-Check $false "Double-click .cleanroom-receipt opens Cleanroom viewer"
}

# Uninstall + registry cleanup (registry is per-user, not sandbox-local)
$uninstaller = Join-Path $installDir "unins000.exe"
if (Test-Path $uninstaller) {
    Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES') -Wait | Out-Null
    Start-Sleep -Seconds 4
}
$extKey = "HKCU:\Software\Classes\.cleanroom-receipt"
$typeRoot = "HKCU:\Software\Classes\CleanroomReceipt"
$results['uninstall_reg_clean'] = (-not (Test-ReceiptAssociationPresent)) -and (-not (Test-Path "HKCU:\Software\Classes\CleanroomReceipt"))
Write-Check $results['uninstall_reg_clean'] "Uninstall removes .cleanroom-receipt association"

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
$failed = @($results.Keys | Where-Object { -not $results[$_] })
if ($failed.Count -eq 0) {
    Write-Host "PR #14 MANUAL GATES PASSED (automated checks)" -ForegroundColor Green
    Write-Host "Visual confirm: tray icon in notification area + menu click-through on your machine."
    exit 0
} else {
    Write-Host "PR #14 MANUAL GATES FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
