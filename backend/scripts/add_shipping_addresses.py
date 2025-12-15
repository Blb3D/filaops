"""
Add shipping addresses to existing sales orders for testing
Run from backend directory: python scripts/add_shipping_addresses.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.sales_order import SalesOrder

# Sample addresses for testing
TEST_ADDRESSES = [
    {
        "shipping_address_line1": "123 Main Street",
        "shipping_address_line2": "Suite 100",
        "shipping_city": "Fort Wayne",
        "shipping_state": "IN",
        "shipping_zip": "46802",
        "shipping_country": "USA"
    },
    {
        "shipping_address_line1": "456 Oak Avenue",
        "shipping_address_line2": "",
        "shipping_city": "Indianapolis",
        "shipping_state": "IN",
        "shipping_zip": "46204",
        "shipping_country": "USA"
    },
    {
        "shipping_address_line1": "789 Elm Boulevard",
        "shipping_address_line2": "Apt 2B",
        "shipping_city": "Chicago",
        "shipping_state": "IL",
        "shipping_zip": "60601",
        "shipping_country": "USA"
    },
    {
        "shipping_address_line1": "321 Pine Road",
        "shipping_address_line2": "",
        "shipping_city": "Columbus",
        "shipping_state": "OH",
        "shipping_zip": "43215",
        "shipping_country": "USA"
    },
    {
        "shipping_address_line1": "555 Maple Drive",
        "shipping_address_line2": "Building C",
        "shipping_city": "Detroit",
        "shipping_state": "MI",
        "shipping_zip": "48201",
        "shipping_country": "USA"
    },
]

def main():
    db = SessionLocal()
    try:
        # Get all orders without shipping addresses
        orders = db.query(SalesOrder).filter(
            SalesOrder.shipping_address_line1.is_(None)
        ).all()
        
        print(f"Found {len(orders)} orders without shipping addresses")
        
        updated = 0
        for i, order in enumerate(orders):
            # Rotate through test addresses
            addr = TEST_ADDRESSES[i % len(TEST_ADDRESSES)]
            
            order.shipping_address_line1 = addr["shipping_address_line1"]
            order.shipping_address_line2 = addr["shipping_address_line2"]
            order.shipping_city = addr["shipping_city"]
            order.shipping_state = addr["shipping_state"]
            order.shipping_zip = addr["shipping_zip"]
            order.shipping_country = addr["shipping_country"]
            
            updated += 1
            print(f"  {order.order_number}: {addr['shipping_city']}, {addr['shipping_state']}")
        
        db.commit()
        print(f"\nUpdated {updated} orders with shipping addresses")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
