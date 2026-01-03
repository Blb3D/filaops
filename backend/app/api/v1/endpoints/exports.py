"""
QuickBooks Export API Endpoints

Export purchase orders in QuickBooks-compatible formats:
- CSV for QuickBooks Online
- IIF for QuickBooks Desktop
"""
import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.db.session import get_db
from app.logging_config import get_logger
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.vendor import Vendor
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.purchasing import (
    QBExportRequest,
    QBExportType,
    QBExportFormat,
    QBExportPreviewLine,
    QBExportPreviewResponse,
)

router = APIRouter()
logger = get_logger(__name__)


def _get_pos_for_export(
    db: Session,
    start_date: date,
    end_date: date,
    status_filter: List[str],
) -> List[PurchaseOrder]:
    """Get purchase orders within date range and status filter"""
    query = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.vendor),
        joinedload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product)
    ).filter(
        and_(
            PurchaseOrder.status.in_(status_filter),
            # Use received_date if available, otherwise order_date
            PurchaseOrder.received_date >= start_date,
            PurchaseOrder.received_date <= end_date,
        )
    ).order_by(PurchaseOrder.received_date)
    
    return query.all()


def _format_date(d: Optional[date]) -> str:
    """Format date for QuickBooks (MM/DD/YYYY)"""
    if not d:
        return ""
    return d.strftime("%m/%d/%Y")


def _generate_csv_expense(
    pos: List[PurchaseOrder],
    include_tax: bool,
    include_shipping: bool,
    include_line_detail: bool,
) -> str:
    """Generate CSV for QuickBooks Online Expense import"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    headers = ["Date", "Vendor", "Ref No", "Account", "Amount", "Memo", "Class"]
    writer.writerow(headers)
    
    for po in pos:
        vendor_name = po.vendor.name if po.vendor else "Unknown Vendor"
        po_date = _format_date(po.received_date or po.order_date)
        
        if include_line_detail:
            # Write each line item separately
            for line in po.lines:
                product_name = line.product.name if line.product else "Unknown Item"
                product_sku = line.product.sku if line.product else ""
                memo = f"{product_sku} - {product_name}" if product_sku else product_name
                
                writer.writerow([
                    po_date,
                    vendor_name,
                    po.po_number,
                    "Inventory:Raw Materials",  # Default account
                    str(line.line_total),
                    memo,
                    "Manufacturing",  # Default class
                ])
        else:
            # Write subtotal as single line
            writer.writerow([
                po_date,
                vendor_name,
                po.po_number,
                "Inventory:Raw Materials",
                str(po.subtotal),
                f"PO {po.po_number}",
                "Manufacturing",
            ])
        
        # Add tax line if applicable
        if include_tax and po.tax_amount and po.tax_amount > 0:
            writer.writerow([
                po_date,
                vendor_name,
                po.po_number,
                "Expenses:Sales Tax",
                str(po.tax_amount),
                "Tax",
                "Manufacturing",
            ])
        
        # Add shipping line if applicable
        if include_shipping and po.shipping_cost and po.shipping_cost > 0:
            writer.writerow([
                po_date,
                vendor_name,
                po.po_number,
                "Expenses:Shipping",
                str(po.shipping_cost),
                "Shipping",
                "Manufacturing",
            ])
    
    return output.getvalue()


def _generate_csv_bill(
    pos: List[PurchaseOrder],
    include_tax: bool,
    include_shipping: bool,
    include_line_detail: bool,
) -> str:
    """Generate CSV for QuickBooks Bill import"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header for bills
    headers = ["Bill No", "Vendor", "Bill Date", "Due Date", "Terms", 
               "Account", "Amount", "Memo"]
    writer.writerow(headers)
    
    for po in pos:
        vendor_name = po.vendor.name if po.vendor else "Unknown Vendor"
        bill_date = _format_date(po.received_date or po.order_date)
        terms = po.vendor.payment_terms if po.vendor else "Net 30"
        
        if include_line_detail:
            for line in po.lines:
                product_name = line.product.name if line.product else "Unknown Item"
                writer.writerow([
                    po.po_number,
                    vendor_name,
                    bill_date,
                    "",  # Due date calculated by QB based on terms
                    terms,
                    "Inventory:Raw Materials",
                    str(line.line_total),
                    product_name,
                ])
        else:
            writer.writerow([
                po.po_number,
                vendor_name,
                bill_date,
                "",
                terms,
                "Inventory:Raw Materials",
                str(po.subtotal),
                f"PO {po.po_number}",
            ])
        
        if include_tax and po.tax_amount and po.tax_amount > 0:
            writer.writerow([
                po.po_number,
                vendor_name,
                bill_date,
                "",
                terms,
                "Expenses:Sales Tax",
                str(po.tax_amount),
                "Tax",
            ])
        
        if include_shipping and po.shipping_cost and po.shipping_cost > 0:
            writer.writerow([
                po.po_number,
                vendor_name,
                bill_date,
                "",
                terms,
                "Expenses:Shipping",
                str(po.shipping_cost),
                "Shipping",
            ])
    
    return output.getvalue()


def _generate_iif_bill(
    pos: List[PurchaseOrder],
    include_tax: bool,
    include_shipping: bool,
    include_line_detail: bool,
) -> str:
    """Generate IIF file for QuickBooks Desktop Bill import"""
    lines = []
    
    # IIF Header
    lines.append("!TRNS\tTRNSID\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO")
    lines.append("!SPL\tSPLID\tTRNSTYPE\tDATE\tACCNT\tAMOUNT\tMEMO")
    lines.append("!ENDTRNS")
    
    for po in pos:
        vendor_name = po.vendor.name if po.vendor else "Unknown"
        po_date = _format_date(po.received_date or po.order_date)
        total = po.total_amount
        
        # Main transaction line (credit to A/P)
        lines.append(f"TRNS\t\tBILL\t{po_date}\tAccounts Payable\t{vendor_name}\t-{total}\t{po.po_number}\t")
        
        # Split lines (debits to expense/inventory accounts)
        if include_line_detail:
            for line in po.lines:
                product_name = line.product.name if line.product else "Unknown"
                lines.append(f"SPL\t\tBILL\t{po_date}\tInventory:Raw Materials\t{line.line_total}\t{product_name}")
        else:
            lines.append(f"SPL\t\tBILL\t{po_date}\tInventory:Raw Materials\t{po.subtotal}\tPO {po.po_number}")
        
        if include_tax and po.tax_amount and po.tax_amount > 0:
            lines.append(f"SPL\t\tBILL\t{po_date}\tExpenses:Sales Tax\t{po.tax_amount}\tTax")
        
        if include_shipping and po.shipping_cost and po.shipping_cost > 0:
            lines.append(f"SPL\t\tBILL\t{po_date}\tExpenses:Shipping\t{po.shipping_cost}\tShipping")
        
        lines.append("ENDTRNS")
    
    return "\n".join(lines)


# ============================================================================
# Preview Endpoint
# ============================================================================

@router.post("/quickbooks/preview", response_model=QBExportPreviewResponse)
async def preview_quickbooks_export(
    request: QBExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview QuickBooks export before downloading
    
    Shows summary of what will be exported including:
    - Total POs
    - Total amount
    - Line-by-line preview
    """
    pos = _get_pos_for_export(
        db,
        request.start_date,
        request.end_date,
        request.status_filter or ["received", "closed"],
    )
    
    if not pos:
        raise HTTPException(
            status_code=404,
            detail=f"No purchase orders found between {request.start_date} and {request.end_date}"
        )
    
    # Build preview lines
    preview_lines = []
    total_amount = Decimal("0")
    
    for po in pos:
        vendor_name = po.vendor.name if po.vendor else "Unknown"
        po_date = po.received_date or po.order_date
        
        if request.include_line_detail:
            for line in po.lines:
                product_name = line.product.name if line.product else "Unknown"
                preview_lines.append(QBExportPreviewLine(
                    date=po_date,
                    vendor=vendor_name,
                    po_number=po.po_number,
                    account="Inventory:Raw Materials",
                    amount=line.line_total,
                    memo=product_name,
                    class_name="Manufacturing",
                ))
                total_amount += line.line_total
        else:
            preview_lines.append(QBExportPreviewLine(
                date=po_date,
                vendor=vendor_name,
                po_number=po.po_number,
                account="Inventory:Raw Materials",
                amount=po.subtotal,
                memo=f"PO {po.po_number}",
                class_name="Manufacturing",
            ))
            total_amount += po.subtotal
        
        if request.include_tax and po.tax_amount:
            preview_lines.append(QBExportPreviewLine(
                date=po_date,
                vendor=vendor_name,
                po_number=po.po_number,
                account="Expenses:Sales Tax",
                amount=po.tax_amount,
                memo="Tax",
            ))
            total_amount += po.tax_amount
        
        if request.include_shipping and po.shipping_cost:
            preview_lines.append(QBExportPreviewLine(
                date=po_date,
                vendor=vendor_name,
                po_number=po.po_number,
                account="Expenses:Shipping",
                amount=po.shipping_cost,
                memo="Shipping",
            ))
            total_amount += po.shipping_cost
    
    return QBExportPreviewResponse(
        total_pos=len(pos),
        total_amount=total_amount,
        date_range=f"{request.start_date} to {request.end_date}",
        lines=preview_lines[:100],  # Limit preview to 100 lines
    )


# ============================================================================
# Download Endpoint
# ============================================================================

@router.post("/quickbooks/export")
async def download_quickbooks_export(
    request: QBExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download QuickBooks export file
    
    Formats:
    - CSV: Universal format for QuickBooks Online
    - IIF: Interchange format for QuickBooks Desktop
    
    Export types:
    - expense: Direct expenses (credit card purchases)
    - bill: Accounts payable bills
    - check: Check register entries
    """
    pos = _get_pos_for_export(
        db,
        request.start_date,
        request.end_date,
        request.status_filter or ["received", "closed"],
    )
    
    if not pos:
        raise HTTPException(
            status_code=404,
            detail=f"No purchase orders found between {request.start_date} and {request.end_date}"
        )
    
    # Generate file content based on format and type
    if request.format == QBExportFormat.CSV:
        if request.export_type == QBExportType.BILL:
            content = _generate_csv_bill(
                pos, request.include_tax, request.include_shipping, request.include_line_detail
            )
        else:  # expense or check (same format)
            content = _generate_csv_expense(
                pos, request.include_tax, request.include_shipping, request.include_line_detail
            )
        
        filename = f"filaops_po_export_{request.start_date}_{request.end_date}.csv"
        media_type = "text/csv"
        
    else:  # IIF format
        content = _generate_iif_bill(
            pos, request.include_tax, request.include_shipping, request.include_line_detail
        )
        filename = f"filaops_po_export_{request.start_date}_{request.end_date}.iif"
        media_type = "application/octet-stream"
    
    logger.info(
        f"Generated QuickBooks export: {len(pos)} POs, format={request.format.value}, "
        f"type={request.export_type.value}, user={current_user.email}"
    )
    
    # Return as downloadable file
    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============================================================================
# Quick Export (GET with query params for simpler access)
# ============================================================================

@router.get("/quickbooks")
async def quick_export(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query("csv", description="Export format: csv or iif"),
    type: str = Query("expense", description="Export type: expense, bill, or check"),
    include_tax: bool = Query(True),
    include_shipping: bool = Query(True),
    include_detail: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Quick export via GET request (for direct links/buttons)
    
    Example: /api/v1/exports/quickbooks?start_date=2025-01-01&end_date=2025-01-31
    """
    request = QBExportRequest(
        start_date=start_date,
        end_date=end_date,
        format=QBExportFormat(format),
        export_type=QBExportType(type),
        include_tax=include_tax,
        include_shipping=include_shipping,
        include_line_detail=include_detail,
    )
    
    return await download_quickbooks_export(request, db, current_user)
