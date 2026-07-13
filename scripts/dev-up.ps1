# PowerShell helper: start local infrastructure services.
$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not (Test-Path ".env")) {
    Write-Host "Copying .env.example to .env"
    Copy-Item ".env.example" ".env"
}

docker compose up -d
docker compose ps
