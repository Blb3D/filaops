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
from datetime import datetime, timezone

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/products")
async def import_products(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """Import products from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    content = await file.read()
    csv_content = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_content)
    
    created = 0
    updated = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            sku = row.get('SKU', '').strip()
            if not sku:
                errors.append(f"Row {row_num}: Missing SKU")
                continue
            
            # Check if product exists
            product = db.query(Product).filter(Product.sku == sku).first()
            
            if product:
                # Update existing
                product.name = row.get('Name', product.name)
                product.description = row.get('Description', product.description)
                product.item_type = row.get('Item Type', product.item_type)
                product.procurement_type = row.get('Procurement Type', product.procurement_type)
                product.unit = row.get('Unit', product.unit)
                if row.get('Standard Cost'):
                    product.standard_cost = float(row.get('Standard Cost'))
                if row.get('Selling Price'):
                    product.selling_price = float(row.get('Selling Price'))
                if row.get('Reorder Point'):
                    product.reorder_point = float(row.get('Reorder Point'))
                product.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Create new
                now = datetime.now(timezone.utc)
                product = Product(
                    sku=sku,
                    name=row.get('Name', ''),
                    description=row.get('Description'),
                    item_type=row.get('Item Type', 'finished_good'),
                    procurement_type=row.get('Procurement Type', 'buy'),
                    unit=row.get('Unit', 'EA'),
                    standard_cost=float(row.get('Standard Cost', 0)) if row.get('Standard Cost') else None,
                    selling_price=float(row.get('Selling Price', 0)) if row.get('Selling Price') else None,
                    reorder_point=float(row.get('Reorder Point', 0)) if row.get('Reorder Point') else None,
                    active=row.get('Active', 'true').lower() == 'true',
                    created_at=now,
                    updated_at=now
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
    
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_processed": created + updated
    }

