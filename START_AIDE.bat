@echo off
title AIDE v5 Launcher
color 0A

echo ============================================
echo         AIDE v5 - Alloy Design Engine
echo ============================================
echo.

REM Check internet connectivity
echo [1/3] Checking internet connection...
ping -n 1 -w 2000 8.8.8.8 >nul 2>&1
if errorlevel 1 (
    echo [WARNING] No internet connection detected.
    echo     The system will run but LLM features may be unavailable.
    echo.
) else (
    echo [OK] Internet connected.
)

REM Navigate to project directory
cd /d "%~dp0"

REM Check if venv exists and activate
echo [2/3] Setting up environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated (.venv)
) else if exist ".venv312\Scripts\activate.bat" (
    call .venv312\Scripts\activate.bat
    echo [OK] Virtual environment activated (.venv312)
) else (
    echo [INFO] No virtual environment found, using system Python.
)

REM Check if uvicorn is installed
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Installing requirements...
    pip install -r requirements.txt
)

REM Kill any existing process on port 9000
echo [3/3] Starting AIDE v5 server on http://localhost:9000 ...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :9000 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo ============================================
echo   AIDE v5 is starting...
echo   Open your browser to: http://localhost:9000/app/
echo   Press Ctrl+C to stop the server.
echo ============================================
echo.

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 9000 --reload

pause
