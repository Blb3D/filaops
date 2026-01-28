#!/usr/bin/env python3
"""
Fix BOM Line Units Script

Updates BOM line units to match their component's inventory unit.
This fixes the "Incompatible UOM bases: EA -> KG" warnings in MRP.
"""

import sys
import os

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

print("Starting BOM Line Unit Fix Script...")
print(f"Working directory: {os.getcwd()}")

# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
print(f"Added to path: {backend_dir}")

try:
    print("Importing settings...")
    from app.core.settings import get_settings

    print("Importing models...")
    from app.models.bom import BOM, BOMLine
    from app.models.product import Product

    print("Importing SQLAlchemy...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from decimal import Decimal

    print("Imports successful!")
except Exception as e:
    print(f"Import error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# UOM conversion definitions (copied from mrp.py for standalone use)
UOM_CONVERSIONS = {
    "G": {"base": "KG", "factor": Decimal("0.001")},
    "KG": {"base": "KG", "factor": Decimal("1")},
    "LB": {"base": "KG", "factor": Decimal("0.453592")},
    "OZ": {"base": "KG", "factor": Decimal("0.0283495")},
    "MM": {"base": "M", "factor": Decimal("0.001")},
    "CM": {"base": "M", "factor": Decimal("0.01")},
    "M": {"base": "M", "factor": Decimal("1")},
    "IN": {"base": "M", "factor": Decimal("0.0254")},
    "FT": {"base": "M", "factor": Decimal("0.3048")},
    "ML": {"base": "L", "factor": Decimal("0.001")},
    "L": {"base": "L", "factor": Decimal("1")},
    "EA": {"base": "EA", "factor": Decimal("1")},
    "PK": {"base": "PK", "factor": Decimal("1")},
    "BOX": {"base": "BOX", "factor": Decimal("1")},
    "ROLL": {"base": "ROLL", "factor": Decimal("1")},
}


def get_unit_base(unit):
    """Get the base unit type for a given unit."""
    unit = (unit or "EA").upper().strip()
    info = UOM_CONVERSIONS.get(unit, {"base": unit})
    return info["base"]


def fix_bom_line_units(dry_run=True):
    """Fix BOM line units to match component inventory units."""
    print("\n" + "=" * 70)
    print("BOM Line Unit Fix Script")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will update database)'}")
    print()

    try:
        settings = get_settings()
        print("Connecting to database...")
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        print("Connected!")
    except Exception as e:
        print(f"Database connection error: {e}")
        import traceback

        traceback.print_exc()
        return

    try:
        # Find all BOM lines with mismatched units
        mismatched = []

        print("Querying BOM lines...")
        bom_lines = db.query(BOMLine).all()
        print(f"Found {len(bom_lines)} BOM lines")

        for line in bom_lines:
            component = db.query(Product).filter(Product.id == line.component_id).first()
            if not component:
                continue

            line_unit = (line.unit or "EA").upper().strip()
            component_unit = (component.unit or "EA").upper().strip()

            # Check if units are different AND incompatible bases
            if line_unit != component_unit:
                line_base = get_unit_base(line_unit)
                comp_base = get_unit_base(component_unit)

                if line_base != comp_base:
                    bom = db.query(BOM).filter(BOM.id == line.bom_id).first()
                    parent = db.query(Product).filter(Product.id == bom.product_id).first() if bom else None

                    mismatched.append(
                        {
                            "line": line,
                            "component": component,
                            "bom": bom,
                            "parent": parent,
                            "line_unit": line_unit,
                            "component_unit": component_unit,
                            "line_base": line_base,
                            "component_base": comp_base,
                        }
                    )

        if not mismatched:
            print("✓ No mismatched BOM line units found!")
            return

        print(f"Found {len(mismatched)} BOM lines with incompatible units:\n")

        for i, item in enumerate(mismatched, 1):
            line = item["line"]
            component = item["component"]
            parent = item["parent"]

            print(f"{i}. BOM Line ID {line.id}")
            print(f"   Parent Product: {parent.sku if parent else 'Unknown'} - {parent.name if parent else 'Unknown'}")
            print(f"   Component: {component.sku} - {component.name}")
            print(f"   Current: {line.quantity} {item['line_unit']} (base: {item['line_base']})")
            print(f"   Component Unit: {item['component_unit']} (base: {item['component_base']})")
            print(f"   Fix: Change line unit from {item['line_unit']} → {item['component_unit']}")
            print()

        if dry_run:
            print("-" * 70)
            print("DRY RUN - No changes made.")
            print("Run with --live to apply fixes.")
            print("-" * 70)
            return

        # Apply fixes
        print("-" * 70)
        print("Applying fixes...")
        print("-" * 70)

        fixed_count = 0
        for item in mismatched:
            line = item["line"]
            old_unit = item["line_unit"]
            new_unit = item["component_unit"]

            line.unit = new_unit
            fixed_count += 1

            print(f"  ✓ BOM Line {line.id}: {old_unit} → {new_unit}")

        db.commit()

        print()
        print("=" * 70)
        print(f"✓ Fixed {fixed_count} BOM lines")
        print("=" * 70)

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    dry_run = "--live" not in sys.argv
    fix_bom_line_units(dry_run=dry_run)
