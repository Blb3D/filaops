# FilaOps - 3D Print Farm ERP

> Production-grade manufacturing resource planning for 3D print operations

[![License: BSL](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

FilaOps is an open-source ERP system designed specifically for 3D print farms. It handles the complete workflow from quote to ship, with features tailored for additive manufacturing operations.

## Features

### Core ERP
- **Product Catalog** - SKUs, variants, pricing with material-aware costing
- **Bill of Materials** - Multi-level BOMs with filament/hardware components
- **Inventory Management** - Real-time stock levels, low stock alerts, FIFO tracking
- **Sales Orders** - Multi-channel order management (retail, wholesale, custom quotes)
- **Production Orders** - Manufacturing workflow with operation tracking
- **MRP** - Material requirements planning with demand forecasting

### Manufacturing
- **Work Centers** - Machine pools, capacity planning, utilization tracking
- **Routings** - Operation sequences with time standards
- **Traceability** - Serial numbers, lot tracking, recall queries (FDA/ISO ready)

### Integrations
- **Stripe** - Payment processing
- **EasyPost** - Multi-carrier shipping rates and labels
- **Squarespace** - Retail order sync (coming soon)
- **QuickBooks** - Accounting integration (coming soon)

## FilaOps Pro & Enterprise

Want the full production-ready experience? We offer hosted solutions with premium features:

| Feature | Open Source | Pro | Enterprise |
|---------|:-----------:|:---:|:----------:|
| Core ERP (Products, BOMs, Orders) | Yes | Yes | Yes |
| Inventory & MRP | Yes | Yes | Yes |
| Serial/Lot Traceability | Yes | Yes | Yes |
| **Customer Quote Portal** | - | Yes | Yes |
| **Multicolor/Multi-Material Quoting** | - | Yes | Yes |
| **B2B Partner Portal** | - | Yes | Yes |
| Squarespace/QuickBooks Sync | - | Yes | Yes |
| **ML Print Time Estimation** | - | - | Yes |
| **Printer Fleet Management** | - | - | Yes |
| **Live Production Monitoring** | - | - | Yes |

**Multicolor quoting** automatically calculates costs for AMS/multi-filament prints with accurate material usage per color.

Interested? [Contact us](mailto:hello@blb3dprinting.com) or watch this repo for updates.

## Quick Start

### Prerequisites
- Python 3.11+
- SQL Server Express (or SQL Server)
- ODBC Driver 17 for SQL Server

### Installation

```bash
# Clone the repository
git clone https://github.com/Blb3D/filaops.git
cd filaops

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your database credentials

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

### Verify Installation

Open http://localhost:8000/docs to see the API documentation.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Order Sources                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Squarespace   │  Customer Portal │    B2B Partners        │
│   (Retail)      │   (Custom Quotes)│   (Wholesale)          │
└────────┬────────┴────────┬────────┴────────┬────────────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FilaOps ERP                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Products │ │   BOMs   │ │ Orders   │ │Production│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Inventory │ │ Routing  │ │Traceabil │ │   MRP    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Print Floor                               │
│         (Bambu, Prusa, or any 3D printer fleet)             │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
filaops/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST API routes
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic
│   │   ├── core/               # Configuration, security
│   │   └── db/                 # Database session management
│   ├── tests/                  # Unit and integration tests
│   └── requirements.txt
├── docs/                       # Documentation
├── config/                     # Configuration templates
└── README.md
```

## API Overview

### Products & Inventory
```
GET    /api/v1/products           # List products
POST   /api/v1/products           # Create product
GET    /api/v1/inventory          # Current stock levels
POST   /api/v1/inventory/adjust   # Adjust inventory
```

### Orders
```
GET    /api/v1/sales-orders       # List sales orders
POST   /api/v1/sales-orders       # Create sales order
PATCH  /api/v1/sales-orders/{id}  # Update order status
```

### Production
```
GET    /api/v1/production-orders  # List production orders
POST   /api/v1/production-orders  # Create production order
POST   /api/v1/production-orders/{id}/start    # Start production
POST   /api/v1/production-orders/{id}/complete # Complete production
```

### Traceability
```
GET    /api/v1/admin/traceability/lots      # Material lots
GET    /api/v1/admin/traceability/serials   # Serial numbers
GET    /api/v1/admin/traceability/recall/forward/{lot}   # Forward trace
GET    /api/v1/admin/traceability/recall/backward/{sn}   # Backward trace
```

Full API documentation available at `/docs` when running.

## Configuration

Key environment variables (see `.env.example` for full list):

```env
# Database
DB_HOST=localhost\SQLEXPRESS
DB_NAME=FilaOps
DB_TRUSTED_CONNECTION=true

# Security
SECRET_KEY=your-secure-secret-key

# Integrations (optional)
STRIPE_SECRET_KEY=sk_test_...
EASYPOST_API_KEY=EZTKtest...
```

## Development

```bash
# Run tests
pytest

# Run with auto-reload
python -m uvicorn app.main:app --reload --port 8000

# Check API docs
open http://localhost:8000/docs
```

## Roadmap

- [x] Core ERP (Products, BOMs, Orders, Inventory)
- [x] Production Orders with Operation Tracking
- [x] Work Centers and Routing
- [x] Serial/Lot Traceability
- [ ] Squarespace Integration
- [ ] QuickBooks Integration
- [ ] B2B Partner Portal
- [ ] Advanced Analytics Dashboard

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## License

This project is licensed under the Business Source License 1.1. See [LICENSE](LICENSE) for details.

After 4 years, the code converts to Apache 2.0.

## Support

- **Issues**: [GitHub Issues](https://github.com/Blb3D/filaops/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

---

Built with Python, FastAPI, and SQLAlchemy. Designed for 3D print farms that need production-grade manufacturing control.
