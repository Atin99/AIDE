# AIDE v5 - One-Click Launcher (PowerShell)
# Double-click or run: powershell -ExecutionPolicy Bypass -File START_AIDE.ps1

$Host.UI.RawUI.WindowTitle = "AIDE v5"
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "        AIDE v5 - Alloy Design Engine" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to script directory
Set-Location $PSScriptRoot

# Check internet
Write-Host "[1/3] Checking internet..." -ForegroundColor Yellow
try {
    $ping = Test-Connection -ComputerName "8.8.8.8" -Count 1 -Quiet -ErrorAction SilentlyContinue
    if ($ping) {
        Write-Host "[OK] Internet connected." -ForegroundColor Green
    } else {
        Write-Host "[WARNING] No internet. LLM features may be limited." -ForegroundColor DarkYellow
    }
} catch {
    Write-Host "[WARNING] Could not check internet." -ForegroundColor DarkYellow
}

# Activate venv
Write-Host "[2/3] Setting up environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
    Write-Host "[OK] Virtual environment activated (.venv)" -ForegroundColor Green
} elseif (Test-Path ".venv312\Scripts\Activate.ps1") {
    & ".venv312\Scripts\Activate.ps1"
    Write-Host "[OK] Virtual environment activated (.venv312)" -ForegroundColor Green
} else {
    Write-Host "[INFO] No venv found, using system Python." -ForegroundColor DarkYellow
}

# Install deps if needed
try {
    python -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "missing" }
} catch {
    Write-Host "[SETUP] Installing requirements..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Kill stale port
Write-Host "[3/3] Starting server..." -ForegroundColor Yellow
$stale = Get-NetTCPConnection -LocalPort 9000 -State Listen -ErrorAction SilentlyContinue
if ($stale) {
    $stale | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "[OK] Cleared stale process on port 9000." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  AIDE v5 running at: " -NoNewLine -ForegroundColor Cyan
Write-Host "http://localhost:9000/app/" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 9000 --reload
