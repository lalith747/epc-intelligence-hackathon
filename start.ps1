$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
Set-Location $backend

Write-Host "Starting Unified AI Data-Centre Project Intelligence Platform"
Write-Host "URL: http://127.0.0.1:8010/dashboard"
Write-Host "Press Ctrl+C to stop."

python -m uvicorn app.unified_main:app --host 127.0.0.1 --port 8010
