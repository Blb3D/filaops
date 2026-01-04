# FilaOps — Zero-to-Running (Windows)

This guide gets a brand‑new Windows machine from **nothing** to a **working FilaOps UI + API** with the fewest “gotchas”.
It assumes **PowerShell 5** (built into Windows), but works in PowerShell 7 too.

**You’ll know you’re done when:**
- Backend health check returns: `{"status":"healthy"}`
- Frontend opens in your browser and can talk to the API

---

## Quick start (copy/paste)

> **Tip:** Always run these from the **repo root**: `C:\repos\filaops`

```powershell
cd C:\repos
git clone https://github.com/Blb3D/filaops.git
cd .\filaops

Set-ExecutionPolicy -Scope Process Bypass -Force
.\install.ps1
.\install-frontend.ps1

.\start-all.ps1
```

- Backend: http://localhost:8000/health
- API docs: http://localhost:8000/docs  
- Frontend (most common): http://localhost:5173 (Vite) or http://localhost:3000 (Next/CRA)

---

## 1) Prerequisites (install once)

Install these system‑wide **one time**:

1) **Git**  
   Download + install (defaults are fine): https://git-scm.com/download/win

2) **Python 3.11 (64‑bit)**  
   Download + install: https://www.python.org/downloads/release/python-3119/  
   ✅ During install, check **“Add Python to PATH”**.

3) **PostgreSQL 16 or 17**  
   Download + install: https://www.postgresql.org/download/windows/  
   - Keep defaults
   - Note the **superuser** (`postgres`) and the **password** you choose
   - Make sure the Postgres service is running after install

4) **Node.js 18+ (for the frontend UI)**  
   Download: https://nodejs.org/en/download  
   Or with winget:
   ```powershell
   winget install OpenJS.NodeJS.LTS
   ```

---

## 2) Clone the repo

```powershell
cd C:\repos
git clone https://github.com/Blb3D/filaops.git
cd .\filaops
```

Already cloned? Update it:
```powershell
git pull
```

---

## 3) Configure environment (one time)

Create a minimal `.env` in the repo root:

```powershell
@'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filaops
DB_USER=postgres
DB_PASSWORD=Admin
ENVIRONMENT=production
DEBUG=false
# Optional: set true only if you plan to connect Google Drive
ENABLE_GOOGLE_DRIVE=false
'@ | Set-Content -Encoding UTF8 .\.env
```

> If your Postgres password isn’t `Admin`, replace it in `DB_PASSWORD`.

**Sanity check (optional):** confirm the file exists
```powershell
Get-Content .\.env
```

---

## 4) Install & initialize the backend (one command)

This script:
- creates a private Python virtual environment in `backend\venv\`
- installs backend dependencies
- runs DB migrations (`alembic upgrade head`)

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\install.ps1
```

**Success looks like:**
- venv created at `backend\venv\`
- migration output ends without errors

---

## 5) Start the backend API

From the **repo root**:

```powershell
.\start-backend.ps1
```

Backend runs at:
- http://localhost:8000

**Health check**
- Open in browser: http://localhost:8000/health  
  Expect:
```json
{"status":"healthy"}
```

**API docs**
- http://localhost:8000/docs

---

## 6) First-run admin setup

If the logs mention first‑run setup, open:

- http://localhost:8000/api/v1/auth/setup

Create the initial admin user.

> If your build exposes a UI route like `/setup`, use that UI instead.

---

## 7) Install the frontend UI (one time per clone)

From the **repo root**:

```powershell
.\install-frontend.ps1
```

This installs Node dependencies inside `frontend\`.

> **Note:** `start-frontend.ps1` will automatically install dependencies if they're missing, so this step is optional. However, running `install-frontend.ps1` first ensures everything is ready before starting.

---

## 8) Start the frontend UI

From the **repo root**:

```powershell
.\start-frontend.ps1
```

The script will automatically check for and install dependencies if needed, then start the dev server.

Then open the URL printed by the dev server. Common defaults:
- Vite: http://localhost:5173
- Next.js / CRA: http://localhost:3000

**If the UI loads but can't reach the API**, jump to **Troubleshooting → Frontend can't talk to backend**.

---

## 9) One command to launch everything

If you want two windows (backend + frontend):

```powershell
.\start-all.ps1
```

---

## Everyday workflow

From the repo root:

- Start everything:
  ```powershell
  .\start-all.ps1
  ```
- Start only backend:
  ```powershell
  .\start-backend.ps1
  ```
- Start only frontend:
  ```powershell
  .\start-frontend.ps1
  ```
- Stop: press **Ctrl + C** in the window that’s running the server.

---

## Optional: Verify script (preflight + DB ping + start)

```powershell
cd C:\repos\filaops\backend
pwsh -NoProfile -ExecutionPolicy Bypass -File .\verify.ps1
```

This:
- activates the venv
- checks critical imports
- pings the DB
- starts Uvicorn on :8000

---

## Optional: Google Drive integration

Disabled by default. To enable later:

1) Install Google libs into the venv:
```powershell
.\backend\venv\Scripts\pip.exe install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib
```

2) In `.env`:
```
ENABLE_GOOGLE_DRIVE=true
```

3) Restart backend.

---

# Scripts to add (repo root)

If these scripts already exist in your repo, you can skip this section.  
If not, create these files at the repo root.

## `install-frontend.ps1`

```powershell
# install-frontend.ps1 (PowerShell 5+)
$ErrorActionPreference = "Stop"

Write-Host "[frontend] Installing frontend deps..." -ForegroundColor Cyan

# 1) sanity checks
$frontendDir = Join-Path $PSScriptRoot "frontend"
if (-not (Test-Path $frontendDir)) {
  Write-Host "[frontend] 'frontend' folder not found. Skipping." -ForegroundColor Yellow
  exit 0
}

# 2) ensure Node is available
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
  Write-Host "[frontend] Node.js not found on PATH." -ForegroundColor Yellow
  Write-Host "          Please install Node 18+ from https://nodejs.org/en/download" -ForegroundColor Yellow
  Write-Host "          (Or install with winget: winget install OpenJS.NodeJS.LTS)" -ForegroundColor Yellow
  exit 1
}

# 3) install
Push-Location $frontendDir
try {
  if (Test-Path "package-lock.json") {
    npm ci
  } else {
    npm install
  }
  Write-Host "[frontend] Dependencies installed." -ForegroundColor Green
} finally {
  Pop-Location
}
```

## `start-frontend.ps1`

```powershell
# start-frontend.ps1 (PowerShell 5+)
$ErrorActionPreference = "Stop"

Write-Host "[frontend] Starting dev server..." -ForegroundColor Cyan

# Get the script directory (repo root) - works when called directly or from another script
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $scriptRoot "frontend"
if (-not (Test-Path $frontendDir)) {
    Write-Host "[frontend] 'frontend' folder not found." -ForegroundColor Red
    exit 1
}

# ensure Node is available
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[frontend] Node.js not found on PATH." -ForegroundColor Red
    Write-Host "          Install Node 18+ from https://nodejs.org/en/download" -ForegroundColor Yellow
    exit 1
}

# figure out which script to run
$pkgPath = Join-Path $frontendDir "package.json"
if (-not (Test-Path $pkgPath)) {
    Write-Host "[frontend] package.json not found." -ForegroundColor Red
    exit 1
}

$pkg = Get-Content $pkgPath -Raw | ConvertFrom-Json
$scriptToRun = $null
if ($pkg.scripts.dev) { $scriptToRun = "dev" }
elseif ($pkg.scripts.start) { $scriptToRun = "start" }
elseif ($pkg.scripts."serve") { $scriptToRun = "serve" }

if (-not $scriptToRun) {
    Write-Host "[frontend] Could not find a dev/start script in package.json." -ForegroundColor Red
    Write-Host "          Define one under 'scripts' (e.g. \"dev\": \"vite\" or \"next dev\")." -ForegroundColor Yellow
    exit 1
}

# Check if node_modules exists and has the required binaries
$nodeModulesPath = Join-Path $frontendDir "node_modules"
$viteBinPath = Join-Path $frontendDir "node_modules\.bin\vite.cmd"
$needsInstall = $false

if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "[frontend] node_modules not found." -ForegroundColor Yellow
    $needsInstall = $true
} elseif (-not (Test-Path $viteBinPath)) {
    Write-Host "[frontend] Dependencies appear incomplete (vite not found in node_modules\.bin\)." -ForegroundColor Yellow
    $needsInstall = $true
}

if ($needsInstall) {
    Write-Host "[frontend] Installing dependencies..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try {
        if (Test-Path "package-lock.json") {
            npm ci
        }
        else {
            npm install
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[frontend] Failed to install dependencies. Exit code: $LASTEXITCODE" -ForegroundColor Red
            Pop-Location
            Write-Host "[frontend] Press any key to exit..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            exit 1
        }
        Write-Host "[frontend] Dependencies installed." -ForegroundColor Green
    }
    catch {
        Write-Host "[frontend] Failed to install dependencies. Error: $_" -ForegroundColor Red
        Pop-Location
        Write-Host "[frontend] Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
    Pop-Location
}

Push-Location $frontendDir
try {
    # helpful hint about common ports
    Write-Host "`n[frontend] If this is Vite: http://localhost:5173" -ForegroundColor DarkGray
    Write-Host "[frontend] If this is Next.js: http://localhost:3000" -ForegroundColor DarkGray
    Write-Host "[frontend] If this is CRA: http://localhost:3000`n" -ForegroundColor DarkGray

    # run it in the current console so logs stream visibly
    npm run $scriptToRun
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[frontend] Error: npm run $scriptToRun failed with exit code $LASTEXITCODE" -ForegroundColor Red
        Write-Host "[frontend] Make sure dependencies are installed. Try running: .\install-frontend.ps1" -ForegroundColor Yellow
        Write-Host "[frontend] Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}
catch {
    Write-Host "`n[frontend] Error: $_" -ForegroundColor Red
    Write-Host "[frontend] Make sure dependencies are installed. Try running: .\install-frontend.ps1" -ForegroundColor Yellow
    Write-Host "[frontend] Press any key to exit..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
finally {
    Pop-Location
}
```

## `start-all.ps1` (optional)

```powershell
# start-all.ps1 (PowerShell 5+)
$ErrorActionPreference = "Stop"

# Get the script directory (repo root)
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# backend window
$backendScript = Join-Path $scriptRoot "start-backend.ps1"
if (-not (Test-Path $backendScript)) {
  Write-Host "[start-all] start-backend.ps1 not found." -ForegroundColor Red
  exit 1
}
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-File","`"$backendScript`""

# frontend window
$frontendScript = Join-Path $scriptRoot "start-frontend.ps1"
if (Test-Path $frontendScript) {
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-File","`"$frontendScript`""
} else {
  Write-Host "[start-all] start-frontend.ps1 not found; skipping frontend." -ForegroundColor Yellow
}

Write-Host "`n[start-all] Launched backend and (if present) frontend in new windows." -ForegroundColor Green
Write-Host "[start-all] Backend will be at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "[start-all] Frontend will be at: http://localhost:5173" -ForegroundColor Cyan
```

---

# Troubleshooting (the stuff that makes people quit)

## “The term '..\venv\Scripts\python.exe' is not recognized…”
You’re running a script that expects a venv that doesn’t exist (or the path is wrong).

Fix:
1) Run from **repo root**
2) Rebuild the venv:
```powershell
cd C:\repos\filaops
.\install.ps1
```

If your repo uses `backend\venv\` (recommended), make sure your `start-backend.ps1` points there.

---

## PowerShell blocks scripts
Run this once per terminal window:
```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
```

---

## Postgres auth errors / migrations fail
Most common causes:
- Postgres service isn’t running
- wrong password in `.env`
- DB doesn’t exist yet

Fast reset (⚠️ wipes the DB):
```powershell
$env:PGPASSWORD="Admin"   # or your password
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS filaops WITH (FORCE)"
psql -h localhost -U postgres -c "CREATE DATABASE filaops"
cd C:\repos\filaops
.\install.ps1
```

If `psql` is missing, see **psql not found** below.

---

## Port 8000 already in use
Use a different port:
```powershell
.\start-backend.ps1 -Port 8010
```

---

## Node not found / frontend won’t install
Install Node 18+ and open a **new** PowerShell window (PATH refresh), then:
```powershell
cd C:\repos\filaops
.\install-frontend.ps1
```

---

## Frontend loads but can’t talk to the backend (CORS / wrong API URL)
Typical symptoms:
- UI shows network errors
- login/setup calls fail
- browser console shows CORS errors

What to do:
1) Confirm backend is healthy: http://localhost:8000/health
2) Check whether your frontend expects an env var like `VITE_API_URL`, `REACT_APP_API_URL`, or `NEXT_PUBLIC_API_URL`.
   - If it does, set it to `http://localhost:8000` in the frontend's `.env.local` / `.env` file.
3) Restart the frontend dev server.

---

## `psql` not found
- Reopen PowerShell (PATH refresh), or add PostgreSQL `bin` folder to PATH.
- You can still run the app without `psql` if migrations are handled via `install.ps1`.

---

## What’s installed where?

- Backend venv: `backend\venv\`
- Backend code: `backend\app\`
- Migrations: `backend\migrations\`
- Frontend: `frontend\`
- Main scripts:
  - `install.ps1` – backend deps + migrations
  - `start-backend.ps1` – run API (`-Migrate` optional)
  - `install-frontend.ps1` – frontend deps
  - `start-frontend.ps1` – frontend dev server
  - `start-all.ps1` – two-window launcher

---

## Next steps

- Open API docs: http://localhost:8000/docs
- Use the UI to add products/materials/orders (once frontend is running)
- If anything in this doc doesn’t match what you see, copy/paste:
  - the exact command you ran, and
  - the last ~30 lines of console output

