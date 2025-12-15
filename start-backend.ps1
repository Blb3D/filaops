# FilaOps Backend Startup Script
# Starts only the backend API server

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FilaOps Backend - Starting" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Set database to FilaOps
# $env:DB_NAME = "FilaOps"  # Now read from .env
Write-Host "[CONFIG] Database: Reading from .env" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "backend" -PathType Container)) {
    Write-Host "[ERROR] Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists (optional)
if (Test-Path "backend\venv") {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
    & "backend\venv\Scripts\Activate.ps1"
}

# Start backend
Write-Host "`n[BACKEND] Starting FastAPI server..." -ForegroundColor Yellow
Write-Host "API will be available at: http://localhost:8000" -ForegroundColor White
Write-Host "API Docs at: http://localhost:8000/docs" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

Set-Location backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

