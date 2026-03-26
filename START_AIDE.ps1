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

function Get-WorkingPython {
    $candidates = @(
        @{ Label = ".venv312"; Path = ".venv312\Scripts\python.exe" },
        @{ Label = ".venv"; Path = ".venv\Scripts\python.exe" },
        @{ Label = "system"; Path = "python" }
    )

    foreach ($candidate in $candidates) {
        try {
            & $candidate.Path -c "import sys; print(sys.executable)" 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
    }

    throw "No working Python interpreter found."
}

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

# Select a working Python interpreter.
Write-Host "[2/3] Setting up environment..." -ForegroundColor Yellow
try {
    $python = Get-WorkingPython
    if ($python.Label -eq "system") {
        Write-Host "[INFO] No working venv found, using system Python." -ForegroundColor DarkYellow
    } else {
        Write-Host "[OK] Using Python from $($python.Label)" -ForegroundColor Green
    }
} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    exit 1
}

# Install deps if needed
try {
    & $python.Path -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "missing" }
} catch {
    Write-Host "[SETUP] Installing requirements..." -ForegroundColor Yellow
    & $python.Path -m pip install -r requirements.txt
}

# Kill stale port
Write-Host "[3/3] Starting server..." -ForegroundColor Yellow
$stale = netstat -aon 2>$null | Select-String ":9000" | Select-String "LISTENING"
if ($stale) {
    $stale | ForEach-Object {
        $parts = ($_ -split "\s+") | Where-Object { $_ }
        $pid = $parts[-1]
        if ($pid -match "^\d+$") {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "[OK] Cleared stale process on port 9000." -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  AIDE v5 running at: " -NoNewLine -ForegroundColor Cyan
Write-Host "http://localhost:9000/app/" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

& $python.Path -m uvicorn backend.app.main:app --host 0.0.0.0 --port 9000
