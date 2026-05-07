$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

docker compose ps
Write-Host ""
Write-Host "Backend health:"
try {
  Invoke-RestMethod "http://localhost:8000/api/health" | ConvertTo-Json -Depth 5
} catch {
  Write-Host $_.Exception.Message
}
