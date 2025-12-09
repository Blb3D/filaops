# FilaOps - 3D Print Farm ERP

> Open source manufacturing resource planning for 3D print operations

[![License: BSL](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

FilaOps is an open source ERP system built for 3D print farms. Manage products, inventory, BOMs, orders, and production - designed by someone who actually runs a print farm.

![FilaOps Dashboard](docs/images/dashboard-preview.png)

---

## 🚀 Quick Start (Docker - 5 Minutes)

**No coding required!** Perfect for print farm owners who want professional ERP functionality without the complexity.

```bash
# 1. Clone the repo
git clone https://github.com/Blb3D/filaops.git
cd filaops

# 2. Start everything (one command!)
docker-compose up -d

# 3. Open your browser
# http://localhost:5173
```

**That's it!** Everything is pre-configured:
- ✅ SQL Server database (auto-initialized)
- ✅ Backend API (FastAPI)
- ✅ Frontend UI (React)
- ✅ All dependencies included

**Default login:** admin@filaops.local / admin123

📖 **[Full Installation Guide](INSTALL.md)** - Step-by-step for Windows/Mac/Linux

> **Why Docker?** Most ERP systems require hours of setup, database configuration, and dependency management. FilaOps runs in containers - everything just works. Perfect for print farm owners who want to focus on their business, not IT infrastructure.

---

## What You Get

### Core ERP (Fully Functional)
- **Product Catalog** - Unified item master (finished goods, components, supplies, services)
- **Bill of Materials** - Multi-level BOMs with explicit units of measure and cost-only flags
- **Inventory Management** - Stock levels, allocations, low stock alerts with MRP integration
- **Sales Orders** - Complete order management with status tracking and MRP explosion
- **Production Orders** - Manufacturing workflow with operation tracking
- **MRP** - Material requirements planning with shortage detection
- **Purchasing** - Low stock alerts with MRP-driven requirements
- **Shipping** - Multi-carrier support, production status validation, packing slips

### Admin Dashboard
- Full React-based admin UI with **dark theme** (your eyes will thank you)
- Real-time KPIs: overdue orders, low stock items, revenue metrics
- Order Command Center: MRP explosion, material/capacity requirements, shortage detection

---

## 📖 Documentation

| Guide | Description |
|-------|-------------|
| **[INSTALL.md](INSTALL.md)** | Docker deployment for print farmers |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Development setup guide |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | Understanding the workflow |
| [CONTRIBUTING.md](CONTRIBUTING.md) | For contributors |

---

## Development Setup (For Contributors)

If you want to modify FilaOps or contribute, here's the dev setup:

### Prerequisites
- Python 3.11+
- Node.js 18+
- SQL Server Express (or SQL Server)
- ODBC Driver 17 for SQL Server

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database settings
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

API docs: http://localhost:8000/docs
Admin UI: http://localhost:5173

---

## Configuration

### Docker (.env file)
```env
# Copy .env.example to .env and customize
DB_PASSWORD=YourSecurePassword
SECRET_KEY=your-64-char-hex-key
```

### Manual Setup (backend/.env)
```env
DB_HOST=localhost\SQLEXPRESS
DB_NAME=FilaOps
DB_TRUSTED_CONNECTION=true
SECRET_KEY=your-secure-secret-key
```

---

## Project Structure
```
filaops/
├── backend/           # FastAPI REST API
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── models/    # SQLAlchemy ORM
│   │   ├── services/  # Business logic (MRP, etc)
│   │   └── core/      # Config, security
│   └── Dockerfile
├── frontend/          # React admin UI
│   └── Dockerfile
├── docker-compose.yml # One-command deployment
├── INSTALL.md         # User installation guide
└── scripts/           # Database setup
```

---

## API Overview

### Products & Inventory
```
GET    /api/v1/items              # List all items
POST   /api/v1/items              # Create item
GET    /api/v1/items/low-stock    # Low stock items + MRP shortages
GET    /api/v1/admin/inventory/transactions  # Transaction history
```

### Orders & MRP
```
GET    /api/v1/sales-orders       # List sales orders
POST   /api/v1/sales-orders       # Create sales order
GET    /api/v1/sales-orders/{id}  # Order detail with MRP explosion
POST   /api/v1/mrp/requirements   # Calculate material requirements
```

### Production
```
GET    /api/v1/production-orders  # List production orders
POST   /api/v1/production-orders  # Create production order
POST   /api/v1/production-orders/{id}/start
POST   /api/v1/production-orders/{id}/complete
```

Full interactive API docs at `http://localhost:8000/docs` when running.

---

## FilaOps Tiers

| Feature | Community | Pro | Enterprise |
|---------|:---------:|:---:|:----------:|
| Products, BOMs, Inventory | ✅ | ✅ | ✅ |
| Sales & Production Orders | ✅ | ✅ | ✅ |
| MRP & Capacity Planning | ✅ | ✅ | ✅ |
| Serial/Lot Traceability | ✅ | ✅ | ✅ |
| Admin Dashboard UI | ✅ | ✅ | ✅ |
| Docker Deployment | ✅ | ✅ | ✅ |
| REST API | ✅ | ✅ | ✅ |
| Customer Quote Portal | - | ✅ | ✅ |
| Multi-User | - | ✅ | ✅ |
| E-commerce Integrations | - | ✅ | ✅ |
| Printer Fleet Management | - | - | ✅ |
| ML Print Time Estimation | - | - | ✅ |
| Priority Support | - | - | ✅ |

**Pro & Enterprise coming 2026** - [Join the waitlist](mailto:hello@blb3dprinting.com)

---

## Recent Updates (December 2025)

- ✅ **Docker deployment** - One-command setup for print farmers
- ✅ MRP engine refactoring (Phase 5 complete)
- ✅ Inventory transaction management
- ✅ Enhanced dashboard with MRP-integrated alerts
- ✅ Unified item master system

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes.

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

Key areas:
- Bug fixes and testing
- Documentation improvements
- UI/UX enhancements
- Performance optimization

---

## License

**Business Source License 1.1** - see [LICENSE](LICENSE)

- ✅ Free for internal business use
- ✅ Free for personal/educational use
- ❌ Cannot be used to offer competing SaaS
- 🔓 Converts to Apache 2.0 after 4 years

---

## Support

- [GitHub Issues](https://github.com/blb3dprinting/filaops/issues) - Bug reports
- [GitHub Discussions](https://github.com/blb3dprinting/filaops/discussions) - Questions & ideas
- [Discord](https://discord.gg/filaops) - Community chat

---

Built by [BLB3D](https://blb3dprinting.com) - a print farm that needed real manufacturing software.
