"""
Clear Test Data Script

Safely removes test data created by test_order_to_ship_workflow.py
This script only deletes data with TEST- prefixes to avoid affecting production data.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import SessionLocal
from app.models.product import Product
from app.models.bom import BOM, BOMLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.models.production_order import ProductionOrder
from app.models.inventory import Inventory, InventoryTransaction
from app.models.payment import Payment
from app.models.user import User
from app.models.work_center import WorkCenter
# Note: Routing imports removed to avoid table redefinition error
# We'll query them dynamically instead


def clear_test_data():
    """Clear all test data"""
    print("\n" + "=" * 60)
    print("CLEARING TEST DATA")
    print("=" * 60)
    print("\nThis will delete:")
    print("  - Products with SKU starting with 'TEST-'")
    print("  - Purchase Orders with PO number starting with 'PO-TEST-'")
    print("  - Sales Orders with order number starting with 'SO-TEST-'")
    print("  - Production Orders related to test sales orders")
    print("  - Payments related to test sales orders")
    print("  - Test user (test-customer@test.com)")
    print("  - Test work centers (TEST-*)")
    print("  - Test routings for test products")
    print("  - Inventory transactions for test data")
    print("  - Inventory for test products")
    print("\n⚠️  This will NOT delete:")
    print("  - Admin users")
    print("  - Company settings")
    print("  - Scrap reasons (these are shared)")
    print("  - Production data")
    print("\nReady to proceed? (Type 'yes' to continue or anything else to cancel)")

    try:
        confirmation = input().strip().lower()
        if confirmation != "yes":
            print("\nCancelled.")
            return
    except KeyboardInterrupt:
        print("\nCancelled.")
        return

    db: Session = SessionLocal()

    try:
        # Get test products first (we'll need their IDs)
        test_products = db.query(Product).filter(Product.sku.like("TEST-%")).all()
        test_product_ids = [p.id for p in test_products]

        # Delete in reverse order of dependencies

        # 1. Inventory Transactions (references everything)
        print("\n[1/10] Deleting inventory transactions...")
        test_txns = (
            db.query(InventoryTransaction)
            .filter(
                or_(
                    InventoryTransaction.product_id.in_(test_product_ids) if test_product_ids else False,
                    InventoryTransaction.reference_type == "purchase_order",
                    InventoryTransaction.reference_type == "sales_order",
                    InventoryTransaction.reference_type == "production_order",
                )
            )
            .all()
        )
        for txn in test_txns:
            # Check if it's test-related
            is_test = False
            if txn.product_id in test_product_ids:
                is_test = True
            elif txn.reference_type == "purchase_order":
                po = db.query(PurchaseOrder).filter(PurchaseOrder.id == txn.reference_id).first()
                if po and po.po_number and po.po_number.startswith("PO-TEST-"):
                    is_test = True
            elif txn.reference_type == "sales_order":
                so = db.query(SalesOrder).filter(SalesOrder.id == txn.reference_id).first()
                if so and so.order_number and so.order_number.startswith("SO-TEST-"):
                    is_test = True
            elif txn.reference_type == "production_order":
                po = db.query(ProductionOrder).filter(ProductionOrder.id == txn.reference_id).first()
                if po and po.code and po.code.startswith("WO-SO-TEST-"):
                    is_test = True

            if is_test:
                db.delete(txn)
        print(f"  [OK] Deleted {len([t for t in test_txns if True])} transactions")

        # 2. Inventory for test products
        print("\n[2/10] Deleting inventory for test products...")
        test_inventory = db.query(Inventory).filter(Inventory.product_id.in_(test_product_ids)).all()
        for inv in test_inventory:
            db.delete(inv)
        print(f"  [OK] Deleted {len(test_inventory)} inventory records")

        # 3. Production Orders (references BOM, Sales Order)
        print("\n[3/10] Deleting production orders...")
        test_sos = db.query(SalesOrder).filter(SalesOrder.order_number.like("SO-TEST-%")).all()
        test_so_ids = [so.id for so in test_sos]
        test_pos = db.query(ProductionOrder).filter(ProductionOrder.sales_order_id.in_(test_so_ids)).all()
        for po in test_pos:
            db.delete(po)
        print(f"  [OK] Deleted {len(test_pos)} production orders")

        # 4. Payments (references Sales Order)
        print("\n[4/10] Deleting payments...")
        test_payments = db.query(Payment).filter(Payment.sales_order_id.in_(test_so_ids)).all()
        for payment in test_payments:
            db.delete(payment)
        print(f"  [OK] Deleted {len(test_payments)} payments")

        # 5. Sales Order Lines
        print("\n[5/10] Deleting sales order lines...")
        test_solines = db.query(SalesOrderLine).filter(SalesOrderLine.sales_order_id.in_(test_so_ids)).all()
        for line in test_solines:
            db.delete(line)
        print(f"  [OK] Deleted {len(test_solines)} sales order lines")

        # 6. Sales Orders
        print("\n[6/10] Deleting sales orders...")
        for so in test_sos:
            db.delete(so)
        print(f"  [OK] Deleted {len(test_sos)} sales orders")

        # 7. Purchase Order Lines
        print("\n[7/10] Deleting purchase order lines...")
        test_pos_po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.like("PO-TEST-%")).all()
        test_po_ids = [po.id for po in test_pos_po]
        test_polines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.purchase_order_id.in_(test_po_ids)).all()
        for line in test_polines:
            db.delete(line)
        print(f"  [OK] Deleted {len(test_polines)} purchase order lines")

        # 8. Purchase Orders
        print("\n[8/10] Deleting purchase orders...")
        for po in test_pos_po:
            db.delete(po)
        print(f"  [OK] Deleted {len(test_pos_po)} purchase orders")

        # 9. BOM Lines and BOMs
        print("\n[9/10] Deleting BOMs...")
        test_boms = db.query(BOM).filter(BOM.product_id.in_(test_product_ids)).all()
        test_bom_ids = [bom.id for bom in test_boms]
        test_bom_lines = db.query(BOMLine).filter(BOMLine.bom_id.in_(test_bom_ids)).all()
        for line in test_bom_lines:
            db.delete(line)
        for bom in test_boms:
            db.delete(bom)
        print(f"  [OK] Deleted {len(test_bom_lines)} BOM lines and {len(test_boms)} BOMs")

        # 10. Routings for test products (query dynamically to avoid import issues)
        print("\n[10/11] Deleting routings...")
        try:
            # Import here to avoid table redefinition issues
            from app.models.manufacturing import Routing, RoutingOperation

            test_routings = db.query(Routing).filter(Routing.product_id.in_(test_product_ids)).all()
            test_routing_ids = [r.id for r in test_routings]
            test_routing_ops = (
                db.query(RoutingOperation).filter(RoutingOperation.routing_id.in_(test_routing_ids)).all()
            )
            for op in test_routing_ops:
                db.delete(op)
            for routing in test_routings:
                db.delete(routing)
            print(f"  [OK] Deleted {len(test_routing_ops)} routing operations and {len(test_routings)} routings")
        except Exception as e:
            print(f"  [SKIP] Could not delete routings: {e}")
            print("         (This is OK - routings may not exist or may be shared)")

        # 11. Products
        print("\n[11/11] Deleting products...")
        for product in test_products:
            db.delete(product)
        print(f"  [OK] Deleted {len(test_products)} products")

        # 12. Test user (optional - only if email is test-customer@test.com)
        print("\n[12/12] Checking for test user...")
        test_user = db.query(User).filter(User.email == "test-customer@test.com").first()
        if test_user:
            # Check if user has any other orders
            other_orders = (
                db.query(SalesOrder)
                .filter(SalesOrder.user_id == test_user.id, ~SalesOrder.order_number.like("SO-TEST-%"))
                .count()
            )
            if other_orders == 0:
                db.delete(test_user)
                print("  [OK] Deleted test user")
            else:
                print(f"  [SKIP] Test user has {other_orders} non-test orders, keeping user")
        else:
            print("  [SKIP] Test user not found")

        # 13. Test work centers (TEST-*)
        print("\n[13/13] Deleting test work centers...")
        test_wcs = db.query(WorkCenter).filter(WorkCenter.code.like("TEST-%")).all()
        for wc in test_wcs:
            db.delete(wc)
        print(f"  [OK] Deleted {len(test_wcs)} work centers")

        db.commit()

        print("\n" + "=" * 60)
        print("[OK] Test data cleared successfully!")
        print("=" * 60)
        print("\nYou can now run the test workflow script again:")
        print("  python -m scripts.test_order_to_ship_workflow")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Failed to clear test data: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_test_data()
