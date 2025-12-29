# FilaOps Session Handoff
## Date: 2025-12-29

---

## WHAT HAPPENED THIS SESSION

**Started:** Frustrated with whack-a-mole bug fixing on UI changes (SO screen buttons not carrying data to Purchasing)

**Pivoted:** Instead of fixing symptoms, we mapped the entire system properly

**Outcome:** Created comprehensive Functional Specification based on operator interview

---

## KEY DOCUMENTS CREATED

| File | Location | Purpose |
|------|----------|---------|
| filaops-functional-spec.md | /home/claude/ AND outputs folder | THE source of truth |

**Copy to repo:** `C:\repos\filaops\docs\filaops-functional-spec.md`

---

## BRANDAN'S OPERATION (Summary)

```
Solo 3D print farm owner
├── 6-7 days/week, 20 hrs/day (unsustainable - system should reduce this)
├── Multiple sales channels: Shopify, Etsy, TikTok, wholesale, POS, custom quotes
├── MTO + MTS hybrid (custom orders AND stocked products)
├── Multiple printers (P1S, A1s)
├── QuickBooks for accounting (keep it there)
```

**Pricing Formula:**
```
Material Cost + ($1.50 × Runtime Hours) = Direct Cost
Direct Cost × 3.5 = Retail Price
Direct Cost × 2.5 = B2B Price (10+ units)
Standard filament cost: $0.02/gram
```

**Replenishment Strategy:**
- Staples (PLA black/white/red): Reorder point alerts
- Specialty (TPU, silk): Order-driven only

**What he needs to see:**

Morning: Ship today, Print today, Need to order, Printer status, Pending quotes

Evening: Need to order, Arriving soon, Low stock, Overnight print suggestions

---

## SPEC STRUCTURE (v0.2)

1. **Part 1: Core Entities** - Items, BOMs, Customers, Vendors, UOM, Locations
2. **Part 2: Workflows** - Quote, SO, WO, PO, Shipment (with state machines)
3. **Part 3: MRP** - Availability calc, shortage detection, reorder alerts
4. **Part 4: Dashboards** - Morning + Evening layouts
5. **Part 5: Integrations** - Future (Shopify, QB, Pirateship, printer status)
6. **Part 6: Data Rules** - Invariants that must always be true
7. **Part 7: Testing** - Critical path tests

---

## NEXT SESSION: TODO

1. **Compare spec to current code**
   - What matches?
   - What's missing?
   - What's broken?

2. **Identify the broken "Order Missing Parts" flow**
   - Spec says: SO blocking issues → pre-fill PO dialog → create PO → link back
   - Current behavior: button opens purchasing, nothing carries over

3. **Prioritize fixes**
   - Core data integrity first
   - Then workflows
   - Then UI

4. **Consider: Integration tests before more UI work**
   - Write tests that prove the core flows work
   - Then fix until tests pass
   - Then resume UI sprint

---

## PREVIOUS WORK (Still Valid)

From earlier sessions (in /mnt/transcripts/):
- UI Refactor plans in `C:\repos\filaops\docs\UI_Refactor\`
- Branching strategy documented
- CI quality gates defined (23 backend + 7 E2E tests passing)
- Dev tracker at /home/claude/filaops-dev-tracker.md

**Branch:** feat/ui-redesign (has UI work, but blocked on data flow issues)

---

## 3-SECOND BOB PROTOCOL

When starting next session, say:

> "FilaOps. We built a functional spec yesterday. Need to compare it to actual code and fix the broken data flows. Spec is at C:\repos\filaops\docs\filaops-functional-spec.md"

Claude will pick up from there.

---

## OPEN QUESTIONS (Decisions Needed)

1. Partial shipments? (ship 8 of 10 now, 2 later)
2. Lot/serial tracking? (needed for traceability?)
3. Multi-location? (or just MAIN for now)
4. How much audit logging?

---

**END OF HANDOFF**
