# FilaOps — Zero-to-Running (Docker)

This guide gets you from **nothing** to a **working FilaOps** using Docker containers.
No need to install Python, Node.js, or PostgreSQL on your machine—Docker handles everything.

**You'll know you're done when:**
- Backend health check returns: `{"status":"healthy"}`
- Frontend opens in your browser at http://localhost:5173
- Setup Wizard appears to create your admin account

---

## Quick Start (copy/paste)

```bash
# Clone the repo
git clone https://github.com/Blb3D/filaops.git
cd filaops

# Copy environment template
cp .env.example .env

# Start all services
docker-compose up --build

# Access FilaOps
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

First build takes 3-5 minutes. Subsequent starts are much faster.

---

## 1) Prerequisites

Install Docker Desktop for your platform:

| Platform | Download |
|----------|----------|
| **Windows** | [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) |
| **macOS** | [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) |
| **Linux** | [Docker Engine](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/) |

**Verify installation:**
```bash
docker --version
# Docker version 24.0.0 or higher

docker-compose --version
# Docker Compose version v2.20.0 or higher
```

---

## 2) Clone the Repository

```bash
# Clone FilaOps
git clone https://github.com/Blb3D/filaops.git
cd filaops
```

Already cloned? Update it:
```bash
git pull
```

---

## 3) Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

**Edit `.env`** with your preferred settings:

```bash
# Database (used by PostgreSQL container)
DB_HOST=db
DB_PORT=5432
DB_NAME=filaops
DB_USER=postgres
DB_PASSWORD=YourSecurePassword123!   # ← Change this!

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production

# Application
ENVIRONMENT=production
DEBUG=false
FILAOPS_TIER=open
```

> ⚠️ **Important:** Change `DB_PASSWORD` and `SECRET_KEY` before deploying to production!

**Generate a secure SECRET_KEY:**
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use openssl
openssl rand -base64 32
```

---

## 4) Build and Start Services

```bash
# Build and start all containers
docker-compose up --build
```

**What happens:**
1. PostgreSQL 17 container starts and initializes
2. Backend container builds, runs migrations, starts FastAPI
3. Frontend container builds and starts Vite dev server

**First run takes 3-5 minutes** while Docker:
- Downloads base images (Python, Node, PostgreSQL)
- Installs dependencies
- Builds the application

Watch for these success indicators:
```
filaops-db       | database system is ready to accept connections
filaops-backend  | INFO:     Uvicorn running on http://0.0.0.0:8000
filaops-frontend | VITE v5.x.x  ready in xxx ms
filaops-frontend | ➜  Local:   http://localhost:5173/
```

---

## 5) Verify Installation

**Test backend health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

**Test API docs:**
Open http://localhost:8000/docs in your browser. You should see the FastAPI Swagger UI.

**Access the application:**
Open http://localhost:5173 in your browser. The **Setup Wizard** will guide you through creating your admin account.

---

## 6) Daily Usage

**Start FilaOps:**
```bash
cd filaops
docker-compose up
```

**Start in background (detached):**
```bash
docker-compose up -d
```

**Stop FilaOps:**
```bash
docker-compose down
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

**Restart a specific service:**
```bash
docker-compose restart backend
```

---

## 7) Data Persistence

Your data is stored in Docker volumes and persists across restarts:

| Volume | Contents |
|--------|----------|
| `filaops_postgres_data` | PostgreSQL database files |

**Backup your database:**
```bash
# Create backup
docker-compose exec db pg_dump -U postgres filaops > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec -T db psql -U postgres filaops < backup_20251226.sql
```

**⚠️ Warning:** Running `docker-compose down -v` will **delete all data**. Only use `-v` flag if you want a fresh start.

---

## 8) Updating FilaOps

```bash
# Pull latest code
git pull

# Rebuild and restart containers
docker-compose down
docker-compose up --build
```

The backend automatically runs database migrations on startup.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   db        │    │  backend    │    │  frontend   │     │
│  │ PostgreSQL  │◄───│  FastAPI    │◄───│    Vite     │     │
│  │   :5432     │    │   :8000     │    │   :5173     │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│        │                  │                  │              │
└────────┼──────────────────┼──────────────────┼──────────────┘
         │                  │                  │
    (internal)         localhost:8000    localhost:5173
                            │                  │
                       ┌────┴──────────────────┴────┐
                       │      Your Browser          │
                       └────────────────────────────┘
```

| Service | Port | Description |
|---------|------|-------------|
| `db` | 5432 (internal) | PostgreSQL 17 database |
| `backend` | 8000 | FastAPI REST API |
| `frontend` | 5173 | Vite React development server |

---

## Troubleshooting

### "Port already in use"

Another application is using port 5173, 8000, or 5432.

**Find what's using the port:**
```bash
# Windows
netstat -ano | findstr :8000

# macOS/Linux
lsof -i :8000
```

**Solutions:**
1. Stop the conflicting application
2. Or edit `docker-compose.yml` to use different ports:
   ```yaml
   ports:
     - "8001:8000"  # Change left number (host port)
   ```

---

### "Cannot connect to Docker daemon"

Docker Desktop isn't running.

**Solution:** Start Docker Desktop application, wait for it to fully load, then retry.

---

### Backend container keeps restarting

Usually a database connection issue.

**Check logs:**
```bash
docker-compose logs backend
```

**Common causes:**
1. Database not ready yet (wait 30 seconds, it should resolve)
2. Wrong `DB_PASSWORD` in `.env`
3. Database container failed to start

**Fix database issues:**
```bash
# Check database container
docker-compose logs db

# Restart everything fresh
docker-compose down
docker-compose up --build
```

---

### "FATAL: password authentication failed"

Password in `.env` doesn't match what PostgreSQL was initialized with.

**Solution (fresh start):**
```bash
# Remove volumes and start fresh
docker-compose down -v
docker-compose up --build
```

> ⚠️ This deletes all data. Only use if you're okay losing your database.

---

### Frontend shows "Failed to fetch"

Backend isn't running or CORS issue.

**Check backend is running:**
```bash
curl http://localhost:8000/health
```

**Check backend logs:**
```bash
docker-compose logs backend
```

---

### Build fails with "no space left on device"

Docker has run out of disk space.

**Clean up Docker:**
```bash
# Remove unused containers, networks, images
docker system prune -a

# Remove unused volumes (careful - this deletes data!)
docker volume prune
```

---

### Changes to code aren't reflected

Docker cached the old build.

**Rebuild without cache:**
```bash
docker-compose build --no-cache
docker-compose up
```

---

## Advanced Configuration

### Using External PostgreSQL

If you already have PostgreSQL running elsewhere:

1. Comment out the `db` service in `docker-compose.yml`
2. Update `.env`:
   ```
   DB_HOST=your-postgres-host.com
   DB_PORT=5432
   DB_NAME=filaops
   DB_USER=your_user
   DB_PASSWORD=your_password
   ```
3. Start only backend and frontend:
   ```bash
   docker-compose up backend frontend
   ```

---

### Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx, Traefik) for SSL/HTTPS
2. **Set strong passwords** in `.env`
3. **Enable backups** for the PostgreSQL volume
4. **Use Docker secrets** instead of `.env` for sensitive values
5. **Set resource limits** in `docker-compose.yml`:
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 512M
   ```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start | `docker-compose up` |
| Start (background) | `docker-compose up -d` |
| Stop | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Rebuild | `docker-compose up --build` |
| Fresh start | `docker-compose down -v && docker-compose up --build` |
| Backup DB | `docker-compose exec db pg_dump -U postgres filaops > backup.sql` |

---

## Next Steps

1. **Create your admin account** via the Setup Wizard
2. **Import your products** from CSV (see [Marketplace Import Guide](docs/MARKETPLACE_IMPORT_GUIDE.md))
3. **Set up your inventory** locations and materials
4. **Create your first BOM** for a product

**Need help?**
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [FAQ](FAQ.md)
- [Discord Community](https://discord.gg/FAhxySnRwa)

---

*Last updated: December 2025*
