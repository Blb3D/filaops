# Session Handoff - BLB3D ERP

> **AI ASSISTANTS: READ THIS FILE AT THE START OF EVERY SESSION.**
> This file captures critical context that must not be lost between sessions.
> Update this file at the END of every session with what was done and what's next.

## Last Updated

**Date:** December 5, 2025 (Session 4)
**Session Summary:** FilaOps public repo live on GitHub with clean history

---

## CRITICAL BUSINESS CONTEXT

### Three Repositories Work Together

```
C:\Users\brand\OneDrive\Documents\blb3d-erp       → ERP Backend (port 8000)
C:\Users\brand\OneDrive\Documents\quote-portal    → Customer + Admin UI (port 5173)
C:\Users\brand\OneDrive\Documents\bambu-print-suite → ML Dashboard (port 8001)
```

**IMPORTANT:**

- Admin UI is at `localhost:5173/admin` (quote-portal), NOT the ML Dashboard
- ML Dashboard reads from ERP via `/api/v1/internal/*` endpoints
- All three repos need to stay in sync

### Revenue-Critical Integrations NOT YET BUILT

| Integration | Why It Matters | Status |
|-------------|----------------|--------|
| **Squarespace** | 80%+ of revenue comes from here. Orders must sync to ERP. | NOT STARTED |
| **QuickBooks** | Accounting compliance. Invoices/payments must sync. | NOT STARTED |
| **B2B Parts Portal** | Retail partners need wholesale ordering | NOT STARTED |

### Current Payment/Shipping Status

- **Stripe**: Works but in TEST MODE only
- **EasyPost**: Works but in TEST MODE only
- Need production API keys before go-live

---

## WHAT WAS COMPLETED THIS SESSION

### GitHub Public Repo Live (Dec 5, 2025 - Session 4)

**Repository:** https://github.com/Blb3D/filaops

**Fresh Start (Clean History):**

- Deleted old repo with sensitive data in history
- Created new repo with single clean initial commit
- No data_migration folder, invoices, PDFs, or screenshots in history
- No Stripe test keys in history

**README Updated:**

- Added Pro & Enterprise tier promotion table
- Highlighted multicolor/multi-material quoting (Pro)
- Highlighted ML print time estimation (Enterprise)
- Fixed all GitHub URLs to Blb3D/filaops

**LICENSE:** User adding BSL 1.1 via GitHub web UI
- Licensor: Brandan Baker DBA BLB3D Printing
- Change Date: December 5, 2029 → Apache 2.0

### Previous Sessions

- Session 3: FilaOps rebrand, SAAS_TIERING_PLAN.md
- Session 2: Security audit, .gitignore updates
- Session 1: Phase 6B traceability, production order modal

---

## WHAT NEEDS TO BE DONE NEXT

### Public Repo - DONE

1. [x] **Choose repo name** - FilaOps
2. [x] **Clean repo** - Fresh history, no sensitive data
3. [x] **Update README.md** - Tier promotion added
4. [x] **Push to GitHub** - https://github.com/Blb3D/filaops
5. [x] **Add LICENSE file** - BSL 1.1 added, renamed to LICENSE

### Immediate (This Week)

1. [ ] **Test create production order** - Verify modal works end-to-end in quote-portal admin
2. [ ] **Add traceability UI** - Admin pages to manage lots, serials, run recall queries
3. [ ] **Squarespace integration** - Start with order webhook receiver

### Short Term

1. [ ] QuickBooks integration (OAuth2 flow, invoice sync)
2. [ ] B2B Partner Portal (pricing tiers, PO-based ordering)
3. [ ] Switch Stripe/EasyPost to production keys

### Known Issues

- 35 e2e tests skipped (conditional, need specific data states)
- Some tests reference wrong ports (fixed in latest commit)

---

## HOW TO PREVENT CONTEXT LOSS

### For the Human

1. **At session start**: Tell the AI to read `SESSION_HANDOFF.md` and `AI_CONTEXT.md`
2. **During session**: If discussing something important, ask AI to update these docs
3. **At session end**: Ask AI to update this file with what was done

### For the AI

1. **Always read** `AI_CONTEXT.md` → Integration Roadmap section
2. **Always read** this file (`SESSION_HANDOFF.md`)
3. **Update this file** at the end of every session
4. **Commit changes** before session ends to preserve work

---

## Key Files Reference

| Purpose | File Path |
|---------|-----------|
| Quick AI context | `AI_CONTEXT.md` |
| This handoff doc | `SESSION_HANDOFF.md` |
| Full architecture | `ARCHITECTURE.md` |
| Project roadmap | `ROADMAP.md` |
| ERP main entry | `backend/app/main.py` |
| Admin UI | `quote-portal/src/pages/admin/` |
| Production orders API | `backend/app/api/v1/endpoints/production_orders.py` |
| Traceability API | `backend/app/api/v1/endpoints/admin/traceability.py` |

---

## Environment Setup

```bash
# Start all services
cd blb3d-erp/backend && python -m uvicorn app.main:app --reload --port 8000
cd quote-portal && npm run dev
cd bambu-print-suite/ml-dashboard/backend && python main.py

# URLs
http://localhost:5173/admin    # Admin dashboard
http://localhost:8000/docs     # ERP API docs
http://localhost:8001/docs     # ML Dashboard docs
```
