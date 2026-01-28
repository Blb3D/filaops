"""
Import functionality for products, inventory
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import csv
import io

from app.db.session import get_db
from app.api.v1.deps import get_current_staff_user
from app.models.user import User
from app.models.product import Product
from app.models.inventory import Inventory, InventoryLocation
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/products")
async def import_products(
    file: UploadFile = File(...), current_user: User = Depends(get_current_staff_user), db: Session = Depends(get_db)
):
    """Import products from CSV"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Handle BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    csv_content = io.StringIO(text)
    reader = csv.DictReader(csv_content)

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            sku = row.get("SKU", "").strip()
            if not sku:
                errors.append(f"Row {row_num}: Missing SKU")
                continue

            # Check if product exists
            product = db.query(Product).filter(Product.sku == sku).first()

            if product:
                # Update existing
                product.name = row.get("Name", product.name)
                product.description = row.get("Description", product.description)
                product.item_type = row.get("Item Type", product.item_type)
                product.procurement_type = row.get("Procurement Type", product.procurement_type)
                product.unit = row.get("Unit", product.unit)
                if row.get("Standard Cost"):
                    product.standard_cost = float(row.get("Standard Cost"))
                if row.get("Selling Price"):
                    product.selling_price = float(row.get("Selling Price"))
                if row.get("Reorder Point"):
                    product.reorder_point = float(row.get("Reorder Point"))
                product.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Create new
                now = datetime.now(timezone.utc)
                product = Product(
                    sku=sku,
                    name=row.get("Name", ""),
                    description=row.get("Description"),
                    item_type=row.get("Item Type", "finished_good"),
                    procurement_type=row.get("Procurement Type", "buy"),
                    unit=row.get("Unit", "EA"),
                    standard_cost=float(row.get("Standard Cost", 0)) if row.get("Standard Cost") else None,
                    selling_price=float(row.get("Selling Price", 0)) if row.get("Selling Price") else None,
                    reorder_point=float(row.get("Reorder Point", 0)) if row.get("Reorder Point") else None,
                    active=row.get("Active", "true").lower() == "true",
                    created_at=now,
                    updated_at=now,
                )
                db.add(product)
                created += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(f"Database error: {str(e)}")

    return {"created": created, "updated": updated, "errors": errors, "total_processed": created + updated}


@router.post("/inventory")
async def import_inventory(
    file: UploadFile = File(...), current_user: User = Depends(get_current_staff_user), db: Session = Depends(get_db)
):
    """
    Import inventory from CSV.

    Expected columns:
    - SKU (required): Product SKU
    - Quantity (required): Quantity to set/add
    - Location: Warehouse/location code (defaults to MAIN)
    - Lot Number: Lot number for tracking (optional)
    - Mode: 'set' to set quantity, 'add' to add to existing (default: set)
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Handle BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    csv_content = io.StringIO(text)
    reader = csv.DictReader(csv_content)

    created = 0
    updated = 0
    errors = []

    # Column name variations
    SKU_COLS = ["SKU", "sku", "Product SKU", "product_sku", "Item SKU"]
    QTY_COLS = ["Quantity", "quantity", "Qty", "qty", "QTY", "On Hand", "on_hand"]
    LOC_COLS = ["Location", "location", "Warehouse", "warehouse", "Location Code"]
    LOT_COLS = ["Lot Number", "lot_number", "Lot", "lot", "Lot #"]
    MODE_COLS = ["Mode", "mode", "Action", "action"]

    # Get or create default location
    default_location = db.query(InventoryLocation).filter(InventoryLocation.code == "MAIN").first()
    if not default_location:
        default_location = InventoryLocation(code="MAIN", name="Main Warehouse", type="warehouse", active=True)
        db.add(default_location)
        db.flush()

    for row_num, row in enumerate(reader, start=2):
        try:
            # Find SKU
            sku = None
            for col in SKU_COLS:
                if row.get(col, "").strip():
                    sku = row.get(col, "").strip()
                    break

            if not sku:
                errors.append(f"Row {row_num}: Missing SKU")
                continue

            # Look up product
            product = db.query(Product).filter(Product.sku == sku).first()
            if not product:
                errors.append(f"Row {row_num}: Product with SKU '{sku}' not found")
                continue

            # Find quantity
            quantity = None
            quantity_error = False
            for col in QTY_COLS:
                if row.get(col, "").strip():
                    try:
                        quantity = Decimal(row.get(col, "").strip())
                    except InvalidOperation:
                        errors.append(f"Row {row_num}: Invalid quantity")
                        quantity_error = True
                    break

            if quantity_error:
                continue

            if quantity is None:
                errors.append(f"Row {row_num}: Missing quantity")
                continue

            # Find location
            location_code = "MAIN"
            for col in LOC_COLS:
                if row.get(col, "").strip():
                    location_code = row.get(col, "").strip()
                    break

            location = db.query(InventoryLocation).filter(InventoryLocation.code == location_code).first()
            if not location:
                location = default_location

            # Find lot number (parsed for future lot tracking support)
            _lot_number = None  # noqa: F841 - placeholder for lot tracking feature
            for col in LOT_COLS:
                if row.get(col, "").strip():
                    _lot_number = row.get(col, "").strip()
                    break

            # Find mode (set or add)
            mode = "set"
            for col in MODE_COLS:
                if row.get(col, "").strip().lower() in ["add", "set"]:
                    mode = row.get(col, "").strip().lower()
                    break

            # Find or create inventory record
            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == product.id, Inventory.location_id == location.id)
                .first()
            )

            if inventory:
                if mode == "add":
                    inventory.on_hand_quantity = (inventory.on_hand_quantity or Decimal("0")) + quantity
                else:
                    inventory.on_hand_quantity = quantity
                # available_quantity is computed, just update on_hand
                inventory.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                inventory = Inventory(
                    product_id=product.id,
                    location_id=location.id,
                    on_hand_quantity=quantity,
                    allocated_quantity=Decimal("0"),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(inventory)
                created += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(f"Database error: {str(e)}")

    return {"created": created, "updated": updated, "errors": errors, "total_processed": created + updated}
