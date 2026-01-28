"""
Backfill received_date for Purchase Orders

This script fixes POs that have 'received' or 'closed' status but NULL received_date.
These were likely created before the received_date field was properly populated.

The script will:
1. Find all POs with status 'received' or 'closed' and NULL received_date
2. Set received_date to:
   - expected_date if available
   - order_date if no expected_date
   - updated_at date as last resort
"""

import sys

sys.path.insert(0, "c:/repos/filaops/backend")

from datetime import date
from sqlalchemy import text
from app.db.session import SessionLocal


def backfill_received_dates():
    db = SessionLocal()
    try:
        # Find POs needing backfill
        result = db.execute(
            text("""
            SELECT id, po_number, status, order_date, expected_date, updated_at
            FROM purchase_orders
            WHERE status IN ('received', 'closed')
              AND received_date IS NULL
        """)
        )

        pos_to_update = result.fetchall()

        if not pos_to_update:
            print("No POs found needing backfill. All received/closed POs have received_date set.")
            return

        print(f"Found {len(pos_to_update)} POs needing received_date backfill:\n")

        for po in pos_to_update:
            po_id, po_number, status, order_date, expected_date, updated_at = po

            # Determine which date to use
            if expected_date:
                backfill_date = expected_date
                source = "expected_date"
            elif order_date:
                backfill_date = order_date
                source = "order_date"
            elif updated_at:
                backfill_date = updated_at.date() if hasattr(updated_at, "date") else date.today()
                source = "updated_at"
            else:
                backfill_date = date.today()
                source = "today (fallback)"

            print(f"  {po_number} ({status}): setting received_date = {backfill_date} (from {source})")

            # Update the PO
            db.execute(
                text("UPDATE purchase_orders SET received_date = :received_date WHERE id = :id"),
                {"received_date": backfill_date, "id": po_id},
            )

        db.commit()
        print(f"\n✓ Successfully updated {len(pos_to_update)} POs with received_date")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("PO Received Date Backfill Script")
    print("=" * 60)
    print()
    backfill_received_dates()
