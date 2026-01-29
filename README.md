# FilaOps

Open-source ERP for 3D print farm operations. Manage inventory, production orders, BOMs, MRP, sales orders, purchasing, and GL accounting in one system built for additive manufacturing.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** React + Vite + Tailwind CSS
- **Printer Integration:** MQTT (Bambu Lab fleet monitoring)

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\Activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database

FilaOps requires PostgreSQL. Create a database and configure `backend/.env`:

```ini
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/filaops
```

Run migrations:

```bash
cd backend
alembic upgrade head
```

## Features

37 core features across 8 modules:

- **Sales** - Quotes, sales orders, fulfillment tracking, blocking issues
- **Inventory** - Multi-location tracking, transactions, cycle counting, spool management
- **Manufacturing** - Production orders, BOMs, routings, work centers, scrap tracking
- **Purchasing** - Purchase orders, receiving, vendor management
- **MRP** - Demand calculation, supply netting, planned order generation
- **Accounting** - Chart of accounts, journal entries, GL reporting, period close
- **Traceability** - Lot tracking, serial numbers, material consumption history
- **Printing** - MQTT printer monitoring, print job tracking, resource scheduling

See [Feature Catalog](docs/FEATURE-CATALOG.md) for the complete list.

## Project Structure

```text
backend/
  app/
    api/v1/endpoints/   # FastAPI route handlers
    models/             # SQLAlchemy models
    services/           # Business logic
    core/               # Config, security, UOM
  alembic/              # Database migrations
  tests/                # pytest unit + integration tests
frontend/
  src/
    components/         # React components
    pages/              # Page-level views
    services/           # API client
```

## Testing

```bash
cd backend
pytest tests/ -v
```

## License

[Business Source License 1.1](LICENSE) - Free for non-competing use. Converts to Apache 2.0 on December 5, 2029.
