# Manual gate: Explorer + in-app context menus (HKCU shell keys, custody-only delete).
# Usage: powershell -File scripts/shell_context_menu_manual_gate.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)

Write-Host "`n=== Shell context menu manual gate ===" -ForegroundColor Cyan
python (Join-Path $root "scripts\shell_context_menu_manual_gate.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== In-app context menu smoke ===" -ForegroundColor Cyan
python (Join-Path $root "scripts\smoke_shell_context_menu.py")
exit $LASTEXITCODE
