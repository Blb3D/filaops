# FilaOps Installation Guide

> **For Print Farmers** - Basic command line knowledge helpful.
> Estimated time: 20-30 minutes

## What You'll Need

- A computer running Windows 10/11, macOS, or Linux
- 4GB+ RAM available
- 10GB+ free disk space
- Internet connection (for initial setup)
- Administrator/sudo access (for installing dependencies)

---

## Step 1: Install PostgreSQL

FilaOps uses PostgreSQL as its database engine.

### Windows

1. Download [PostgreSQL installer](https://www.postgresql.org/download/windows/) (version 14 or newer)
2. Run the installer
3. Follow the prompts:
   - Choose installation directory (default is fine)
   - Select components: PostgreSQL Server, pgAdmin, Command Line Tools
   - Set a **password for postgres user** (remember this!)
   - Port: 5432 (default)
   - Locale: Default locale
4. Complete the installation

### macOS

Using Homebrew (recommended):
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14
```

### Linux (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## Step 2: Install Python

FilaOps requires Python 3.9 or newer.

### Windows

1. Download [Python](https://www.python.org/downloads/) (3.9+)
2. Run the installer
3. **Important:** Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```powershell
   python --version
   ```

### macOS

```bash
# Using Homebrew
brew install python@3.11
```

### Linux (Ubuntu/Debian)

```bash
# Python 3.9+ usually pre-installed, verify:
python3 --version

# If needed:
sudo apt install python3 python3-pip python3-venv
```

---

## Step 3: Install Node.js

The FilaOps frontend requires Node.js 18 or newer.

### All Platforms

1. Download [Node.js LTS](https://nodejs.org/) (18+)
2. Run the installer (accept defaults)
3. Verify installation:
   ```bash
   node --version
   npm --version
   ```

---

## Step 4: Download FilaOps

### Option A: Download ZIP (Easiest)

1. Go to [FilaOps Releases](https://github.com/blb3dprinting/filaops/releases)
2. Download the latest `Source code (zip)`
3. Extract to a folder (e.g., `C:\FilaOps` or `~/filaops`)

### Option B: Git Clone

```bash
git clone https://github.com/blb3dprinting/filaops.git
cd filaops
```

---

## Step 5: Create Database

Open a terminal/command prompt and create the FilaOps database:

### Windows (Command Prompt as Administrator)

```cmd
psql -U postgres
```
Enter your postgres password, then:
```sql
CREATE DATABASE filaops;
CREATE USER filaops_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE filaops TO filaops_user;
\q
```

### macOS/Linux

```bash
sudo -u postgres psql
```
Then:
```sql
CREATE DATABASE filaops;
CREATE USER filaops_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE filaops TO filaops_user;
\q
```

---

## Step 6: Configure FilaOps

1. Navigate to the FilaOps folder:
   ```bash
   cd C:\FilaOps  # Windows
   cd ~/filaops   # Mac/Linux
   ```

2. Copy the example configuration:
   - Windows: `copy backend\.env.example backend\.env`
   - Mac/Linux: `cp backend/.env.example backend/.env`

3. Edit `backend/.env` and update:
   ```bash
   # Database connection
   DATABASE_URL=postgresql://filaops_user:your_secure_password_here@localhost:5432/filaops

   # Security (generate with: openssl rand -hex 32)
   SECRET_KEY=your_generated_secret_key_here

   # CORS origins (add your network IP if accessing remotely)
   CORS_ORIGINS=["http://localhost:5173","http://localhost:5174"]
   ```

---

## Step 7: Install Backend Dependencies

### Windows (PowerShell)

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

### macOS/Linux

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

---

## Step 8: Install Frontend Dependencies

Open a **new terminal** (keep backend terminal open):

```bash
cd frontend
npm install
```

---

## Step 9: Start FilaOps

You'll need **two terminals running** - one for backend, one for frontend.

### Terminal 1: Backend

```bash
cd backend
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\activate   # Windows

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

---

## Step 10: Access FilaOps

1. Open your browser
2. Go to: **http://localhost:5174**
3. You should see the FilaOps **Setup Wizard**!

### First-Time Setup

On a fresh install, you'll see the Setup Wizard:

1. Enter your **email address** (this becomes your admin login)
2. Enter your **full name**
3. Set a **strong password** (min 8 chars, upper/lower/number/special)
4. Click **Create Admin Account**

You'll be logged in automatically and can start using FilaOps!

> **Note:** If you see the login screen instead of the setup wizard, your database may have existing data. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#stuck-at-login-screen) for help.

---

## Production Deployment (Optional)

For production use, you'll want to run FilaOps as a system service instead of in terminal windows.

### Backend Service (systemd on Linux)

Create `/etc/systemd/system/filaops-backend.service`:
```ini
[Unit]
Description=FilaOps Backend
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/filaops/backend
Environment="PATH=/opt/filaops/backend/venv/bin"
ExecStart=/opt/filaops/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable filaops-backend
sudo systemctl start filaops-backend
```

### Frontend Service (PM2 on all platforms)

Install PM2:
```bash
npm install -g pm2
```

Build and serve frontend:
```bash
cd frontend
npm run build
pm2 serve dist 5173 --name filaops-frontend --spa
pm2 save
pm2 startup  # Follow the instructions to enable on boot
```

### Backend Service (Windows)

Use NSSM (Non-Sucking Service Manager):
1. Download [NSSM](https://nssm.cc/download)
2. Install service:
   ```cmd
   nssm install FilaOpsBackend "C:\FilaOps\backend\venv\Scripts\python.exe" "-m" "uvicorn" "app.main:app" "--host" "0.0.0.0" "--port" "8000"
   nssm set FilaOpsBackend AppDirectory "C:\FilaOps\backend"
   nssm start FilaOpsBackend
   ```

---

## Accessing from Other Computers (Network/Remote Access)

> **Important:** If you see "Failed to fetch" or "Connection Issue" when accessing FilaOps from another computer, follow these steps.

To access FilaOps from other machines on your network:

1. Find your server's IP address:
   - Windows: `ipconfig` (look for IPv4 Address, e.g., `192.168.1.100`)
   - Mac/Linux: `ip addr` or `ifconfig`

2. Update `backend/.env`:
   ```bash
   # Add your network IP to CORS origins
   CORS_ORIGINS=["http://localhost:5173","http://192.168.1.100:5173"]
   ```

3. Update `frontend/.env.local` (create if doesn't exist):
   ```bash
   # Example: If your server IP is 192.168.1.100
   VITE_API_URL=http://192.168.1.100:8000
   ```

4. **Rebuild frontend** (the URL is baked in at build time):
   ```bash
   cd frontend
   npm run build
   ```

5. Restart backend:
   ```bash
   cd backend
   # Stop with Ctrl+C, then restart:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Access from other computers at: `http://YOUR_IP_ADDRESS:5173`

### Why This Is Needed

The frontend is a static web app that needs to know where the API server is located. By default, it's configured for `localhost` which only works when accessing from the same machine. When you access from another computer, `localhost` refers to *that* computer, not your server.

Setting `VITE_API_URL` tells the frontend where to find the API server on your network.

---

## Common Commands

### Start FilaOps (Development)

Terminal 1:
```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:
```bash
cd frontend
npm run dev
```

### Stop FilaOps

Press `Ctrl+C` in each terminal.

### Update to Latest Version

```bash
# Stop FilaOps (Ctrl+C in both terminals)

# Pull latest code
git pull

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Update frontend
cd ../frontend
npm install

# Restart FilaOps (see "Start FilaOps" above)
```

### Reset Database (⚠️ deletes all data)

```bash
# Drop and recreate database
psql -U postgres
DROP DATABASE filaops;
CREATE DATABASE filaops;
GRANT ALL PRIVILEGES ON DATABASE filaops TO filaops_user;
\q

# Re-run migrations
cd backend
source venv/bin/activate
alembic upgrade head
```

---

## Troubleshooting

### "psql: command not found"
PostgreSQL binaries not in PATH. Add to PATH:
- Windows: `C:\Program Files\PostgreSQL\14\bin`
- macOS (Homebrew): Already in PATH
- Linux: Usually already in PATH

### "FATAL: password authentication failed"
Check your database password in `backend/.env` matches what you set during database creation.

### "Port 5174 already in use"
Another application is using that port. Either:
- Stop the other application, or
- Edit `frontend/vite.config.ts` and change the port number

### "Database connection failed"
- Make sure PostgreSQL is running:
  - Windows: Check Services app
  - macOS: `brew services list`
  - Linux: `sudo systemctl status postgresql`
- Verify DATABASE_URL in `backend/.env`

### "Module not found" errors
Make sure you:
- Activated the virtual environment (backend)
- Ran `pip install -r requirements.txt` (backend)
- Ran `npm install` (frontend)

### Still stuck?

- [Open a GitHub Issue](https://github.com/Blb3D/filaops/issues)
- [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| Storage | 10GB | 20GB+ |
| CPU | 2 cores | 4+ cores |
| OS | Win 10, macOS 11, Ubuntu 20.04 | Latest versions |
| PostgreSQL | 12+ | 14+ |
| Python | 3.9+ | 3.11+ |
| Node.js | 18+ | 20+ |

---

## What's Next?

1. **Add your materials** - Inventory → Materials → Add Material
2. **Create your BOMs** - Products → Bill of Materials
3. **Enter a sales order** - Orders → New Order
4. **Run MRP** - Dashboard → Run MRP to see what you need to order

Need help? Check out the [User Guide](./docs/USER_GUIDE.md) or [Video Tutorials](https://youtube.com/@filaops).

---

*FilaOps - ERP for 3D Print Farms*
