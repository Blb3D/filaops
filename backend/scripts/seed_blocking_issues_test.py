"""
Create test data for BlockingIssuesPanel verification.

This script creates a complete test scenario with:
- A finished product with BOM
- Component materials with mixed inventory levels
- A sales order and production order

Expected Results:
- 1 material PASSES (sufficient inventory)
- 2 materials FAIL (blocking issues - insufficient/zero inventory)
"""

from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os

db_password = os.environ.get("DB_PASSWORD", "Admin")
engine = create_engine(f"postgresql+psycopg://postgres:{db_password}@localhost:5432/filaops")

now = datetime.now()

with engine.connect() as conn:
    # Get user ID
    result = conn.execute(text("SELECT id FROM users LIMIT 1"))
    user_id = result.fetchone()[0]

    # Get or create a default location
    result = conn.execute(text("SELECT id FROM inventory_locations LIMIT 1"))
    loc = result.fetchone()
    if loc:
        location_id = loc[0]
    else:
        conn.execute(
            text("""
            INSERT INTO inventory_locations (name, code, active)
            VALUES ('Main Warehouse', 'WH-MAIN', true)
        """)
        )
        result = conn.execute(text("SELECT id FROM inventory_locations WHERE code = 'WH-MAIN'"))
        location_id = result.fetchone()[0]

    print(f"Using location_id: {location_id}")

    # =========================================
    # CREATE COMPONENT PRODUCTS (Raw Materials)
    # =========================================

    # Component A: Widget Frame - WILL HAVE ENOUGH INVENTORY (PASS)
    result = conn.execute(
        text("""
        INSERT INTO products (sku, name, item_type, procurement_type, type, has_bom, is_raw_material, active, created_at, updated_at, stocking_policy)
        VALUES ('COMP-FRAME-001', 'Widget Frame', 'component', 'buy', 'standard', false, true, true, :now, :now, 'on_demand')
        RETURNING id
    """),
        {"now": now},
    )
    frame_id = result.fetchone()[0]
    print(f"Created Widget Frame (id: {frame_id})")

    # Component B: Widget Motor - WILL HAVE INSUFFICIENT INVENTORY (FAIL - short)
    result = conn.execute(
        text("""
        INSERT INTO products (sku, name, item_type, procurement_type, type, has_bom, is_raw_material, active, created_at, updated_at, stocking_policy)
        VALUES ('COMP-MOTOR-001', 'Widget Motor', 'component', 'buy', 'standard', false, true, true, :now, :now, 'on_demand')
        RETURNING id
    """),
        {"now": now},
    )
    motor_id = result.fetchone()[0]
    print(f"Created Widget Motor (id: {motor_id})")

    # Component C: Widget Bolt Pack - WILL HAVE ZERO INVENTORY (FAIL - completely missing)
    result = conn.execute(
        text("""
        INSERT INTO products (sku, name, item_type, procurement_type, type, has_bom, is_raw_material, active, created_at, updated_at, stocking_policy)
        VALUES ('COMP-BOLTS-001', 'Widget Bolt Pack', 'component', 'buy', 'standard', false, true, true, :now, :now, 'on_demand')
        RETURNING id
    """),
        {"now": now},
    )
    bolts_id = result.fetchone()[0]
    print(f"Created Widget Bolt Pack (id: {bolts_id})")

    # =========================================
    # CREATE FINISHED PRODUCT (Assembly)
    # =========================================
    result = conn.execute(
        text("""
        INSERT INTO products (sku, name, item_type, procurement_type, type, has_bom, is_raw_material, active, created_at, updated_at, stocking_policy)
        VALUES ('ASSY-WIDGET-001', 'Test Assembly Widget', 'finished_good', 'make', 'standard', true, false, true, :now, :now, 'on_demand')
        RETURNING id
    """),
        {"now": now},
    )
    assembly_id = result.fetchone()[0]
    print(f"Created Test Assembly Widget (id: {assembly_id})")

    # =========================================
    # CREATE BOM
    # =========================================
    result = conn.execute(
        text("""
        INSERT INTO boms (product_id, code, name, version, active, created_at)
        VALUES (:product_id, 'BOM-WIDGET-001', 'Widget Assembly BOM', 1, true, :now)
        RETURNING id
    """),
        {"product_id": assembly_id, "now": now},
    )
    bom_id = result.fetchone()[0]
    print(f"Created BOM (id: {bom_id})")

    # =========================================
    # CREATE BOM LINES (Material Requirements)
    # =========================================
    # Frame: need 1 per unit
    conn.execute(
        text("""
        INSERT INTO bom_lines (bom_id, component_id, sequence, quantity, unit, consume_stage, is_cost_only)
        VALUES (:bom_id, :component_id, 1, 1, 'EA', 'start', false)
    """),
        {"bom_id": bom_id, "component_id": frame_id},
    )

    # Motor: need 2 per unit
    conn.execute(
        text("""
        INSERT INTO bom_lines (bom_id, component_id, sequence, quantity, unit, consume_stage, is_cost_only)
        VALUES (:bom_id, :component_id, 2, 2, 'EA', 'start', false)
    """),
        {"bom_id": bom_id, "component_id": motor_id},
    )

    # Bolts: need 4 per unit
    conn.execute(
        text("""
        INSERT INTO bom_lines (bom_id, component_id, sequence, quantity, unit, consume_stage, is_cost_only)
        VALUES (:bom_id, :component_id, 3, 4, 'EA', 'start', false)
    """),
        {"bom_id": bom_id, "component_id": bolts_id},
    )
    print("Created BOM lines (3 components)")

    # =========================================
    # CREATE INVENTORY (Mixed availability)
    # =========================================
    # Frame: 50 available (PASS - need 5 for qty 5, have 50)
    conn.execute(
        text("""
        INSERT INTO inventory (product_id, location_id, on_hand_quantity, allocated_quantity, created_at, updated_at)
        VALUES (:product_id, :location_id, 50, 0, :now, :now)
    """),
        {"product_id": frame_id, "location_id": location_id, "now": now},
    )
    print("Created inventory: Widget Frame = 50 (sufficient)")

    # Motor: 3 available (FAIL - need 10 for qty 5, only have 3, short 7)
    conn.execute(
        text("""
        INSERT INTO inventory (product_id, location_id, on_hand_quantity, allocated_quantity, created_at, updated_at)
        VALUES (:product_id, :location_id, 3, 0, :now, :now)
    """),
        {"product_id": motor_id, "location_id": location_id, "now": now},
    )
    print("Created inventory: Widget Motor = 3 (INSUFFICIENT - will be short)")

    # Bolts: 0 available (FAIL - need 20 for qty 5, have 0, short 20)
    conn.execute(
        text("""
        INSERT INTO inventory (product_id, location_id, on_hand_quantity, allocated_quantity, created_at, updated_at)
        VALUES (:product_id, :location_id, 0, 0, :now, :now)
    """),
        {"product_id": bolts_id, "location_id": location_id, "now": now},
    )
    print("Created inventory: Widget Bolt Pack = 0 (ZERO - will be blocking)")

    # =========================================
    # CREATE SALES ORDER
    # =========================================
    result = conn.execute(
        text("""
        INSERT INTO sales_orders (
            user_id, order_number, order_type, source, quantity,
            material_type, finish, unit_price, total_price, tax_amount, shipping_cost, grand_total,
            status, payment_status, fulfillment_status, rush_level,
            customer_name, customer_email, product_name, product_id,
            created_at, updated_at
        ) VALUES (
            :user_id, 'SO-TEST-BOM', 'standard', 'manual', 5,
            'PLA', 'standard', 100.00, 500.00, 0, 0, 500.00,
            'confirmed', 'paid', 'pending', 'normal',
            'Test Customer BOM', 'bom-test@example.com', 'Test Assembly Widget', :product_id,
            :now, :now
        )
        RETURNING id
    """),
        {"user_id": user_id, "product_id": assembly_id, "now": now},
    )
    so_id = result.fetchone()[0]
    print(f"Created Sales Order SO-TEST-BOM (id: {so_id})")

    # =========================================
    # CREATE PRODUCTION ORDER with BOM
    # =========================================
    result = conn.execute(
        text("""
        INSERT INTO production_orders (
            code, product_id, bom_id, sales_order_id, quantity_ordered, quantity_completed, quantity_scrapped,
            source, status, qc_status, priority, due_date,
            created_at, updated_at
        ) VALUES (
            'PO-TEST-BOM', :product_id, :bom_id, :so_id, 5, 0, 0,
            'sales_order', 'draft', 'pending', 1, :due_date,
            :now, :now
        )
        RETURNING id
    """),
        {
            "product_id": assembly_id,
            "bom_id": bom_id,
            "so_id": so_id,
            "due_date": (now + timedelta(days=7)).date(),
            "now": now,
        },
    )
    po_id = result.fetchone()[0]
    print(f"Created Production Order PO-TEST-BOM (id: {po_id})")

    conn.commit()

    print("\n" + "=" * 60)
    print("TEST DATA CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"""
SCENARIO: Build 5x Test Assembly Widgets

MATERIAL REQUIREMENTS (per unit x 5 units):
  - Widget Frame:     1 x 5 = 5 required
  - Widget Motor:     2 x 5 = 10 required
  - Widget Bolt Pack: 4 x 5 = 20 required

INVENTORY LEVELS:
  - Widget Frame:     50 available  --> PASS (5 needed, 50 have)
  - Widget Motor:      3 available  --> FAIL (10 needed, 3 have, SHORT 7)
  - Widget Bolt Pack:  0 available  --> FAIL (20 needed, 0 have, SHORT 20)

EXPECTED BLOCKING ISSUES:
  - 2 materials blocking (Motor + Bolts)
  - 1 material ready (Frame)

TO VERIFY:
  Sales Order:      /admin/orders/{so_id}
  Production Order: /admin/production/{po_id}
""")
