param(
    [string]$PythonExe = "python",
    [string]$Script = "startup_manager_gui.py",
    [string]$DistName = "Cleanroom",
    [switch]$OneFile,
    [switch]$Console
)

# Ensure PyInstaller is installed
$check = & $PythonExe -m pip show pyinstaller 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller not found. Installing..."
    & $PythonExe -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller."
        exit 1
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$absScript = Join-Path $scriptDir $Script

$opts = @('--name', $DistName, '--noconfirm', '--clean')
if ($OneFile) { $opts += '--onefile' }
if (-not $Console) { $opts += '--noconsole' }

# App icon (exe resource + bundled for the window titlebar)
$iconPath = Join-Path $scriptDir 'assets\brand\cleanroom-icon.ico'
if (-not (Test-Path $iconPath)) {
    $iconPath = Join-Path $scriptDir 'icon.ico'
}
if (Test-Path $iconPath) {
    $opts += @('--icon', $iconPath)
    $opts += @('--add-data', "${iconPath};.")
}
$iconPng = Join-Path $scriptDir 'assets\brand\cleanroom-icon.png'
if (-not (Test-Path $iconPng)) {
    $iconPng = Join-Path $scriptDir 'icon.png'
}
if (Test-Path $iconPng) {
    $opts += @('--add-data', "${iconPng};.")
}

# Bundle the default config alongside the app
$configPath = Join-Path $scriptDir 'cleanup_config.yaml'
$opts += @('--add-data', "${configPath};.")

# Helper scripts the GUI shells out to (scheduling)
foreach ($ps1 in @('register_task.ps1', 'run_scheduled.ps1')) {
    $p = Join-Path $scriptDir $ps1
    if (Test-Path $p) { $opts += @('--add-data', "${p};.") }
}

# CustomTkinter themes/assets — required for packaged EXE (no runtime download)
$opts += @('--collect-all', 'customtkinter')
$opts += @('--copy-metadata', 'customtkinter')

$opts += $absScript

Write-Host "Running PyInstaller with: PyInstaller $($opts -join ' ')"
& $PythonExe -m PyInstaller @opts

if ($LASTEXITCODE -eq 0) {
    if ($OneFile) {
        Write-Host "Build complete: dist\$DistName.exe"
    } else {
        Write-Host "Build complete: dist\$DistName\$DistName.exe"
    }
} else {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
