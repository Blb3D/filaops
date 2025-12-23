# start-backend.ps1 (PowerShell 5+)
$ErrorActionPreference = "Stop"

Write-Host "[backend] Starting FilaOps Backend..." -ForegroundColor Cyan

# Get the script directory (repo root)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptRoot "backend"

if (-not (Test-Path $backendDir)) {
    Write-Host "[backend] 'backend' folder not found." -ForegroundColor Red
    exit 1
}

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[backend] Python not found on PATH." -ForegroundColor Red
    Write-Host "          Install Python 3.11+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check for virtual environment
$venvPath = Join-Path $backendDir "venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Host "[backend] Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "          Creating virtual environment..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[backend] Failed to create virtual environment." -ForegroundColor Red
            Pop-Location
            exit 1
        }
        Write-Host "[backend] Virtual environment created." -ForegroundColor Green
    }
    catch {
        Write-Host "[backend] Error creating venv: $_" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
}

# Check if dependencies are installed
$requirementsPath = Join-Path $backendDir "requirements.txt"
$pipPath = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $requirementsPath)) {
    Write-Host "[backend] requirements.txt not found." -ForegroundColor Red
    exit 1
}

# Quick check if FastAPI is installed
$fastApiCheck = & $pipPath show fastapi 2>$null
if (-not $fastApiCheck) {
    Write-Host "[backend] Dependencies not installed. Installing..." -ForegroundColor Yellow
    Push-Location $backendDir
    try {
        & $venvActivate
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[backend] Failed to install dependencies." -ForegroundColor Red
            Pop-Location
            exit 1
        }
        Write-Host "[backend] Dependencies installed." -ForegroundColor Green
    }
    catch {
        Write-Host "[backend] Error installing dependencies: $_" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
}

# Start the backend server
Push-Location $backendDir
try {
    Write-Host "`n[backend] Starting server at: http://localhost:8001" -ForegroundColor Green
    Write-Host "[backend] API docs at: http://localhost:8001/docs" -ForegroundColor Green
    Write-Host "[backend] Press Ctrl+C to stop`n" -ForegroundColor Yellow
    
    # Activate venv and start uvicorn
    & $venvActivate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[backend] Server stopped with exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "[backend] Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}
catch {
    Write-Host "`n[backend] Error: $_" -ForegroundColor Red
    Write-Host "[backend] Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
finally {
    Pop-Location
}


