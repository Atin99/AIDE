param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 5173
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path ".").Path

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\\frontend'; python -m http.server $WebPort"

Write-Output "API: http://localhost:$ApiPort"
Write-Output "Frontend: http://localhost:$WebPort"
