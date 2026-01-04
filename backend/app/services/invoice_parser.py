"""
Invoice Parser Service

Uses Claude API to extract structured data from invoices (PDF/CSV).
"""
import os
import csv
import json
import time
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional, Tuple, List
from pathlib import Path
import base64

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.purchase_order_document import VendorItem
from app.schemas.invoice_parsing import (
    ParsedInvoice,
    ParsedInvoiceLine,
    MatchConfidence,
)

# Load .env from project root (parent of backend/)
_env_path = Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

logger = get_logger(__name__)


# Claude API prompt for invoice extraction
INVOICE_EXTRACTION_PROMPT = '''You are an invoice parser. Extract structured data from this invoice.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "vendor_name": "Company Name from invoice",
  "invoice_number": "INV-12345 or similar",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "lines": [
    {
      "line_number": 1,
      "vendor_sku": "Part number/SKU exactly as shown",
      "description": "Item description",
      "quantity": 10.00,
      "unit": "EA or KG or LB etc",
      "unit_cost": 5.99,
      "line_total": 59.90
    }
  ],
  "subtotal": 100.00,
  "tax": 8.00,
  "shipping": 5.00,
  "total": 113.00
}

Rules:
- Extract vendor SKU/part numbers exactly as shown (case-sensitive)
- Preserve original units (don't convert)
- Use null for missing fields, not empty strings
- Quantities and costs should be numbers, not strings
- If multiple pages, include all line items
'''


def _get_anthropic_client():
    """Get Anthropic client, raising clear error if not configured."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

    return anthropic.Anthropic(api_key=api_key)


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf package not installed. Run: pip install pypdf")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []

    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text:
            text_parts.append(f"--- Page {page_num} ---\n{text}")

    return "\n\n".join(text_parts)


def _parse_pdf_basic(text: str) -> dict:
    """
    Basic regex-based PDF parsing (no AI required).
    Extracts common invoice patterns without Claude API.
    """
    import re

    result = {
        "vendor_name": "",
        "invoice_number": "",
        "invoice_date": None,
        "lines": [],
        "subtotal": 0,
        "tax": 0,
        "shipping": 0,
        "total": 0,
    }

    lines_text = text.split('\n')

    # Try to find invoice number
    inv_patterns = [
        r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'INV[#-]?\s*([A-Z0-9-]+)',
        r'Order\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'PO\s*#?\s*:?\s*([A-Z0-9-]+)',
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["invoice_number"] = match.group(1).strip()
            break

    # Try to find date and normalize to YYYY-MM-DD
    date_patterns = [
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # YYYY-MM-DD or YYYY/MM/DD
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # MM-DD-YYYY or DD/MM/YYYY
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2})',  # MM-DD-YY
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                # Try various formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m-%d-%Y', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%Y',
                           '%m-%d-%y', '%m/%d/%y', '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y']:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        result["invoice_date"] = parsed.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                if result["invoice_date"]:
                    break
            except Exception:
                pass

    # Try to find total
    total_patterns = [
        r'Total[:\s]*\$?\s*([\d,]+\.?\d*)',
        r'Grand\s*Total[:\s]*\$?\s*([\d,]+\.?\d*)',
        r'Amount\s*Due[:\s]*\$?\s*([\d,]+\.?\d*)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                result["total"] = float(match.group(1).replace(',', ''))
            except ValueError:
                pass
            break

    # Try to find line items - look for patterns like:
    # SKU/Item  Description  Qty  Price  Total
    # This is a basic heuristic - looks for lines with numbers that could be qty/price
    line_pattern = r'([A-Z0-9-]+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)'

    line_num = 0
    for line in lines_text:
        match = re.search(line_pattern, line)
        if match:
            line_num += 1
            try:
                qty = float(match.group(3))
                unit_cost = float(match.group(4).replace(',', ''))
                line_total = float(match.group(5).replace(',', ''))

                result["lines"].append({
                    "line_number": line_num,
                    "vendor_sku": match.group(1).strip(),
                    "description": match.group(2).strip(),
                    "quantity": qty,
                    "unit": "EA",
                    "unit_cost": unit_cost,
                    "line_total": line_total,
                })
            except ValueError:
                continue

    # Calculate subtotal from lines if we found any
    if result["lines"]:
        result["subtotal"] = sum(line["line_total"] for line in result["lines"])

    # If no lines found, add a note
    if not result["lines"]:
        logger.warning("Basic PDF parser couldn't extract line items - manual entry may be needed")

    return result


def _is_api_available() -> bool:
    """Check if Anthropic API is configured and available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return bool(api_key and len(api_key) > 10)


def _is_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    import requests
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def _get_ollama_model() -> str:
    """Get the preferred Ollama model for invoice parsing."""
    # User can override via env var, default to llama3.2 (good balance of speed/quality)
    return os.getenv("OLLAMA_MODEL", "llama3.2")


def _parse_with_ollama(text: str) -> dict:
    """Send text to Ollama for structured extraction."""
    import requests

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model = _get_ollama_model()

    # Ollama API format
    payload = {
        "model": model,
        "prompt": f"{INVOICE_EXTRACTION_PROMPT}\n\nInvoice text:\n{text}",
        "stream": False,
        "format": "json",  # Request JSON output
    }

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=60  # Give it time for larger invoices
        )
        response.raise_for_status()

        result = response.json()
        response_text = result.get("response", "")

        # Clean up response - sometimes wrapped in markdown
        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)

        return json.loads(response_text)

    except requests.exceptions.Timeout:
        logger.warning(f"Ollama request timed out - model {model} may be too slow")
        raise RuntimeError("Ollama request timed out")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Ollama request failed: {e}")
        raise RuntimeError(f"Ollama request failed: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"Ollama returned invalid JSON: {e}")
        raise


def _parse_csv_invoice(csv_bytes: bytes) -> dict:
    """Parse CSV invoice directly without AI."""
    content = csv_bytes.decode('utf-8-sig')  # Handle BOM
    reader = csv.DictReader(io.StringIO(content))

    lines = []
    line_num = 0

    # Common column name variations
    sku_cols = ['sku', 'part', 'part_number', 'item', 'item_number', 'product_code']
    desc_cols = ['description', 'desc', 'name', 'product', 'item_description']
    qty_cols = ['quantity', 'qty', 'amount', 'units']
    cost_cols = ['unit_cost', 'cost', 'price', 'unit_price', 'rate']
    total_cols = ['total', 'line_total', 'amount', 'extended', 'ext_price']

    def find_col(row: dict, candidates: list) -> Optional[str]:
        row_lower = {k.lower().strip(): k for k in row.keys()}
        for c in candidates:
            if c in row_lower:
                return row_lower[c]
        return None

    for row in reader:
        line_num += 1

        sku_col = find_col(row, sku_cols)
        desc_col = find_col(row, desc_cols)
        qty_col = find_col(row, qty_cols)
        cost_col = find_col(row, cost_cols)
        total_col = find_col(row, total_cols)

        if not sku_col:
            continue

        try:
            qty = Decimal(str(row.get(qty_col, 1) or 1).replace(',', ''))
            cost = Decimal(str(row.get(cost_col, 0) or 0).replace(',', '').replace('$', ''))
            total = Decimal(str(row.get(total_col, 0) or 0).replace(',', '').replace('$', ''))

            if total == 0 and qty > 0 and cost > 0:
                total = qty * cost

            lines.append({
                "line_number": line_num,
                "vendor_sku": str(row.get(sku_col, '')).strip(),
                "description": str(row.get(desc_col, '')).strip() if desc_col else '',
                "quantity": float(qty),
                "unit": "EA",
                "unit_cost": float(cost),
                "line_total": float(total),
            })
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Skipping CSV row {line_num}: {e}")
            continue

    return {
        "vendor_name": "Unknown (CSV Import)",
        "invoice_number": "",
        "invoice_date": None,
        "lines": lines,
        "subtotal": sum(item["line_total"] for item in lines),
        "total": sum(item["line_total"] for item in lines),
    }


def _parse_with_claude(text: str) -> dict:
    """Send text to Claude for structured extraction."""
    client = _get_anthropic_client()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"{INVOICE_EXTRACTION_PROMPT}\n\nInvoice text:\n{text}"
            }
        ]
    )

    response_text = message.content[0].text

    # Clean up response - Claude sometimes wraps in markdown
    response_text = response_text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last lines if they're markdown fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    return json.loads(response_text)


def _parse_with_claude_vision(pdf_bytes: bytes) -> dict:
    """Send PDF as image to Claude for extraction (for scanned invoices)."""
    client = _get_anthropic_client()

    # Encode PDF as base64
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": INVOICE_EXTRACTION_PROMPT,
                    }
                ]
            }
        ]
    )

    response_text = message.content[0].text

    # Clean up response
    response_text = response_text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    return json.loads(response_text)


def _match_vendor(db: Session, vendor_name: str) -> Tuple[Optional[int], MatchConfidence]:
    """Try to match vendor name to existing vendor."""
    if not vendor_name:
        return None, MatchConfidence.NONE

    # Exact match
    vendor = db.query(Vendor).filter(
        Vendor.name.ilike(vendor_name)
    ).first()

    if vendor:
        return vendor.id, MatchConfidence.EXACT

    # Fuzzy match - check if name contains vendor name or vice versa
    vendors = db.query(Vendor).filter(Vendor.is_active.is_(True)).all()
    for v in vendors:
        if vendor_name.lower() in v.name.lower() or v.name.lower() in vendor_name.lower():
            return v.id, MatchConfidence.FUZZY

    return None, MatchConfidence.NONE


def _match_products(
    db: Session,
    lines: List[dict],
    vendor_id: Optional[int]
) -> List[ParsedInvoiceLine]:
    """Match invoice lines to products using vendor_items and similarity."""
    result = []

    for line in lines:
        # Use 'or' to handle explicit null values from AI responses
        vendor_sku = line.get("vendor_sku") or ""
        description = line.get("description") or ""

        parsed_line = ParsedInvoiceLine(
            line_number=line.get("line_number") or 0,
            vendor_sku=vendor_sku,
            description=description,
            quantity=Decimal(str(line.get("quantity") or 0)),
            unit=line.get("unit") or "EA",
            unit_cost=Decimal(str(line.get("unit_cost") or 0)),
            line_total=Decimal(str(line.get("line_total") or 0)),
        )

        # Try vendor_items first (if we have vendor_id)
        if vendor_id and vendor_sku:
            vendor_item = db.query(VendorItem).filter(
                VendorItem.vendor_id == vendor_id,
                VendorItem.vendor_sku == vendor_sku,
                VendorItem.product_id.isnot(None),
            ).first()

            if vendor_item and vendor_item.product:
                parsed_line.matched_product_id = vendor_item.product_id
                parsed_line.matched_product_sku = vendor_item.product.sku
                parsed_line.matched_product_name = vendor_item.product.name
                parsed_line.match_confidence = MatchConfidence.EXACT
                parsed_line.match_source = "vendor_items"
                result.append(parsed_line)
                continue

        # Try SKU similarity
        if vendor_sku:
            product = db.query(Product).filter(
                Product.sku.ilike(f"%{vendor_sku}%"),
                Product.active.is_(True),
            ).first()

            if product:
                parsed_line.matched_product_id = product.id
                parsed_line.matched_product_sku = product.sku
                parsed_line.matched_product_name = product.name
                parsed_line.match_confidence = MatchConfidence.FUZZY
                parsed_line.match_source = "sku_similarity"
                result.append(parsed_line)
                continue

        # Try description match
        if description:
            words = description.split()[:2]
            for word in words:
                if len(word) >= 4:
                    product = db.query(Product).filter(
                        Product.name.ilike(f"%{word}%"),
                        Product.active.is_(True),
                    ).first()

                    if product:
                        parsed_line.matched_product_id = product.id
                        parsed_line.matched_product_sku = product.sku
                        parsed_line.matched_product_name = product.name
                        parsed_line.match_confidence = MatchConfidence.FUZZY
                        parsed_line.match_source = f"description_contains_{word}"
                        break

        result.append(parsed_line)

    return result


def parse_invoice(
    db: Session,
    file_bytes: bytes,
    filename: str,
    vendor_id: Optional[int] = None,
    use_vision: bool = False,
) -> ParsedInvoice:
    """
    Parse an invoice file and return structured data.

    Args:
        db: Database session
        file_bytes: Raw file content
        filename: Original filename (for type detection)
        vendor_id: Pre-selected vendor ID (optional)
        use_vision: Use Claude vision for PDFs (slower but better for scanned docs)

    Returns:
        ParsedInvoice with matched products
    """
    start_time = time.time()
    warnings = []

    # Determine file type
    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    try:
        if ext == 'csv':
            # Direct CSV parsing
            raw_data = _parse_csv_invoice(file_bytes)
            raw_text = file_bytes.decode('utf-8-sig')[:2000]

        elif ext == 'pdf':
            # Extract text first (needed for both AI and basic parsing)
            text = _extract_text_from_pdf(file_bytes)
            raw_text = text[:2000]

            if len(text.strip()) < 50:
                warnings.append("PDF has minimal text - may be scanned. Consider re-parsing with vision mode.")

            # Try AI parsing in order of preference:
            # 1. Anthropic API (best quality, paid)
            # 2. Ollama (good quality, free/local)
            # 3. Basic regex (limited quality, always available)

            if _is_api_available():
                if use_vision:
                    # Use Claude vision for scanned/image PDFs
                    raw_data = _parse_with_claude_vision(file_bytes)
                    raw_text = "(PDF processed via vision)"
                else:
                    # Use Claude for text extraction
                    raw_data = _parse_with_claude(text)
                logger.info("Using Anthropic Claude for invoice parsing")

            elif _is_ollama_available():
                # Use local Ollama - free AI parsing
                try:
                    raw_data = _parse_with_ollama(text)
                    model = _get_ollama_model()
                    logger.info(f"Using Ollama ({model}) for invoice parsing")
                except Exception as e:
                    # Ollama failed, fall back to basic
                    logger.warning(f"Ollama parsing failed: {e}, falling back to basic parser")
                    warnings.append("AI parsing failed. Using basic parsing - some fields may need manual entry.")
                    raw_data = _parse_pdf_basic(text)

            else:
                # Fallback to basic regex parsing (no AI cost)
                warnings.append("Using basic parsing (no AI configured). Some fields may need manual entry.")
                raw_data = _parse_pdf_basic(text)
                logger.info("Using basic PDF parser - no AI service available")
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        raise ValueError(f"Failed to parse invoice structure: {e}")
    except Exception as e:
        logger.error(f"Invoice parsing failed: {e}")
        raise

    # Match vendor
    vendor_name = raw_data.get("vendor_name", "Unknown")
    if not vendor_id:
        vendor_id, vendor_confidence = _match_vendor(db, vendor_name)
    else:
        vendor_confidence = MatchConfidence.EXACT

    # Match products
    lines = _match_products(db, raw_data.get("lines", []), vendor_id)

    # Parse dates
    invoice_date = None
    due_date = None
    try:
        if raw_data.get("invoice_date"):
            invoice_date = datetime.strptime(raw_data["invoice_date"], "%Y-%m-%d").date()
        if raw_data.get("due_date"):
            due_date = datetime.strptime(raw_data["due_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        warnings.append("Could not parse invoice date")

    # Calculate stats
    matched_count = sum(1 for item in lines if item.matched_product_id)
    unmapped_count = len(lines) - matched_count

    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Parsed invoice in {processing_time_ms}ms: {len(lines)} lines, {matched_count} matched")

    return ParsedInvoice(
        vendor_name=vendor_name,
        vendor_id=vendor_id,
        vendor_confidence=vendor_confidence,
        invoice_number=raw_data.get("invoice_number", ""),
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=Decimal(str(raw_data.get("subtotal") or 0)),
        tax=Decimal(str(raw_data.get("tax") or 0)),
        shipping=Decimal(str(raw_data.get("shipping") or 0)),
        total=Decimal(str(raw_data.get("total") or 0)),
        lines=lines,
        line_count=len(lines),
        matched_count=matched_count,
        unmapped_count=unmapped_count,
        warnings=warnings,
        raw_text=raw_text,
    )
