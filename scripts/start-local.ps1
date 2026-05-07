param(
  [switch]$PullModel
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Review secrets before production use."
}

docker compose up -d --build

if ($PullModel) {
  docker compose exec ollama ollama pull llama3.1:8b
}

Write-Host "KHULOUD AI OS is starting."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000/api/health"
