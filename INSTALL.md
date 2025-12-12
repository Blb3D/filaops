# FilaOps Installation Guide

> **For Print Farmers** - No development experience required.  
> Estimated time: 10-15 minutes

## What You'll Need

- A computer running Windows 10/11, macOS, or Linux
- 4GB+ RAM available
- 10GB+ free disk space
- Internet connection (for initial setup)

---

## Step 1: Install Docker Desktop

Docker runs FilaOps in isolated containers - no Python or database setup required.

### Windows

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Run the installer (double-click the downloaded file)
3. Follow the prompts - accept defaults
4. **Restart your computer** when prompted
5. After restart, Docker Desktop should start automatically (whale icon in system tray)

### macOS

1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Open the downloaded `.dmg` file
3. Drag Docker to Applications folder
4. Open Docker from Applications
5. Grant permissions when prompted

### Linux (Ubuntu/Debian)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to docker group (avoids needing sudo)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
```

---

## Step 2: Download FilaOps

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

## Step 3: Configure (Optional)

For most users, the defaults work fine. Skip to Step 4.

**If you want to customize:**

1. Copy the example config:
   - Windows: `copy .env.example .env`
   - Mac/Linux: `cp .env.example .env`

2. Edit `.env` and change:
   - `DB_PASSWORD` - Database password (change from default!)
   - `SECRET_KEY` - Security key (run `openssl rand -hex 32` to generate)

---

## Step 4: Start FilaOps

Open a terminal/command prompt in the FilaOps folder:

### Windows (PowerShell or Command Prompt)

```powershell
cd C:\FilaOps
docker-compose up -d
```

### Mac/Linux

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

---

## Step 5: Access FilaOps

1. Open your browser
2. Go to: **http://localhost:5173**
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

## Common Commands

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

### Build and Start (After Code Changes)
```bash
docker-compose build
docker-compose up -d
```

### Update to Latest Version (Rebuild from Scratch)
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

**Note:** `-d` flag is for `up` (detached/background mode), not `build`. Build first, then start.

### Reset Everything (⚠️ deletes all data)
```bash
docker-compose down -v
docker-compose up -d
```

---

## Accessing from Other Computers (Network/Remote Access)

> **Important:** If you see "Failed to fetch" or "Connection Issue" when accessing FilaOps from another computer, follow these steps.

To access FilaOps from other machines on your network:

1. Find your server's IP address:
   - Windows: `ipconfig` (look for IPv4 Address, e.g., `192.168.1.100`)
   - Mac/Linux: `ip addr` or `ifconfig`

2. Create/edit your `.env` file in the FilaOps folder:
   ```bash
   # Example: If your server IP is 192.168.1.100
   VITE_API_URL=http://192.168.1.100:8000
   ```

3. **Rebuild and restart** (rebuilding is required - the URL is baked into the frontend at build time):
   ```bash
   docker-compose down
   docker-compose build --no-cache frontend
   docker-compose up -d
   ```

4. Access from other computers at: `http://YOUR_IP_ADDRESS:5173`

### Why This Is Needed

The frontend is a static web app that needs to know where the API server is located. By default, it's configured for `localhost` which only works when accessing from the same machine. When you access from another computer, `localhost` refers to *that* computer, not your server.

Setting `VITE_API_URL` tells the frontend where to find the API server on your network.

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

---

## What's Next?

1. **Add your materials** - Inventory → Materials → Add Material
2. **Create your BOMs** - Products → Bill of Materials
3. **Enter a sales order** - Orders → New Order
4. **Run MRP** - Dashboard → Run MRP to see what you need to order

Need help? Check out the [User Guide](./docs/USER_GUIDE.md) or [Video Tutorials](https://youtube.com/@filaops).

---

*FilaOps - ERP for 3D Print Farms*
