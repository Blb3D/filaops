"""
Fix Work Center Type Script

Updates work centers with invalid center_type="production" to center_type="machine"
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.work_center import WorkCenter


def fix_work_center_types():
    """Update work centers with invalid center_type"""
    db: Session = SessionLocal()
    try:
        # Find work centers with invalid "production" type
        invalid_wcs = db.query(WorkCenter).filter(WorkCenter.center_type == "production").all()

        if not invalid_wcs:
            print("No work centers with invalid 'production' type found.")
            return

        print(f"\nFound {len(invalid_wcs)} work center(s) with invalid type 'production':")
        for wc in invalid_wcs:
            print(f"  - {wc.code}: {wc.name} (has {len(wc.resources) if wc.resources else 0} resources)")

        # Update to "machine" type (most common for work centers with resources)
        for wc in invalid_wcs:
            wc.center_type = "machine"
            print(f"  [OK] Updated {wc.code} to center_type='machine'")

        db.commit()
        print(f"\n✅ Successfully updated {len(invalid_wcs)} work center(s)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    fix_work_center_types()
