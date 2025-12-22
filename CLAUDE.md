# FilaOps - Claude Code Instructions

## ⚠️ CRITICAL - Development Environment Only

**This folder is for DEVELOPMENT only. Production runs in a separate location (`C:\BLB3D_Production`).**

### Always Use Development Commands

```bash
# CORRECT - Development (safe)
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml exec backend <command>

# WRONG - Never use bare docker-compose in this folder!
docker-compose build  # ❌ NO!
docker-compose up     # ❌ NO!
```

### Development Environment

| Service | Port | Container |
|---------|------|-----------|
| Frontend | http://localhost:5174 | filaops-dev-frontend |
| Backend | http://localhost:8001 | filaops-dev-backend |
| Database | localhost:1434 | filaops-dev-db |
| Redis | localhost:6380 | filaops-dev-redis |

### Production Environment

**Location**: `C:\BLB3D_Production`

| Service | Port | Container |
|---------|------|-----------|
| Frontend | http://localhost:7000 | filaops-prod-frontend |
| Backend | http://localhost:10000 | filaops-prod-backend |
| Database | localhost:1435 | filaops-prod-db |
| Redis | localhost:6381 | filaops-prod-redis |

### Why This Matters

- Production is completely separate (different folder, different containers, different volumes, different ports)
- Development has its own Docker volumes (`filaops-dev-*`)
- You cannot accidentally touch production from this folder

---

## Project Overview
FilaOps is an ERP system for 3D printing businesses built with:
- **Backend**: Python/FastAPI with SQLAlchemy and PostgreSQL
- **Frontend**: React with Vite, Tailwind CSS
- **Deployment**: Docker Compose

## Development Workflow

### Before Pushing Code
**IMPORTANT: Always follow this checklist before `git push`:**

1. **Run backend tests**
   ```bash
   cd backend && python -m pytest tests/ -v
   ```

2. **Run linting**
   ```bash
   cd backend && ruff check .
   ```

3. **List files for CodeRabbit review**
   ```bash
   git diff --name-only HEAD~1  # or appropriate range
   ```

4. **Wait for CodeRabbit review** (if PR is open)
   - Address any CodeRabbit findings before merging
   - Common issues: SQL Server compatibility, type hints, error handling
'''markdown
### Commit Message Format
```
Longer description if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### Issue Workflow
- Reference issues in commits: `Fixes #123` or `Relates to #123`
- Add comments to issues with implementation details
- Close issues only after testing confirms the fix

## Code Style

### Backend (Python)
- Use type hints for function parameters and returns
- Use Pydantic models for request/response validation
- Follow existing patterns in `app/services/` for business logic

### Frontend (React)
- Use dark theme styling (bg-gray-900, text-white, border-gray-700)
- Use Tailwind CSS classes consistently
- Fetch from `${API_URL}/api/v1/...`

## Testing Checklist

### For New Features
1. Unit tests in `backend/tests/`
2. API endpoint testing via curl or frontend
3. Docker container rebuild if dependencies changed
4. UI workflow testing with screenshots (for documentation)

### For Bug Fixes
1. Verify the issue is reproducible
2. Implement fix
3. Test fix resolves the issue
4. Check for regressions
