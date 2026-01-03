"""
Test script to verify the purchase_uom fix for cost calculations.

Run this after applying the migration to ensure costs are calculated correctly.
"""
import sys
sys.path.insert(0, '.')

from decimal import Decimal
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import Product
from app.services.inventory_service import (
    get_effective_cost,
    get_effective_cost_per_inventory_unit,
)


def test_cost_conversion():
    """Test that cost conversion works correctly for filaments."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("TESTING PURCHASE_UOM COST CONVERSION")
        print("=" * 60)
        
        # Find a filament product
        filament = db.query(Product).filter(
            Product.sku.like('MAT-%'),
            Product.purchase_uom == 'KG',
            Product.unit == 'G',
            Product.standard_cost.isnot(None)
        ).first()
        
        if not filament:
            print("ERROR: No filament product found with purchase_uom='KG' and unit='G'")
            print("Run the migration first!")
            return False
        
        print(f"\nTest Product: {filament.sku}")
        print(f"  Name: {filament.name}")
        print(f"  purchase_uom: {filament.purchase_uom}")
        print(f"  unit (storage): {filament.unit}")
        print(f"  standard_cost: ${filament.standard_cost}/KG")
        
        # Get effective costs
        base_cost = get_effective_cost(filament)
        cost_per_storage = get_effective_cost_per_inventory_unit(filament)
        
        print(f"\nCost Calculations:")
        print(f"  Base cost ($/purchase_uom): ${base_cost}")
        print(f"  Cost per storage unit ($/G): ${cost_per_storage}")
        
        # Verify conversion
        expected_per_gram = Decimal(str(filament.standard_cost)) / Decimal('1000')
        
        if cost_per_storage is None:
            print("\nERROR: cost_per_storage is None!")
            return False
        
        # Allow for small floating point differences
        diff = abs(float(cost_per_storage) - float(expected_per_gram))
        if diff > 0.0001:
            print(f"\nERROR: Cost conversion incorrect!")
            print(f"  Expected: ${expected_per_gram}/G")
            print(f"  Got: ${cost_per_storage}/G")
            return False
        
        print(f"\n✓ PASSED: Cost correctly converted from $/KG to $/G")
        
        # Test a sample transaction calculation
        test_grams = Decimal('1000')  # 1 KG
        transaction_cost = test_grams * cost_per_storage
        
        print(f"\nSample Transaction:")
        print(f"  Quantity: {test_grams} G (1 KG)")
        print(f"  Cost: {test_grams} G × ${cost_per_storage}/G = ${transaction_cost}")
        print(f"  Expected: ${filament.standard_cost} (1 KG worth)")
        
        expected_cost = Decimal(str(filament.standard_cost))
        if abs(float(transaction_cost) - float(expected_cost)) > 0.01:
            print(f"\nERROR: Transaction cost mismatch!")
            return False
        
        print(f"\n✓ PASSED: Transaction cost matches expected value")
        
        # Test a hardware product (should NOT convert)
        hardware = db.query(Product).filter(
            Product.sku.like('HW-%'),
            Product.purchase_uom == 'EA',
            Product.unit == 'EA',
        ).first()
        
        if hardware and hardware.standard_cost:
            print(f"\n\nTest Hardware Product: {hardware.sku}")
            print(f"  purchase_uom: {hardware.purchase_uom}")
            print(f"  unit (storage): {hardware.unit}")
            print(f"  standard_cost: ${hardware.standard_cost}/EA")
            
            hw_cost_per_storage = get_effective_cost_per_inventory_unit(hardware)
            print(f"  Cost per storage unit: ${hw_cost_per_storage}/EA")
            
            if hw_cost_per_storage != hardware.standard_cost:
                print(f"\nERROR: Hardware cost should NOT be converted!")
                return False
            
            print(f"\n✓ PASSED: Hardware cost unchanged (no conversion needed)")
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    finally:
        db.close()


def show_product_uom_summary():
    """Show summary of all products with their UOM configuration."""
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 60)
        print("PRODUCT UOM SUMMARY")
        print("=" * 60)
        
        # Query products grouped by purchase_uom/unit combination
        products = db.query(Product).filter(Product.active == True).all()
        
        # Group by UOM configuration
        groups = {}
        for p in products:
            key = f"{p.purchase_uom or 'NULL'}/{p.unit or 'NULL'}"
            if key not in groups:
                groups[key] = []
            groups[key].append(p)
        
        for key, items in sorted(groups.items()):
            purchase, storage = key.split('/')
            print(f"\n{key} ({len(items)} products)")
            print(f"  Purchase UOM: {purchase}, Storage UOM: {storage}")
            if purchase != storage:
                print(f"  → Cost conversion REQUIRED")
            else:
                print(f"  → No conversion needed")
            
            # Show first 3 examples
            for p in items[:3]:
                cost = p.standard_cost or p.average_cost or 0
                print(f"    - {p.sku}: ${cost}/{purchase}")
        
    finally:
        db.close()


if __name__ == '__main__':
    show_product_uom_summary()
    print()
    success = test_cost_conversion()
    sys.exit(0 if success else 1)
