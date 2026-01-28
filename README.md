<div align="center">

# FilaOps

### The ERP Built for 3D Print Farms

*Production-grade manufacturing software that actually understands additive manufacturing*

[![License: BSL 1.1](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Discord](https://img.shields.io/badge/Discord-Community-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/FAhxySnRwa)

[Quick Start](#-quick-start) · [Features](#-features) · [Documentation](docs/) · [Contributing](CONTRIBUTING.md)

</div>

---

> [!CAUTION]
> **Security Alert:** A malicious actor has been distributing malware through fake FilaOps repositories.
>
> **Official source:** `github.com/Blb3D/filaops` only. [Full security details](SECURITY.md)

---

## Why FilaOps?

Most ERP systems were built for traditional manufacturing—injection molding, CNC, assembly lines. They don't understand filament spools, print times, multi-material jobs, or why you need to track which roll went into which print.

**FilaOps was built by a print farm owner who got tired of spreadsheets.**

| Problem | FilaOps Solution |
|---------|------------------|
| Generic BOMs don't track filament usage | BOMs with per-gram material costs and scrap factors |
| No concept of print failures | Scrap tracking with reasons, partial quantities, auto-remake orders |
| Inventory doesn't track spools | Lot/serial traceability down to the spool level |
| Enterprise software requires enterprise budgets | Self-hosted, open source, your data stays yours |
| Dark mode? What's that? | Built for 2am production runs |

---

## Features

### Core Manufacturing

| Module | Description |
|--------|-------------|
| **Products & Items** | Unified catalog for finished goods, components, filament, hardware |
| **Bill of Materials** | Multi-level BOMs with material costs, scrap factors, unit conversions |
| **Inventory Management** | Real-time stock levels, FIFO tracking, configurable reorder points |
| **Production Orders** | Complete workflow from sales order to shipment |
| **Operations & Routing** | Multi-step manufacturing with work centers and scheduling |
| **Scrap & Remake** | Track failures by reason, partial scrap, automatic remake generation |
| **MRP Engine** | Material requirements planning with shortage detection and suggestions |

### Quality & Traceability

| Feature | Description |
|---------|-------------|
| **Serial Numbers** | Unique identifiers for finished goods |
| **Lot Tracking** | Batch traceability for raw materials |
| **Forward/Backward Trace** | "Where did this material go?" / "What went into this product?" |
| **Compliance Ready** | Foundation for FDA 21 CFR Part 11, ISO 13485 |

### Business Operations

| Feature | Description |
|---------|-------------|
| **Sales Orders** | Customer order management with status tracking |
| **Purchase Orders** | Vendor management, receiving, cost tracking |
| **General Ledger** | Basic accounting with journal entries |
| **Multi-User** | Team access with role-based permissions |
| **REST API** | Complete API for integrations and automation |

---

## Quick Start

### Option 1: Docker (Fastest)

```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops
cp .env.example .env
docker-compose up --build
```

Open http://localhost:5173 — the Setup Wizard creates your admin account.

### Option 2: Native Installation

**Prerequisites:** Python 3.11+, PostgreSQL 16+, Node.js 18+

```bash
# Clone
git clone https://github.com/Blb3D/filaops.git
cd filaops

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Edit with your PostgreSQL credentials
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Admin Dashboard |
| http://localhost:8000/docs | API Documentation |
| http://localhost:8000/health | Health Check |

**Detailed guides:** [Windows](docs/setup/windows.md) · [macOS/Linux](docs/setup/linux-macos.md) · [Docker](docs/setup/docker.md)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FilaOps ERP                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │   React     │────▶│   FastAPI   │────▶│ PostgreSQL  │        │
│  │  Frontend   │     │   Backend   │     │  Database   │        │
│  │  (Vite)     │◀────│  (Uvicorn)  │◀────│   (16+)     │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│        :5173              :8000                                  │
├─────────────────────────────────────────────────────────────────┤
│  Backend Services:                                               │
│  • MRP Engine - Material requirements planning                   │
│  • Scrap Service - Failure tracking and remake generation        │
│  • Inventory Service - Stock management with FIFO                │
│  • Traceability - Lot/serial tracking with recall queries        │
│  • Transaction Audit - Complete change history                   │
└─────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
filaops/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # REST endpoints
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── services/      # Business logic (MRP, scrap, inventory)
│   │   ├── schemas/       # Pydantic request/response models
│   │   └── core/          # Configuration, security, utilities
│   ├── migrations/        # Alembic database migrations
│   └── tests/             # pytest test suite
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable React components
│   │   ├── pages/         # Page components
│   │   └── lib/           # Utilities and API client
│   └── public/
└── docs/                  # Documentation
```

---

## Editions

| | Community | Pro | Enterprise |
|---|:---:|:---:|:---:|
| **Core ERP** | ✅ | ✅ | ✅ |
| Products, BOMs, Inventory | ✅ | ✅ | ✅ |
| Sales & Production Orders | ✅ | ✅ | ✅ |
| Operations & Routing | ✅ | ✅ | ✅ |
| Scrap Tracking & Remakes | ✅ | ✅ | ✅ |
| MRP & Shortage Detection | ✅ | ✅ | ✅ |
| Serial/Lot Traceability | ✅ | ✅ | ✅ |
| REST API | ✅ | ✅ | ✅ |
| **Integrations** | | | |
| Customer Quote Portal | — | ✅ | ✅ |
| B2B Wholesale Portal | — | ✅ | ✅ |
| QuickBooks Integration | — | ✅ | ✅ |
| Shopify/Squarespace Sync | — | ✅ | ✅ |
| **Advanced** | | | |
| Advanced Permissions | — | ✅ | ✅ |
| User Activity Audit | — | ✅ | ✅ |
| ML Print Time Estimation | — | — | ✅ |
| Printer Fleet Management | — | — | ✅ |
| SSO / LDAP | — | ✅ | ✅ |
| Priority Support | — | — | ✅ |
| **Pricing** | Free | Contact | Contact |

**Pro & Enterprise launching 2026** — [Join waitlist](mailto:info@blb3dprinting.com)

---

## Documentation

| Guide | Description |
|-------|-------------|
| [Getting Started](docs/getting-started.md) | First-time setup walkthrough |
| [How It Works](docs/how-it-works.md) | System overview and workflows |
| [API Reference](http://localhost:8000/docs) | Interactive API documentation |
| [Email Configuration](docs/EMAIL_CONFIGURATION.md) | SMTP setup for notifications |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |
| [FAQ](docs/faq.md) | Frequently asked questions |

---

## Contributing

We welcome contributions from the community.

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/filaops.git
cd filaops

# Create feature branch
git checkout -b feature/your-feature

# Make changes, then
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

**Good first issues:**
- Bug fixes and error handling improvements
- Documentation updates
- UI/UX polish
- Test coverage expansion

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

**Business Source License 1.1** — [Full text](LICENSE)

| Use Case | Allowed |
|----------|---------|
| Internal business use | ✅ Yes |
| Personal / educational | ✅ Yes |
| Modifications for internal use | ✅ Yes |
| Offering as hosted service | ❌ No |
| After 4 years | Apache 2.0 |

---

## Support

| Channel | Use For |
|---------|---------|
| [Discord](https://discord.gg/FAhxySnRwa) | Community chat, quick questions |
| [GitHub Issues](https://github.com/Blb3D/filaops/issues) | Bug reports |
| [GitHub Discussions](https://github.com/Blb3D/filaops/discussions) | Feature requests, ideas |
| [Email](mailto:info@blb3dprinting.com) | Business inquiries |

---

<div align="center">

**Built by [BLB3D](https://blb3dprinting.com)** — A print farm that needed real manufacturing software.

*If you find FilaOps useful, consider giving it a ⭐ on GitHub!*

</div>
