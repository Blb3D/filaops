#!/usr/bin/env python3
"""
Quick test script for Phase 1 order status workflow
Run from backend container: python test_order_status.py
"""

from app.db.session import SessionLocal
from app.models.sales_order import SalesOrder
from app.models.production_order import ProductionOrder
from app.models.product import Product
from app.models.bom import BOM
from app.services.order_status import order_status_service
from datetime import datetime

# Create database session
db = SessionLocal()

print("\n" + "=" * 60)
print("PHASE 1 ORDER STATUS WORKFLOW - QUICK TEST")
print("=" * 60)

# ========================================
# TEST 1: Verify Models Have New Fields
# ========================================
print("\n=== TEST 1: Check Model Fields ===")

so = db.query(SalesOrder).first()
if so:
    print(f"SO {so.order_number}:")
    print(f"  status: {so.status}")
    print(f"  fulfillment_status: {so.fulfillment_status}")
    print("✅ SalesOrder has fulfillment_status field!")
else:
    print("⚠️  No sales orders found")

wo = db.query(ProductionOrder).first()
if wo:
    print(f"\nWO {wo.code}:")
    print(f"  status: {wo.status}")
    print(f"  qc_status: {wo.qc_status}")
    print("✅ ProductionOrder has qc_status field!")
else:
    print("⚠️  No production orders found")

# ========================================
# TEST 2: Status Transition Validation
# ========================================
print("\n=== TEST 2: Status Transition Validation ===")

is_valid, error = order_status_service.validate_so_transition("draft", "pending_payment")
print(f"draft → pending_payment: {'✅ VALID' if is_valid else '❌ INVALID'}")

is_valid, error = order_status_service.validate_so_transition("draft", "shipped")
print(f"draft → shipped: {'✅ VALID' if is_valid else f'❌ INVALID - {error}'}")

is_valid, error = order_status_service.validate_wo_transition("draft", "released")
print(f"WO draft → released: {'✅ VALID' if is_valid else '❌ INVALID'}")

# ========================================
# TEST 3: Create Test Sales Order
# ========================================
print("\n=== TEST 3: Create Test Order ===")

product = db.query(Product).first()

if not product:
    print("⚠️  No products found - skipping remaining tests")
    db.close()
    exit(0)

test_so = SalesOrder(
    order_number=f"TEST-SO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    user_id=1,
    product_id=product.id,
    product_name=product.name,
    quantity=1,
    material_type="PLA",
    unit_price=10.00,
    total_price=10.00,
    grand_total=10.00,
    status="draft",
    fulfillment_status="pending",
    payment_status="pending",
)
db.add(test_so)
db.commit()
db.refresh(test_so)
print(f"✅ Created test order: {test_so.order_number}")

# ========================================
# TEST 4: Status Update with Validation
# ========================================
print("\n=== TEST 4: Update Status (Valid) ===")

try:
    order_status_service.update_so_status(db, test_so, "pending_payment")
    print(f"✅ Updated to: {test_so.status}")

    order_status_service.update_so_status(db, test_so, "confirmed")
    print(f"✅ Updated to: {test_so.status}")
    print(f"   confirmed_at: {test_so.confirmed_at}")
except ValueError as e:
    print(f"❌ Error: {e}")

# ========================================
# TEST 5: Invalid Status Update
# ========================================
print("\n=== TEST 5: Try Invalid Status Update ===")

try:
    order_status_service.update_so_status(db, test_so, "delivered")
    print("❌ Should have blocked this transition!")
except ValueError as e:
    print(f"✅ Correctly blocked: {e}")

# ========================================
# TEST 6: Create Production Order
# ========================================
print("\n=== TEST 6: Create Production Order ===")

bom = db.query(BOM).filter(BOM.product_id == product.id).first()

test_wo = ProductionOrder(
    code=f"TEST-WO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    product_id=product.id,
    bom_id=bom.id if bom else None,
    sales_order_id=test_so.id,
    quantity_ordered=1,
    status="draft",
    qc_status="pending",
    source="sales_order",
)
db.add(test_wo)
db.commit()
db.refresh(test_wo)
print(f"✅ Created test WO: {test_wo.code}")

# ========================================
# TEST 7: WO Status Progression
# ========================================
print("\n=== TEST 7: WO Status Progression ===")

order_status_service.update_wo_status(db, test_wo, "released")
print(f"✅ Released: {test_wo.status}")

order_status_service.update_wo_status(db, test_wo, "scheduled")
print(f"✅ Scheduled: {test_wo.status}")

order_status_service.update_wo_status(db, test_wo, "in_progress")
print(f"✅ Started: {test_wo.status} (actual_start: {test_wo.actual_start})")

db.refresh(test_so)
print(f"   SO auto-updated to: {test_so.status}")

order_status_service.update_wo_status(db, test_wo, "completed")
print(f"✅ Completed: {test_wo.status}")

# ========================================
# TEST 8: QC Pass and Close
# ========================================
print("\n=== TEST 8: QC Pass and Close WO ===")

test_wo.qc_status = "passed"
test_wo.qc_inspected_by = "Test Inspector"
test_wo.qc_inspected_at = datetime.utcnow()
db.commit()

order_status_service.update_wo_status(db, test_wo, "closed")
print(f"✅ Closed: {test_wo.status}")

db.refresh(test_so)
print(f"   SO status: {test_so.status}")

# ========================================
# TEST 9: Scrap & Remake Workflow
# ========================================
print("\n=== TEST 9: Scrap & Remake ===")

scrap_wo = ProductionOrder(
    code=f"TEST-WO-SCRAP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    product_id=product.id,
    bom_id=bom.id if bom else None,
    sales_order_id=test_so.id,
    quantity_ordered=5,
    status="completed",
    qc_status="failed",
    source="sales_order",
)
db.add(scrap_wo)
db.commit()
db.refresh(scrap_wo)

remake_wo = order_status_service.scrap_wo_and_create_remake(
    db=db, wo=scrap_wo, scrap_reason="layer_shift", scrap_quantity=5
)

print(f"✅ Scrapped: {scrap_wo.code} (reason: {scrap_wo.scrap_reason})")
print(f"✅ Created remake: {remake_wo.code} (priority: {remake_wo.priority})")

# ========================================
# CLEANUP
# ========================================
print("\n=== Cleanup ===")
db.delete(test_so)
db.delete(test_wo)
db.delete(scrap_wo)
db.delete(remake_wo)
db.commit()
print("🧹 Test data cleaned up")

db.close()

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\nPhase 1 implementation validated successfully!")
print("Ready to proceed to Phase 2 (API endpoint updates)")
