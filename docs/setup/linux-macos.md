# FilaOps — Zero-to-Running (macOS, Linux, SSH)

This guide gets a brand-new developer from **nothing installed** → **backend running** → **frontend UI running** — so they can *click around like a human*, not just hit APIs.

- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Frontend UI (typical):
  - Vite: `http://localhost:5173`
  - Next.js / CRA: `http://localhost:3000`

> If you’re on Windows, use the Windows guide. This doc is for **macOS + Linux + SSH**.

---

## Quick start (you can copy/paste)

**Local dev (macOS/Linux):**
1) Install prerequisites (Python 3.11, Postgres 16+, Node 18+, git)
2) Start Postgres + create DB
3) Clone repo
4) Create `.env` in repo root
5) Backend: venv → deps → migrate → run
6) Frontend: npm install → run dev server

---

# macOS (Intel / Apple Silicon) — Quickstart

## 1) Install prerequisites (Homebrew)

Install Homebrew (one-time):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install packages:
```bash
brew update
brew install python@3.11 postgresql@16 node@18 git
```

Sanity:
```bash
python3.11 --version
psql --version
node -v
npm -v
git --version
```

---

## 2) Start Postgres (Homebrew service) + create DB

Start Postgres:
```bash
brew services start postgresql@16
```

Create the DB (safe to run multiple times):
```bash
createdb filaops 2>/dev/null || true
```

**Tip (macOS + Homebrew Postgres):**
- Your DB user is usually your **macOS username** (`$USER`)
- Password is often **empty** by default

Confirm you can connect:
```bash
psql -d filaops -c "select version();"
```

---

## 3) Clone the repo

```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops
```

---

## 4) Create `.env` (repo root)

```bash
cat > .env <<'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filaops
DB_USER=$USER
DB_PASSWORD=
ENVIRONMENT=production
DEBUG=false
EOF
```

Quick check:
```bash
cat .env
```

---

## 5) Backend: venv + deps + migrate + run

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate

python -m pip install -U pip

# Install dependencies from requirements file
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify in a **new terminal**:
```bash
curl -fsS http://127.0.0.1:8000/health && echo
```

---

## 6) Frontend: install + run

Open a **new terminal**:

```bash
cd filaops/frontend
node -v && npm -v
[ -f package-lock.json ] && npm ci || npm install
npm run dev || npm start
```

> **Note:** If you cloned to a different location, adjust the path accordingly (e.g., `cd ~/projects/filaops/frontend`).

Open:
- Vite: `http://localhost:5173`
- Next/CRA: `http://localhost:3000`

---

# Ubuntu / Debian — Quickstart

## 1) Install prerequisites

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip   postgresql postgresql-contrib   nodejs npm git curl
```

(Optional: better Node 18+ via NodeSource)
```bash
# curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
# sudo apt install -y nodejs
```

Sanity:
```bash
python3.11 --version
psql --version
node -v
npm -v
git --version
```

---

## 2) Create DB role + DB

Make sure your UNIX user exists as a Postgres superuser (safe to re-run):
```bash
sudo -u postgres createuser -s "$USER" 2>/dev/null || true
```

Create DB:
```bash
createdb filaops 2>/dev/null || true
```

Confirm connection:
```bash
psql -d filaops -c "select current_user, current_database();"
```

---

## 3) Clone the repo

```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops
```

---

## 4) Create `.env` (repo root)

```bash
cat > .env <<EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filaops
DB_USER=$USER
DB_PASSWORD=
ENVIRONMENT=production
DEBUG=false
EOF
```

---

## 5) Backend: venv + deps + migrate + run

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate

python -m pip install -U pip

# Install dependencies from requirements file
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check (new terminal):
```bash
curl -fsS http://127.0.0.1:8000/health && echo
```

---

## 6) Frontend: install + run

```bash
cd filaops/frontend
[ -f package-lock.json ] && npm ci || npm install
npm run dev || npm start
```

> **Note:** If you cloned to a different location, adjust the path accordingly.

Open:
- Vite: `http://localhost:5173`
- Next/CRA: `http://localhost:3000`

---

# Generic Linux (Fedora / RHEL / Arch…) — Cliff Notes

1) Install:
- Python **3.11** + venv
- Postgres **16+**
- Node **18+**
- git

2) Create a Postgres role matching your UNIX user + create DB:
- Create role (superuser) for `$USER`
- `createdb filaops`

3) Follow the Ubuntu steps from **Clone the repo** onward.

---

# Remote server (SSH) — Minimal “first run”

This is the “get it running” path. For a real deployment, see the production note at the bottom.

## 1) SSH in

```bash
ssh youruser@your.server.ip
```

## 2) Install system packages (Ubuntu example)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip   postgresql postgresql-contrib   git curl
```

> If you want the frontend dev server on the server too, also install Node 18+:
> ```bash
> sudo apt install -y nodejs npm
> ```

## 3) Clone & create `.env`

```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops

cat > .env <<EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=filaops
DB_USER=$USER
DB_PASSWORD=
ENVIRONMENT=production
DEBUG=false
EOF
```

## 4) DB + backend setup

```bash
sudo -u postgres createuser -s "$USER" 2>/dev/null || true
createdb filaops 2>/dev/null || true

cd backend
python3.11 -m venv venv
source venv/bin/activate
python -m pip install -U pip

# Install dependencies from requirements file
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

## 5) Keep it running (tmux)

```bash
sudo apt install -y tmux
tmux new -s filaops
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Detach: `Ctrl+B` then `D`  
Reattach later:
```bash
tmux attach -t filaops
```

## 6) Open firewall (if needed)

UFW example:
```bash
sudo ufw allow 8000/tcp
```

### Accessing it from your laptop

If you’re running the **frontend locally** but backend remotely, you usually need:
- Backend reachable: `http://SERVER_IP:8000`
- Frontend configured to call that (often an env like `VITE_API_URL` / `VITE_API_BASE_URL` / `NEXT_PUBLIC_API_URL`)

Simple smoke test from your laptop:
```bash
curl -fsS http://SERVER_IP:8000/health
```

---

# Optional Unix scripts (repo root)

If you want the same “one-liners” as Windows PowerShell users, add these files at the repo root.

## `install-frontend.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[frontend] Installing frontend deps..."

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/frontend"
if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "[frontend] 'frontend' folder not found. Skipping."
  exit 0
fi

command -v node >/dev/null 2>&1 || { echo "[frontend] Node.js not found (need Node 18+)."; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "[frontend] npm not found."; exit 1; }

pushd "$FRONTEND_DIR" >/dev/null
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
popd >/dev/null

echo "[frontend] Done."
```

## `start-frontend.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[frontend] Starting dev server..."

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/frontend"
if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "[frontend] 'frontend' folder not found."
  exit 1
fi

command -v node >/dev/null 2>&1 || { echo "[frontend] Node.js not found (need Node 18+)."; exit 1; }
command -v npm  >/dev/null 2>&1 || { echo "[frontend] npm not found."; exit 1; }

# Check if node_modules exists, if not install dependencies
if [[ ! -d "$FRONTEND_DIR/node_modules" ]] || [[ ! -f "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
  echo "[frontend] Dependencies missing or incomplete. Installing..."
  pushd "$FRONTEND_DIR" >/dev/null
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
  popd >/dev/null
fi

pushd "$FRONTEND_DIR" >/dev/null

echo
echo "[frontend] If Vite:     http://localhost:5173"
echo "[frontend] If Next/CRA: http://localhost:3000"
echo

# prefer dev, fall back to start
if node -e "process.exit(require('./package.json').scripts?.dev ? 0 : 1)"; then
  npm run dev
else
  npm start
fi
```

## `start-backend.sh` (simple version)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[backend] Starting backend on http://localhost:8000"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

if [[ ! -d venv ]]; then
  echo "[backend] venv not found. Create it first:"
  echo "         python3.11 -m venv venv && source venv/bin/activate && pip install -U pip && pip install -r requirements.txt"
  echo "         Then run: alembic upgrade head"
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## `start-all.sh` (opens backend + frontend in separate terminals if possible)

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v open >/dev/null 2>&1; then
  # macOS Terminal
  open -a Terminal "$ROOT_DIR/start-backend.sh"
  open -a Terminal "$ROOT_DIR/start-frontend.sh"
  echo "[start-all] Launched in Terminal."
elif command -v gnome-terminal >/dev/null 2>&1; then
  gnome-terminal -- bash -lc "$ROOT_DIR/start-backend.sh; exec bash"
  gnome-terminal -- bash -lc "$ROOT_DIR/start-frontend.sh; exec bash"
  echo "[start-all] Launched in gnome-terminal."
else
  echo "[start-all] Couldn't auto-open terminals."
  echo "Run these in two terminals:"
  echo "  $ROOT_DIR/start-backend.sh"
  echo "  $ROOT_DIR/start-frontend.sh"
fi
```

Make scripts executable:
```bash
chmod +x install-frontend.sh start-frontend.sh start-backend.sh start-all.sh
```

---

# Common gotchas (fast answers)

## `psycopg` / Postgres build errors
We use:
- `psycopg[binary]>=3.1` (psycopg3 - most painless across platforms)
- If you encounter issues, you can also try `psycopg2-binary` as an alternative

## `alembic upgrade head` fails
- Ensure you’re in `backend/`
- Ensure venv is activated (you should see `(venv)` in prompt)
- Confirm DB connection works:
  ```bash
  psql -d filaops -c "select 1;"
  ```

## Port already in use
Run on a different port:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## Frontend can't reach backend
- If both are on the same machine, frontend should call `http://localhost:8000`
- If frontend is on your laptop but backend is remote, update frontend env to call `http://SERVER_IP:8000` and open firewall (`ufw allow 8000/tcp`)

---

# Production note (when you’re past first-run)

For real deployments, prefer:
- `systemd` service for Uvicorn (or gunicorn+uvicorn workers)
- Nginx reverse proxy with TLS
- DB user/password not empty + least privilege
- Optional: build frontend and serve static assets from Nginx

For **first impressions**, the quickstart above is meant to be the fastest path to “it’s working.”
