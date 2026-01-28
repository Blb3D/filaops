"""
Amazon Business CSV Import Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
import csv
import io
from collections import defaultdict

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.product import Product
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class AmazonProduct(BaseModel):
    """Unique product from Amazon CSV"""

    asin: str
    title: str
    brand: str
    total_qty: int
    total_spent: float
    suggested_category: str  # "filament", "subscription", "misc"


class AmazonOrder(BaseModel):
    """Order from Amazon CSV"""

    order_id: str
    order_date: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    shipping: float
    total: float


class ParseResult(BaseModel):
    """Result of parsing Amazon CSV"""

    order_count: int
    product_count: int
    total_spend: float
    products: List[AmazonProduct]
    orders: List[AmazonOrder]


class ProductMapping(BaseModel):
    """Mapping an Amazon product to a system product"""

    asin: str
    product_id: Optional[int] = None  # None = create as MISC
    category: str = "misc"  # "filament", "subscription", "misc", "skip"
    qty_override: Optional[int] = None  # Override qty (e.g., 1 pack = 240 units)


class ImportRequest(BaseModel):
    """Request to import orders"""

    orders: List[AmazonOrder]
    mappings: Dict[str, ProductMapping]  # ASIN -> mapping


class ImportResult(BaseModel):
    """Result of import"""

    pos_created: int
    lines_created: int
    skipped_orders: int
    errors: List[str]


# ============================================================================
# Helper Functions
# ============================================================================


def clean_price(val: str) -> float:
    """Clean a price string to float"""
    if not val:
        return 0.0
    return float(str(val).replace(",", "").replace('"', "").replace("$", "").strip() or 0)


def suggest_category(title: str, brand: str) -> str:
    """Suggest a category based on product title/brand"""
    title_lower = title.lower()
    brand_lower = brand.lower()

    # Filament brands and keywords
    filament_brands = ["elegoo", "overture", "esun", "polymaker", "bambulab", "sunlu", "hp3df"]
    filament_keywords = ["pla", "petg", "abs", "asa", "filament", "tpu"]

    if any(b in brand_lower for b in filament_brands):
        return "filament"
    if any(k in title_lower for k in filament_keywords):
        return "filament"

    # Subscriptions
    subscription_keywords = ["subscription", "membership", "music unlimited", "prime", "kindle unlimited", "audible"]
    if any(k in title_lower for k in subscription_keywords):
        return "subscription"

    # 3D printing related
    if any(k in title_lower for k in ["nozzle", "hotend", "build plate", "bed", "extruder"]):
        return "printer_parts"

    return "misc"


def parse_amazon_csv(content: str) -> ParseResult:
    """Parse Amazon Business CSV content"""
    orders = defaultdict(
        lambda: {"items": [], "date": None, "subtotal": 0.0, "tax": 0.0, "shipping": 0.0, "total": 0.0}
    )
    unique_products = {}

    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        order_id = row.get("Order ID", "")
        if not order_id:
            continue

        asin = row.get("ASIN", "")
        title = (row.get("Title", "") or "Unknown")[:100]
        brand = row.get("Brand", "") or "Unknown"

        qty = int(row.get("Item Quantity", "1") or "1")
        unit_cost = clean_price(row.get("Purchase PPU", "")) or clean_price(row.get("Item Subtotal", ""))
        item_total = clean_price(row.get("Item Net Total", ""))
        item_tax = clean_price(row.get("Item Tax", ""))
        item_shipping = clean_price(row.get("Item Shipping & Handling", ""))
        item_subtotal = clean_price(row.get("Item Subtotal", ""))

        # Track unique products
        if asin and asin not in unique_products:
            unique_products[asin] = {
                "asin": asin,
                "title": title,
                "brand": brand,
                "total_qty": 0,
                "total_spent": 0.0,
                "suggested_category": suggest_category(title, brand),
            }

        if asin:
            unique_products[asin]["total_qty"] += qty
            unique_products[asin]["total_spent"] += item_total

        # Add to order
        orders[order_id]["date"] = row.get("Order Date", "")
        orders[order_id]["items"].append(
            {
                "asin": asin,
                "title": title,
                "brand": brand,
                "qty": qty,
                "unit_cost": unit_cost if unit_cost > 0 else (item_subtotal / qty if qty > 0 else 0),
                "subtotal": item_subtotal,
                "tax": item_tax,
                "shipping": item_shipping,
                "total": item_total,
            }
        )
        orders[order_id]["subtotal"] += item_subtotal
        orders[order_id]["tax"] += item_tax
        orders[order_id]["shipping"] += item_shipping
        orders[order_id]["total"] += item_total

    # Convert to response format
    products_list = [
        AmazonProduct(**p) for p in sorted(unique_products.values(), key=lambda x: x["total_spent"], reverse=True)
    ]

    orders_list = [
        AmazonOrder(
            order_id=oid,
            order_date=data["date"],
            items=data["items"],
            subtotal=data["subtotal"],
            tax=data["tax"],
            shipping=data["shipping"],
            total=data["total"],
        )
        for oid, data in orders.items()
    ]

    total_spend = sum(p.total_spent for p in products_list)

    return ParseResult(
        order_count=len(orders_list),
        product_count=len(products_list),
        total_spend=total_spend,
        products=products_list,
        orders=orders_list,
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/parse", response_model=ParseResult)
async def parse_amazon_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Parse an Amazon Business CSV file and return products for mapping
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        # Try UTF-8 with BOM first
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    result = parse_amazon_csv(text)
    return result


@router.get("/existing-products")
async def get_existing_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get existing products that can be mapped to Amazon items
    """
    query = db.query(Product).filter(Product.active.is_(True))  # noqa: E712

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_filter))
            | (Product.sku.ilike(search_filter))
            | (Product.description.ilike(search_filter))
        )

    products = query.order_by(Product.name).limit(100).all()

    return [
        {"id": p.id, "sku": p.sku, "name": p.name, "description": p.description[:50] if p.description else None}
        for p in products
    ]


@router.post("/execute", response_model=ImportResult)
async def execute_import(
    request: ImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Execute the import with product mappings
    """
    errors = []
    pos_created = 0
    lines_created = 0
    skipped_orders = 0

    # Get or create Amazon vendor
    amazon_vendor = db.query(Vendor).filter(Vendor.name.ilike("%Amazon%")).first()
    if not amazon_vendor:
        amazon_vendor = Vendor(
            code="VND-AMAZON",
            name="Amazon Business",
            website="https://www.amazon.com/business",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(amazon_vendor)
        db.commit()
        db.refresh(amazon_vendor)

    # Get or create MISC product for unmapped items
    misc_product = db.query(Product).filter(Product.sku == "MISC-AMAZON").first()
    if not misc_product:
        misc_product = Product(
            sku="MISC-AMAZON",
            name="Miscellaneous Amazon Purchase",
            description="Catch-all for unmapped Amazon items",
            item_type="supply",
            active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(misc_product)
        db.commit()
        db.refresh(misc_product)

    # Process each order
    for order in request.orders:
        try:
            # Check if PO already exists for this Amazon order
            existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == f"AMZ-{order.order_id}").first()

            if existing_po:
                skipped_orders += 1
                continue

            # Parse date
            try:
                order_date = datetime.strptime(order.order_date, "%m/%d/%Y").date()
            except ValueError:
                order_date = datetime.utcnow().date()

            # Create PO
            po = PurchaseOrder(
                po_number=f"AMZ-{order.order_id}",
                vendor_id=amazon_vendor.id,
                status="received",  # Already received
                order_date=order_date,
                received_date=order_date,
                subtotal=Decimal(str(order.subtotal)),
                tax_amount=Decimal(str(order.tax)),
                shipping_cost=Decimal(str(order.shipping)),
                total_amount=Decimal(str(order.total)),
                notes="Imported from Amazon Business CSV",
                created_by=f"{current_user.first_name} {current_user.last_name}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(po)
            db.flush()  # Get PO ID

            # Create lines
            line_num = 1
            for item in order.items:
                asin = item.get("asin", "")
                mapping = request.mappings.get(asin)

                # Determine product_id
                if mapping and mapping.category == "skip":
                    continue
                elif mapping and mapping.product_id:
                    product_id = mapping.product_id
                else:
                    product_id = misc_product.id

                # Calculate quantities with optional override
                # qty_override is units per Amazon unit (e.g., 240 magnets per pack)
                amazon_qty = item.get("qty", 1)
                line_total = Decimal(str(item.get("total", 0)))

                if mapping and mapping.qty_override:
                    # qty_override = units per amazon unit
                    received_qty = amazon_qty * mapping.qty_override
                    unit_cost = line_total / Decimal(str(received_qty)) if received_qty > 0 else Decimal("0")
                else:
                    received_qty = amazon_qty
                    unit_cost = Decimal(str(item.get("unit_cost", 0)))

                line = PurchaseOrderLine(
                    purchase_order_id=po.id,
                    product_id=product_id,
                    line_number=line_num,
                    quantity_ordered=Decimal(str(received_qty)),
                    quantity_received=Decimal(str(received_qty)),  # Already received
                    unit_cost=unit_cost,
                    line_total=line_total,
                    notes=f"{item.get('title', '')} (ASIN: {asin})",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(line)
                lines_created += 1
                line_num += 1

            pos_created += 1

        except Exception as e:
            errors.append(f"Order {order.order_id}: {str(e)}")
            logger.error(f"Error importing order {order.order_id}: {e}")

    db.commit()

    return ImportResult(
        pos_created=pos_created, lines_created=lines_created, skipped_orders=skipped_orders, errors=errors
    )
