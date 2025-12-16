# CLAUDE.md - Instructions for Claude

## FIRST: Read These Files Every Session

> **MANDATORY**: Before doing ANY work, read these files to avoid losing context:

1. **`SESSION_HANDOFF.md`** - What was done last session, what's next
2. **`AI_CONTEXT.md`** → "Integration Roadmap" section - Revenue-critical integrations NOT YET BUILT

**Why**: Context is lost between AI sessions. These files preserve critical business decisions.

---

## Project: BLB3D ERP

This is a custom ERP system for a 3D print farm business. Read `AI_CONTEXT.md` for quick context or `ARCHITECTURE.md` for full details.

## Key Context

### Multi-Channel Order System
- **Squarespace**: Retail orders with known product SKUs
- **Customer Portal**: B2B custom quotes with uploaded 3MF files  
- **Both must flow to the same production/MRP system**

### The Critical Gap (as of Nov 2025)
Portal quotes create orders WITHOUT products or BOMs. This breaks MRP.

**Solution needed**: When converting a quote to a sales order, auto-create:
1. A custom product (`CUSTOM-Q-2025-XXX`)
2. A BOM with material requirements from the quote

### Tech Stack
- FastAPI + SQL Server Express + SQLAlchemy
- Integrates with Bambu Print Suite (port 8001) for print scheduling
- JWT authentication

## Code Style

- Use type hints
- Follow existing patterns in codebase
- Pydantic for request/response validation
- SQLAlchemy ORM (not raw SQL except for complex queries)
- Use `Depends(get_db)` and `Depends(get_current_user)` patterns

## When Making Changes

1. **Check if change affects both order types** (quote-based AND line-item)
2. **Ensure product_id is always set** on production orders
3. **Update schemas** (Pydantic) when changing models
4. **Test with**: `python -m uvicorn app.main:app --reload --port 8000`

## File Structure

```text
backend/app/
├── api/v1/endpoints/   # Route handlers
├── models/             # SQLAlchemy models  
├── schemas/            # Pydantic schemas
├── services/           # Business logic
├── core/               # Config, security
└── db/                 # Database session
```

## Common Patterns

### Adding an endpoint
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter(prefix="/thing", tags=["Things"])

@router.post("/", response_model=ThingResponse)
async def create_thing(
    request: ThingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # implementation
```

### Status changes with timestamps
```python
if new_status == "confirmed":
    order.confirmed_at = datetime.utcnow()
elif new_status == "shipped":
    order.shipped_at = datetime.utcnow()
```

### Sequential number generation
```python
year = datetime.utcnow().year
last = db.query(Model).filter(Model.code.like(f"PO-{year}-%")).order_by(desc(Model.code)).first()
next_num = (int(last.code.split("-")[2]) + 1) if last else 1
code = f"PO-{year}-{next_num:03d}"
```

## Don't

- Don't use raw SQL unless necessary for complex aggregations
- Don't forget to handle the quote-based vs line-item distinction
- Don't assume product_id exists on older quote-based orders
- Don't hardcode status strings - but we don't have enums yet (TODO)

## FastAPI Gotchas

### Route Ordering (CRITICAL)
**Static routes MUST be defined BEFORE parameterized routes.**

FastAPI matches routes in definition order. If you have:
```python
# BAD - "consolidate" gets matched as {sales_order_id}
@router.post("/ship/{sales_order_id}/get-rates")
async def get_rates_for_order(sales_order_id: int): ...

@router.post("/ship/consolidate/get-rates")  # Never reached!
async def get_consolidated_rates(): ...
```

Fix by reordering:
```python
# GOOD - Static route first
@router.post("/ship/consolidate/get-rates")
async def get_consolidated_rates(): ...

@router.post("/ship/{sales_order_id}/get-rates")
async def get_rates_for_order(sales_order_id: int): ...
```

**Symptom**: 422 Unprocessable Content with error like:
```json
{"loc": ["path", "sales_order_id"], "msg": "Input should be a valid integer", "input": "consolidate"}
```

### EasyPost Rate Purchase
The `buy` method requires rate as a dict, not just the ID:
```python
# BAD
client.shipment.buy(shipment_id, rate=rate_id)

# GOOD
client.shipment.buy(shipment_id, rate={"id": rate_id})
```

## Useful Commands

```bash
# Run server
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Check API docs
open http://localhost:8000/docs

# Test database connection
python -c "from app.db.session import engine; print(engine.execute('SELECT 1').scalar())"
```

## Related Docs

- `SESSION_HANDOFF.md` - **READ FIRST** - Session continuity
- `AI_CONTEXT.md` - Quick reference for AI assistants (includes Integration Roadmap)
- `ARCHITECTURE.md` - Full system architecture
- `ROADMAP.md` - Development roadmap and phases
- `PHASE2_COMPLETE.md` - What was built in Phase 2
- `BAMBU_PRINT_SUITE_INTEGRATION.md` - Integration details

---

## Related Repositories

This system spans 3 local repositories. When working on integrations, you may need context from all three:

| Repo | Location | Purpose | Public? |
|------|----------|---------|---------|
| **blb3d-erp** (this) | `C:\Users\brand\OneDrive\Documents\blb3d-erp` | ERP Backend (port 8000) | YES |
| **quote-portal** | `C:\Users\brand\OneDrive\Documents\quote-portal` | Customer + Admin UI (port 5173) | YES |
| **bambu-print-suite** | `C:\Users\brand\OneDrive\Documents\bambu-print-suite` | ML Dashboard + Print Management (port 8001) | NO - contains proprietary ML models |

### When to Check Other Repos

- **Frontend changes**: Check `quote-portal/src/pages/admin/` for admin UI
- **Quote generation**: Check `bambu-print-suite/quote-engine/` for slicing logic
- **ML features**: Check `bambu-print-suite/ml-dashboard/` (PRIVATE - don't expose)
- **API integration**: This repo's `/api/v1/internal/*` endpoints are consumed by bambu-print-suite

### Proprietary Content (NEVER make public)

- `bambu-print-suite/Printer_Gcode_Files/` - Production print history
- `bambu-print-suite/ml-engine/data/` - ML training data
- `**/data/models/*.pkl` - Trained ML models
- Any file with print farm operational data
