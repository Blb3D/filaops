# Getting Started with FilaOps

This guide will walk you through setting up FilaOps step by step. No coding experience required.

**Time needed:** 
- **Docker method:** 10-15 minutes (recommended)
- **Manual method:** 30 minutes (for advanced users)

---

## 🚀 Quick Start (Docker - Recommended)

**Perfect for print farm owners!** No Python, Node.js, or database setup required.

### Step 1: Install Docker Desktop

**Windows:**
1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Run the installer and follow the prompts
3. **Restart your computer** when prompted
4. After restart, Docker Desktop should start automatically (whale icon in system tray)

**macOS:**
1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Open the downloaded `.dmg` file
3. Drag Docker to Applications folder
4. Open Docker from Applications and grant permissions

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then verify
docker --version
```

### Step 2: Download FilaOps

**Option A: Download ZIP (Easiest)**
1. Go to https://github.com/Blb3D/filaops
2. Click the green "Code" button → "Download ZIP"
3. Extract to a folder (e.g., `C:\FilaOps` or `~/filaops`)

**Option B: Git Clone**
```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops
```

### Step 3: Start FilaOps

Open a terminal/command prompt in the FilaOps folder:

**Windows (PowerShell or Command Prompt):**
```powershell
cd C:\FilaOps
docker-compose up -d
```

**Mac/Linux:**
```bash
cd ~/filaops
docker-compose up -d
```

**First startup takes 3-5 minutes** as Docker downloads and builds everything.

You'll see output like:
```
Creating filaops-db       ... done
Creating filaops-redis    ... done
Creating filaops-db-init  ... done
Creating filaops-backend  ... done
Creating filaops-frontend ... done
```

### Step 4: Access FilaOps

1. Open your browser
2. Go to: **http://localhost:5173**
3. You should see the FilaOps **Setup Wizard**!

**First-Time Setup:**

1. Enter your **email address** (this becomes your admin login)
2. Enter your **full name**
3. Set a **strong password** (min 8 chars, upper/lower/number/special)
4. Click **Create Admin Account**

You'll be logged in automatically!

> **Tip:** If you see the login screen instead of setup, your database may have existing data. Run `docker-compose down -v && docker-compose up -d` for a fresh start.

---

## Common Docker Commands

### Start FilaOps
```bash
docker-compose up -d
```

### Stop FilaOps
```bash
docker-compose down
```

### View Logs (troubleshooting)
```bash
docker-compose logs -f
```

### Update to Latest Version
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

---

## What's Next?

### Quick Tour of FilaOps

| Menu Item | What It Does |
|-----------|--------------|
| **Dashboard** | Overview of your operation |
| **Products** | Your catalog (filaments, finished goods, supplies) |
| **BOMs** | Bills of Materials - what goes into each product |
| **Orders** | Customer orders |
| **Production** | Manufacturing queue |
| **Inventory** | Stock levels |
| **Manufacturing** | Printers, work stations, routings |
| **Purchasing** | Vendor management, purchase orders |

### Recommended First Steps

1. **Complete onboarding** - Import your products, customers, and materials via CSV
2. **Add a filament** - Go to Products → Add Product (if not imported)
3. **Create a BOM** - Link your finished good to the filament it uses
4. **Create a test order** - See how the workflow works

For a detailed explanation of how everything connects, see **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**.

---

## Troubleshooting

### "Cannot connect to Docker daemon"
- Make sure Docker Desktop is running (whale icon in system tray)
- On Windows, try running PowerShell as Administrator

### "Port 5173 already in use"
Another application is using that port. Either:
- Stop the other application, or
- Edit `docker-compose.yml` and change `"5173:80"` to `"8080:80"`, then access at http://localhost:8080

### "Database connection failed"
- Wait 30 seconds and try again (database may still be starting)
- Check logs: `docker-compose logs db`

### "Container keeps restarting"
Check what's wrong:
```bash
docker-compose logs backend
```

### Still stuck?
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Detailed troubleshooting guide
- **[FAQ.md](FAQ.md)** - Common questions and answers
- [GitHub Issues](https://github.com/Blb3D/filaops/issues) - Report bugs
- [GitHub Discussions](https://github.com/Blb3D/filaops/discussions) - Ask questions

---

## 📖 Need More Details?

- **[INSTALL.md](INSTALL.md)** - Complete Docker installation guide with advanced options
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Detailed troubleshooting for common issues
- **[FAQ.md](FAQ.md)** - Frequently asked questions

---

## 🔧 Advanced Setup (Manual Installation)

If you prefer to install Python, Node.js, and SQL Server manually (or Docker isn't available), see the manual setup guide below.

<details>
<summary><strong>Click to expand manual setup instructions</strong></summary>

### What You'll Need

Before starting, you need to install these programs. Click each link to download.

#### 1. Python (the programming language)

**Download:** https://www.python.org/downloads/

When installing:
- **Check the box** that says "Add Python to PATH"
- Click "Install Now"

**To verify it worked:** Open Command Prompt and type:
```
python --version
```
You should see something like `Python 3.11.x` or `Python 3.12.x`

#### 2. Node.js (for the web interface)

**Download:** https://nodejs.org/ (choose the LTS version)

Just run the installer with default settings.

**To verify it worked:** Open Command Prompt and type:
```
node --version
```
You should see something like `v18.x.x` or `v20.x.x`

#### 3. SQL Server Express (the database)

**Download:** https://www.microsoft.com/en-us/sql-server/sql-server-downloads

Scroll down to "Express" and click "Download now"

When installing:
- Choose "Basic" installation
- Accept the defaults
- **Write down the server name** shown at the end (usually `localhost\SQLEXPRESS`)

#### 4. ODBC Driver (connects Python to SQL Server)

**Download:** https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

Choose "ODBC Driver 17 for SQL Server" for Windows.

---

### Step 1: Download FilaOps

Open Command Prompt and run these commands one at a time:

```
cd %USERPROFILE%\Documents
git clone https://github.com/Blb3D/filaops.git
cd filaops
```

**Don't have git?** Download it from https://git-scm.com/download/win

**Alternative:** Go to https://github.com/Blb3D/filaops, click the green "Code" button, then "Download ZIP". Extract to your Documents folder.

---

### Step 2: Install Python Packages

Still in Command Prompt, run:

```
cd backend
pip install -r requirements.txt
```

This will take a few minutes. You'll see lots of text scrolling. **Wait until it finishes** and you see your command prompt again.

**If you see errors about "pip not found":** Python wasn't added to PATH. Reinstall Python and make sure to check "Add Python to PATH".

---

### Step 3: Create the Database

Run this command:

```
python ../scripts/fresh_database_setup.py --database FilaOps
```

**What you should see:**

```
============================================================
FILAOPS FRESH DATABASE SETUP
============================================================

  Host: localhost\SQLEXPRESS
  Database: FilaOps
Created database 'FilaOps'

Creating tables...
All tables created successfully!

Seeding default data...
Default data seeded successfully!

  Default admin login:
    Email: admin@localhost
    Password: admin123
```

**If you see "Login failed" or connection errors:**
1. Make sure SQL Server is running (search "Services" in Windows, look for "SQL Server (SQLEXPRESS)")
2. Try: `python ../scripts/fresh_database_setup.py --database FilaOps --host localhost\SQLEXPRESS`

---

### Step 4: Configure FilaOps

Create a configuration file. Run:

```
copy .env.example .env
```

Now open the `.env` file in Notepad:

```
notepad .env
```

Find these lines and make sure they look like this:

```
DB_HOST=localhost\SQLEXPRESS
DB_NAME=FilaOps
DB_TRUSTED_CONNECTION=true
SECRET_KEY=change-this-to-any-random-text-you-want
```

Save and close Notepad.

---

### Step 5: Start the Backend Server

Run:

```
python -m uvicorn app.main:app --reload --port 8000
```

**What you should see:**

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

**Leave this window open!** The server needs to keep running.

**To verify:** Open your web browser and go to http://localhost:8000/docs

You should see "FilaOps API" with a list of endpoints.

---

### Step 6: Start the Web Interface

**Open a NEW Command Prompt window** (don't close the first one!)

```
cd %USERPROFILE%\Documents\filaops\frontend
npm install
npm run dev
```

The first command (`npm install`) will take a few minutes.

**What you should see:**

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

---

### Step 7: Log In

Open your web browser and go to: **http://localhost:5173**

You should see a login page.

**Login with:**
- **Email:** `admin@localhost`
- **Password:** `admin123`

**You're in!** You should see the FilaOps dashboard.

---

### Starting FilaOps (After First Setup)

Once everything is set up, here's how to start FilaOps each time:

**Window 1 - Backend:**
```
cd %USERPROFILE%\Documents\filaops\backend
python -m uvicorn app.main:app --reload --port 8000
```

**Window 2 - Frontend:**
```
cd %USERPROFILE%\Documents\filaops\frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

---

### Stopping FilaOps

In each Command Prompt window, press `Ctrl+C` to stop the server.

</details>

---

*FilaOps - ERP for 3D Print Farms*
