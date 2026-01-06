# FilaOps v2 - Fresh Install Guide

**Start from nothing, get running in 30 minutes.**

This guide assumes you have a clean Windows machine with nothing installed. Linux/Mac users: steps are similar, just adjust paths and use your package manager for installs.

---

## Step 1: Install Prerequisites

### 1.1 Install Git

**Download:** https://git-scm.com/download/win

Run the installer with default options. When done, you should be able to open PowerShell and run:
```powershell
git --version
# Should show: git version 2.x.x
```

### 1.2 Install Python 3.10+

**Download:** https://www.python.org/downloads/

⚠️ **Important:** During install, check **"Add Python to PATH"**

Verify:
```powershell
python --version
# Should show: Python 3.10.x or higher
```

### 1.3 Install Node.js 18+

**Download:** https://nodejs.org/ (LTS version)

Run installer with defaults.

Verify:
```powershell
node --version
# Should show: v18.x.x or higher

npm --version
# Should show: 9.x.x or higher
```

### 1.4 Install PostgreSQL 15+

**Download:** https://www.postgresql.org/download/windows/

Run the installer:
1. Choose install location (default is fine)
2. Select components: PostgreSQL Server, pgAdmin 4, Command Line Tools
3. Set data directory (default is fine)
4. **Set password for postgres user** — remember this!
5. Port: 5432 (default)
6. Locale: default

Verify it's running:
```powershell
psql -U postgres -c "SELECT version();"
# Enter your password when prompted
# Should show PostgreSQL version info
```

**Troubleshooting:** If `psql` is not found, add PostgreSQL to your PATH:
```powershell
# Add to PATH (adjust version number if different)
$env:PATH += ";C:\Program Files\PostgreSQL\15\bin"
```

---

## Step 2: Clone FilaOps

```powershell
# Navigate to where you want the project
cd C:\repos

# Clone the repository
git clone https://github.com/Blb3D/filaops.git

# Enter the directory
cd filaops
```

---

## Step 3: Create the Database

Open pgAdmin 4 (installed with PostgreSQL) or use command line:

```powershell
# Create the database
psql -U postgres -c "CREATE DATABASE filaops;"

# Create a dedicated user (optional but recommended)
psql -U postgres -c "CREATE USER filaops WITH PASSWORD 'filaops';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE filaops TO filaops;"
```

---

## Step 4: Set Up Backend

### 4.1 Create Virtual Environment

```powershell
cd C:\repos\filaops\backend

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate

# You should see (venv) in your prompt now
```

### 4.2 Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4.3 Configure Environment

```powershell
# Copy the example environment file
copy .env.example .env

# Edit the .env file
notepad .env
```

**Update these values in `.env`:**
```env
# Database connection - THIS IS THE IMPORTANT ONE
DATABASE_URL=postgresql://filaops:filaops@localhost:5432/filaops

# Or if using the postgres user directly:
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/filaops
```

### 4.4 Initialize Database Tables

```powershell
# Make sure venv is still activated
# Run database migrations
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, initial tables
INFO  [alembic.runtime.migration] Running upgrade abc123 -> def456, add materials
...
```

### 4.5 Load Test Data (Optional)

```powershell
python load_test_data.py
```

### 4.6 Start the Backend

```powershell
python run.py
```

You should see:
```
* Running on http://0.0.0.0:5000
```

**Test it:** Open browser to http://localhost:5000/health

Should show: `{"status": "healthy", "version": "2.0.0"}`

✅ **Backend is running!** Keep this terminal open.

---

## Step 5: Set Up Frontend

**Open a NEW terminal** (keep backend running in the other one)

```powershell
cd C:\repos\filaops\frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

You should see:
```
  VITE v4.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Open browser:** http://localhost:5173

✅ **FilaOps is running!**

---

## Step 6: Verify Everything Works

1. **Check backend health:** http://localhost:5000/health
2. **Open the app:** http://localhost:5173
3. **Navigate around** — you should see the dashboard, inventory, etc.

If you ran `load_test_data.py`, you should see sample materials in the Inventory section.

---

## Common Issues

### "psql is not recognized"
Add PostgreSQL to your PATH:
```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\15\bin"
```
Or search "Environment Variables" in Windows, edit PATH, add the PostgreSQL bin folder.

### "connection refused" on database
- Make sure PostgreSQL service is running (check Windows Services)
- Verify your DATABASE_URL in `.env` has correct password
- Try connecting manually: `psql -U postgres -d filaops`

### "alembic: command not found"
Make sure your virtual environment is activated:
```powershell
.\venv\Scripts\Activate
```

### "Module not found" errors in Python
```powershell
# Make sure you're in backend folder with venv activated
pip install -r requirements.txt
```

### Frontend shows "Network Error" or blank page
- Make sure backend is running on port 5000
- Check browser console (F12) for specific errors
- Verify backend health endpoint works

### "Port already in use"
Something else is using port 5000 or 5173:
```powershell
# Find what's using the port
netstat -ano | findstr :5000

# Kill it (replace PID with the number from above)
taskkill /PID <PID> /F
```

---

## Daily Startup

Once installed, here's your daily routine:

**Terminal 1 - Backend:**
```powershell
cd C:\repos\filaops\backend
.\venv\Scripts\Activate
python run.py
```

**Terminal 2 - Frontend:**
```powershell
cd C:\repos\filaops\frontend
npm run dev
```

Open: http://localhost:5173

---

## Next Steps

- **Configure Printers:** See [BAMBU_SETUP_GUIDE.md](BAMBU_SETUP_GUIDE.md)
- **Having Issues?** Check [GitHub Issues](https://github.com/Blb3D/filaops/issues)

---

## Getting Help

- **GitHub Issues:** Report bugs or ask questions
- **Discussions:** Community help and feature requests

Welcome to FilaOps! 🚀
