"""
Admin Orders Management - CSV Import
"""
import csv
import io
from typing import Optional, List
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderLine
from app.api.v1.deps import get_current_staff_user
from app.core.security import hash_password
import secrets

router = APIRouter(prefix="/orders", tags=["Admin Orders"])


# ============================================================================
# SCHEMAS
# ============================================================================

class OrderCSVImportResult(BaseModel):
    """Result of order CSV import"""
    total_rows: int
    created: int
    skipped: int
    errors: List[dict]


# ============================================================================
# CSV IMPORT
# ============================================================================

def clean_price(price_str: str) -> Optional[Decimal]:
    """Remove currency symbols and commas from price string"""
    if not price_str:
        return None
    try:
        # Remove $, commas, and whitespace
        cleaned = price_str.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return None
        return Decimal(cleaned)
    except (ValueError, TypeError, InvalidOperation):
        return None


def find_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    """Find product by SKU (case-insensitive)"""
    return db.query(Product).filter(Product.sku.ilike(sku.strip())).first()


def find_or_create_customer(db: Session, email: str, name: str = None, 
                           shipping_address: dict = None) -> Optional[User]:
    """Find existing customer by email or create new one"""
    if not email or "@" not in email:
        return None
    
    email_lower = email.lower().strip()
    
    # Try to find existing customer
    customer = db.query(User).filter(User.email.ilike(email_lower)).first()
    
    if customer:
        return customer
    
    # Create new customer
    # Split name into first/last
    first_name = ""
    last_name = ""
    if name:
        name_parts = name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    # Generate customer number
    year = datetime.now(timezone.utc).year
    last_customer = db.query(User).filter(
        User.customer_number.like(f"CUST-{year}-%")
    ).order_by(User.customer_number.desc()).first()
    
    if last_customer:
        try:
            last_num = int(last_customer.customer_number.split("-")[2])
            customer_number = f"CUST-{year}-{last_num + 1:06d}"
        except (ValueError, IndexError):
            customer_number = f"CUST-{year}-000001"
    else:
        customer_number = f"CUST-{year}-000001"
    
    now = datetime.now(timezone.utc)
    customer = User(
        customer_number=customer_number,
        email=email_lower,
        password_hash=hash_password(secrets.token_urlsafe(32)),  # Random password
        first_name=first_name or None,
        last_name=last_name or None,
        company_name=shipping_address.get("company") if shipping_address else None,
        phone=shipping_address.get("phone") if shipping_address else None,
        status="active",
        account_type="customer",
        email_verified=False,
        shipping_address_line1=shipping_address.get("line1") if shipping_address else None,
        shipping_address_line2=shipping_address.get("line2") if shipping_address else None,
        shipping_city=shipping_address.get("city") if shipping_address else None,
        shipping_state=shipping_address.get("state") if shipping_address else None,
        shipping_zip=shipping_address.get("zip") if shipping_address else None,
        shipping_country=shipping_address.get("country") or "USA",
        billing_address_line1=shipping_address.get("line1") if shipping_address else None,
        billing_address_line2=shipping_address.get("line2") if shipping_address else None,
        billing_city=shipping_address.get("city") if shipping_address else None,
        billing_state=shipping_address.get("state") if shipping_address else None,
        billing_zip=shipping_address.get("zip") if shipping_address else None,
        billing_country=shipping_address.get("country") or "USA",
        created_at=now,
        updated_at=now
    )
    db.add(customer)
    db.flush()
    return customer


@router.get("/import/template")
async def download_order_import_template():
    """
    Download CSV template for order import.
    
    Template format supports single-line orders (one product per order) or
    multi-line orders (multiple products per order using Order ID grouping).
    """
    template = """Order ID,Order Date,Order Status,Payment Status,Customer Email,Customer Name,Product SKU,Quantity,Unit Price,Shipping Cost,Tax Amount,Shipping Address Line 1,Shipping City,Shipping State,Shipping Zip,Shipping Country,Customer Notes
ORD-001,2025-01-15,pending,paid,customer@example.com,John Doe,PROD-001,2,19.99,5.00,2.00,123 Main St,New York,NY,10001,USA,Please handle with care
ORD-002,2025-01-16,processing,paid,jane@example.com,Jane Smith,PROD-002,1,29.99,7.50,2.25,456 Oak Ave,Los Angeles,CA,90001,USA,"""
    
    return StreamingResponse(
        io.BytesIO(template.encode('utf-8')),
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=order_import_template.csv"}
    )


@router.post("/import", response_model=OrderCSVImportResult)
async def import_orders_csv(
    file: UploadFile = File(...),
    create_customers: bool = Query(True, description="Create customers if they don't exist"),
    source: str = Query("manual", description="Order source: manual, squarespace, shopify, woocommerce, etsy, tiktok"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_user),
):
    """
    Import orders from CSV file.
    
    Supports single-line orders (one product per row) or multi-line orders
    (multiple products per order, grouped by Order ID).
    
    Expected CSV format:
    - Order ID: Unique order identifier (required for multi-line orders)
    - Order Date: Order date (YYYY-MM-DD)
    - Customer Email: Customer email (required)
    - Customer Name: Customer full name
    - Product SKU: Product SKU (required)
    - Quantity: Quantity ordered (required)
    - Unit Price: Price per unit (optional, uses product price if not provided)
    - Shipping Cost: Shipping cost (optional)
    - Tax Amount: Tax amount (optional)
    - Shipping Address: Full shipping address fields
    
    Creates:
    - Customers (if create_customers=True and customer doesn't exist)
    - Sales Orders with line items
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    
    # Handle BOM
    if text.startswith('\ufeff'):
        text = text[1:]
    
    reader = csv.DictReader(io.StringIO(text))
    
    result = OrderCSVImportResult(
        total_rows=0,
        created=0,
        skipped=0,
        errors=[],
    )
    
    # Column name variations
    ORDER_ID_COLS = ["order id", "Order ID", "order_id", "Order_ID", "Order Number", "order_number", "Order #", "Order#"]
    ORDER_DATE_COLS = ["order date", "Order Date", "order_date", "Date", "date", "Order Date/Time"]
    CUSTOMER_EMAIL_COLS = ["customer email", "Customer Email", "customer_email", "Email", "email", "Buyer Email", "buyer_email"]
    CUSTOMER_NAME_COLS = ["customer name", "Customer Name", "customer_name", "Name", "name", "Buyer Name", "buyer_name", "Shipping Name", "shipping name"]
    PRODUCT_SKU_COLS = ["product sku", "Product SKU", "product_sku", "SKU", "sku", "Variant SKU", "variant_sku", "Item SKU", "item_sku"]
    QUANTITY_COLS = ["quantity", "Quantity", "Qty", "qty", "QTY"]
    UNIT_PRICE_COLS = ["unit price", "Unit Price", "unit_price", "Price", "price", "Item Price", "item_price"]
    SHIPPING_COST_COLS = ["shipping cost", "Shipping Cost", "shipping_cost", "Shipping", "shipping"]
    TAX_COLS = ["tax amount", "Tax Amount", "tax_amount", "Tax", "tax"]
    SHIP_LINE1_COLS = ["shipping address line 1", "Shipping Address Line 1", "shipping_address_line1", "Shipping Address", "shipping address"]
    SHIP_CITY_COLS = ["shipping city", "Shipping City", "shipping_city", "City", "city"]
    SHIP_STATE_COLS = ["shipping state", "Shipping State", "shipping_state", "State", "state"]
    SHIP_ZIP_COLS = ["shipping zip", "Shipping Zip", "shipping_zip", "Zip", "zip", "Postal Code", "postal_code"]
    SHIP_COUNTRY_COLS = ["shipping country", "Shipping Country", "shipping_country", "Country", "country"]
    NOTES_COLS = ["customer notes", "Customer Notes", "customer_notes", "Notes", "notes", "Order Notes"]
    
    # Group rows by Order ID (for multi-line orders)
    orders_dict = {}
    
    for row_num, row in enumerate(reader, start=2):
        result.total_rows += 1
        
        try:
            # Find order ID
            order_id = ""
            for col in ORDER_ID_COLS:
                if row.get(col, "").strip():
                    order_id = row.get(col, "").strip()
                    break
            
            # If no order ID, use row number as order ID (single-line orders)
            if not order_id:
                order_id = f"IMPORT-{row_num}"
            
            # Find customer email (optional - will create placeholder if missing)
            customer_email = ""
            for col in CUSTOMER_EMAIL_COLS:
                if row.get(col, "").strip():
                    customer_email = row.get(col, "").strip().lower()
                    break
            
            # If no email, create placeholder email (will be handled during order creation)
            if not customer_email or "@" not in customer_email:
                customer_email = f"import-{order_id.lower().replace(' ', '-')}@placeholder.local"
            
            # Find product SKU (optional - line item will be skipped if missing)
            product_sku = ""
            for col in PRODUCT_SKU_COLS:
                if row.get(col, "").strip():
                    product_sku = row.get(col, "").strip()
                    break
            
            # Skip line item if no SKU, but continue processing order
            if not product_sku:
                result.errors.append({
                    "row": row_num,
                    "error": "Product SKU missing - line item skipped",
                    "order_id": order_id
                })
                # Don't add this line to the order, but continue processing
                continue
            
            # Find quantity
            quantity = 1
            for col in QUANTITY_COLS:
                if row.get(col, "").strip():
                    try:
                        quantity = int(float(row.get(col, "").strip().replace(",", "")))
                        if quantity <= 0:
                            quantity = 1
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Find unit price
            unit_price = None
            for col in UNIT_PRICE_COLS:
                if row.get(col, "").strip():
                    unit_price = clean_price(row.get(col, "").strip())
                    break
            
            # Find shipping cost
            shipping_cost = Decimal("0.00")
            for col in SHIPPING_COST_COLS:
                if row.get(col, "").strip():
                    cost = clean_price(row.get(col, "").strip())
                    if cost:
                        shipping_cost = cost
                    break
            
            # Find tax amount
            tax_amount = Decimal("0.00")
            for col in TAX_COLS:
                if row.get(col, "").strip():
                    tax = clean_price(row.get(col, "").strip())
                    if tax:
                        tax_amount = tax
                    break
            
            # Find customer name
            customer_name = ""
            for col in CUSTOMER_NAME_COLS:
                if row.get(col, "").strip():
                    customer_name = row.get(col, "").strip()
                    break
            
            # Find shipping address
            shipping_address = {}
            for col in SHIP_LINE1_COLS:
                if row.get(col, "").strip():
                    shipping_address["line1"] = row.get(col, "").strip()
                    break
            for col in SHIP_CITY_COLS:
                if row.get(col, "").strip():
                    shipping_address["city"] = row.get(col, "").strip()
                    break
            for col in SHIP_STATE_COLS:
                if row.get(col, "").strip():
                    shipping_address["state"] = row.get(col, "").strip()
                    break
            for col in SHIP_ZIP_COLS:
                if row.get(col, "").strip():
                    shipping_address["zip"] = row.get(col, "").strip()
                    break
            for col in SHIP_COUNTRY_COLS:
                if row.get(col, "").strip():
                    shipping_address["country"] = row.get(col, "").strip()
                    break
            
            # Find notes
            notes = ""
            for col in NOTES_COLS:
                if row.get(col, "").strip():
                    notes = row.get(col, "").strip()
                    break
            
            # Add to orders dictionary
            if order_id not in orders_dict:
                orders_dict[order_id] = {
                    "customer_email": customer_email,
                    "customer_name": customer_name,
                    "shipping_address": shipping_address,
                    "shipping_cost": shipping_cost,
                    "tax_amount": tax_amount,
                    "notes": notes,
                    "lines": []
                }
            
            orders_dict[order_id]["lines"].append({
                "sku": product_sku,
                "quantity": quantity,
                "unit_price": unit_price
            })
            
        except Exception as e:
            result.errors.append({
                "row": row_num,
                "error": str(e),
                "order_id": order_id if 'order_id' in locals() else ""
            })
            result.skipped += 1
    
    # Process each order
    for order_id, order_data in orders_dict.items():
        try:
            # Find or create customer
            customer = None
            if create_customers:
                customer = find_or_create_customer(
                    db,
                    order_data["customer_email"],
                    order_data["customer_name"],
                    order_data["shipping_address"]
                )
            else:
                customer = db.query(User).filter(
                    User.email.ilike(order_data["customer_email"])
                ).first()
            
            if not customer:
                # If placeholder email and create_customers is False, skip order
                if "@placeholder.local" in order_data["customer_email"] and not create_customers:
                    result.errors.append({
                        "order_id": order_id,
                        "error": "Customer email missing and create_customers=false - order skipped"
                    })
                    result.skipped += 1
                    continue
                # Otherwise, try to create customer (should have been created above)
                result.errors.append({
                    "order_id": order_id,
                    "error": f"Customer not found: {order_data['customer_email']} (set create_customers=true to auto-create)"
                })
                result.skipped += 1
                continue
            
            # Process order lines
            line_products = []
            total_price = Decimal("0.00")
            total_quantity = 0
            
            for line in order_data["lines"]:
                product = find_product_by_sku(db, line["sku"])
                
                if not product:
                    result.errors.append({
                        "order_id": order_id,
                        "error": f"Product not found: {line['sku']}"
                    })
                    continue
                
                if not product.active:
                    result.errors.append({
                        "order_id": order_id,
                        "error": f"Product '{line['sku']}' is inactive"
                    })
                    continue
                
                # Use provided price or product price
                unit_price = line["unit_price"] or product.selling_price or Decimal("0.00")
                if unit_price <= 0:
                    result.errors.append({
                        "order_id": order_id,
                        "error": f"Product '{line['sku']}' has no price"
                    })
                    continue
                
                line_total = unit_price * line["quantity"]
                line_products.append({
                    "product": product,
                    "quantity": line["quantity"],
                    "unit_price": unit_price,
                    "line_total": line_total
                })
                
                total_price += line_total
                total_quantity += line["quantity"]
            
            if not line_products:
                result.errors.append({
                    "order_id": order_id,
                    "error": "No valid products found for order"
                })
                result.skipped += 1
                continue
            
            # Check if order already exists (by source_order_id)
            existing_order = db.query(SalesOrder).filter(
                SalesOrder.source_order_id == order_id
            ).first()
            
            if existing_order:
                result.errors.append({
                    "order_id": order_id,
                    "error": f"Order already exists: {existing_order.order_number}"
                })
                result.skipped += 1
                continue
            
            # Generate order number
            year = datetime.now(timezone.utc).year
            last_order = db.query(SalesOrder).filter(
                SalesOrder.order_number.like(f"SO-{year}-%")
            ).order_by(SalesOrder.order_number.desc()).first()
            
            if last_order:
                try:
                    last_num = int(last_order.order_number.split("-")[2])
                    order_number = f"SO-{year}-{last_num + 1:06d}"
                except (ValueError, IndexError):
                    order_number = f"SO-{year}-000001"
            else:
                order_number = f"SO-{year}-000001"
            
            # Calculate totals
            shipping_cost = order_data["shipping_cost"]
            tax_amount = order_data["tax_amount"]
            grand_total = total_price + shipping_cost + tax_amount
            
            # Get shipping address from customer or order data
            shipping_address = order_data["shipping_address"]
            shipping_line1 = shipping_address.get("line1") or customer.shipping_address_line1
            shipping_city = shipping_address.get("city") or customer.shipping_city
            shipping_state = shipping_address.get("state") or customer.shipping_state
            shipping_zip = shipping_address.get("zip") or customer.shipping_zip
            shipping_country = shipping_address.get("country") or customer.shipping_country or "USA"
            
            # Create sales order
            sales_order = SalesOrder(
                user_id=customer.id,
                order_number=order_number,
                order_type="line_item",
                source=source,
                source_order_id=order_id,
                product_name=line_products[0]["product"].name if line_products else "Imported Order",
                quantity=total_quantity,
                material_type="PLA",  # Default, can be updated later
                finish="standard",
                unit_price=total_price / total_quantity if total_quantity > 0 else Decimal("0.00"),
                total_price=total_price,
                tax_amount=tax_amount,
                shipping_cost=shipping_cost,
                grand_total=grand_total,
                status="pending",
                payment_status="pending",
                rush_level="standard",
                shipping_address_line1=shipping_line1,
                shipping_address_line2=None,
                shipping_city=shipping_city,
                shipping_state=shipping_state,
                shipping_zip=shipping_zip,
                shipping_country=shipping_country,
                customer_notes=order_data["notes"],
                internal_notes=f"Imported from {source} CSV",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(sales_order)
            db.flush()
            
            # Create order lines
            for line_data in line_products:
                order_line = SalesOrderLine(
                    sales_order_id=sales_order.id,
                    product_id=line_data["product"].id,
                    quantity=line_data["quantity"],
                    unit_price=line_data["unit_price"],
                    total=line_data["line_total"],
                    discount=Decimal("0.00"),
                    tax_rate=Decimal("0.00"),
                    notes=None,
                    created_by=current_user.id
                )
                db.add(order_line)
            
            db.commit()
            result.created += 1
            
        except Exception as e:
            db.rollback()
            result.errors.append({
                "order_id": order_id,
                "error": str(e)
            })
            result.skipped += 1
    
    return result

