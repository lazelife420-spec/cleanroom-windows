# Enable required status checks on main (repo admin required).
# Usage: .\scripts\enable_branch_protection.ps1 [-Repo owner/name]

param(
    [string]$Repo = "Z3r0DayZion-install/cleanroom-windows"
)

$checks = @(
    'CI / tests',
    'CI / public-surface',
    'CI / migration',
    'CI / security',
    'Build Windows'
)

$body = @{
    required_status_checks = @{
        strict   = $true
        contexts = $checks
    }
    enforce_admins                 = $true
    required_pull_request_reviews  = $null
    restrictions                   = $null
    allow_force_pushes             = $false
    allow_deletions                = $false
} | ConvertTo-Json -Depth 6

Write-Host "Applying branch protection to $Repo (main)..."
Write-Host "Required checks: $($checks -join ', ')"
$body | gh api -X PUT "repos/$Repo/branches/main/protection" --input -
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed. Ensure you have admin access and gh is authenticated."
    exit 1
}
Write-Host "Branch protection enabled."
