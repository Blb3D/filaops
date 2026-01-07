/**
 * Invoice Review Modal
 *
 * Displays parsed invoice data for review before creating a PO.
 * Allows product mapping overrides and quantity/cost edits.
 */
import { useState, useMemo } from "react";
import { API_URL } from "../../config/api";
import ProductSearchSelect from "./ProductSearchSelect";

// Match confidence badge colors
const CONFIDENCE_STYLES = {
  exact: "bg-green-500/20 text-green-400 border-green-500/30",
  fuzzy: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  none: "bg-red-500/20 text-red-400 border-red-500/30",
};

const CONFIDENCE_LABELS = {
  exact: "Matched",
  fuzzy: "Fuzzy Match",
  none: "Unmapped",
};

// UOM classes - units in the same class can be converted between each other
const UOM_CLASSES = {
  weight: ["G", "KG", "LB", "OZ"],
  quantity: ["EA", "PK"],
};

// All available UOMs for fallback when no product selected
const ALL_UOMS = ["EA", "KG", "G", "LB", "OZ", "PK"];

// Get valid UOMs for a product based on its purchase_uom class
function getValidUomsForProduct(product) {
  if (!product?.purchase_uom) return ALL_UOMS;

  const productUom = product.purchase_uom.toUpperCase();

  // Find which class this UOM belongs to
  for (const [, uoms] of Object.entries(UOM_CLASSES)) {
    if (uoms.includes(productUom)) {
      return uoms;
    }
  }

  // Unknown UOM class - return all
  return ALL_UOMS;
}

export default function InvoiceReviewModal({
  parsedInvoice,
  originalFile,
  vendors = [],
  products = [],
  onClose,
  onSuccess,
}) {
  // Editable state initialized from parsed data
  const [vendorId, setVendorId] = useState(parsedInvoice.vendor_id || "");
  const [invoiceNumber, setInvoiceNumber] = useState(parsedInvoice.invoice_number || "");
  const [invoiceDate, setInvoiceDate] = useState(parsedInvoice.invoice_date || "");
  const [tax, setTax] = useState(parsedInvoice.tax || 0);
  const [shipping, setShipping] = useState(parsedInvoice.shipping || 0);
  const [attachDocument, setAttachDocument] = useState(true);
  const [notes, setNotes] = useState("");

  // Line items with editable overrides
  const [lines, setLines] = useState(
    parsedInvoice.lines.map((line, idx) => {
      // If product is matched, use that product's purchase_uom instead of invoice unit
      const matchedProduct = line.matched_product_id
        ? products.find((p) => String(p.id) === String(line.matched_product_id))
        : null;

      // Recalculate unit_cost from line_total if available (handles discounts)
      // The parser may extract list price as unit_cost but actual charged amount as line_total
      const qty = parseFloat(line.quantity) || 1;
      const lineTotal = parseFloat(line.line_total) || 0;
      const parsedUnitCost = parseFloat(line.unit_cost) || 0;
      // Use line_total / qty if it differs significantly from parsed unit_cost (indicates discount)
      const calculatedUnitCost = qty > 0 ? lineTotal / qty : parsedUnitCost;
      const unitCost = lineTotal > 0 && Math.abs(calculatedUnitCost - parsedUnitCost) > 0.01
        ? calculatedUnitCost.toFixed(4)
        : line.unit_cost;

      return {
        ...line,
        key: idx,
        product_id: line.matched_product_id || "",
        save_mapping: line.match_confidence !== "exact", // Auto-save new mappings
        // Override unit with product's purchase_uom if matched (e.g., KG instead of EA)
        unit: matchedProduct?.purchase_uom || line.unit,
        // Use calculated unit cost that accounts for discounts
        unit_cost: unitCost,
      };
    })
  );

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  // Product lookup for dropdown
  const productOptions = useMemo(() => {
    return products
      .filter((p) => p.active !== false)
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [products]);

  // Calculate totals
  const subtotal = useMemo(() => {
    return lines.reduce((sum, line) => sum + parseFloat(line.line_total || 0), 0);
  }, [lines]);

  const total = subtotal + parseFloat(tax || 0) + parseFloat(shipping || 0);

  // Count unmapped lines
  const unmappedCount = useMemo(() => {
    return lines.filter((line) => !line.product_id).length;
  }, [lines]);

  // Update a line field with automatic recalculation
  const updateLine = (index, field, value) => {
    setLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;

        const updated = { ...line, [field]: value };
        const qty = parseFloat(field === "quantity" ? value : line.quantity) || 0;
        const unitCost = parseFloat(field === "unit_cost" ? value : line.unit_cost) || 0;
        const lineTotal = parseFloat(field === "line_total" ? value : line.line_total) || 0;

        if (field === "quantity" || field === "unit_cost") {
          // Recalc line total when qty or unit cost changes
          updated.line_total = (qty * unitCost).toFixed(2);
        } else if (field === "line_total") {
          // Recalc unit cost when line total changes
          updated.unit_cost = qty > 0 ? (lineTotal / qty).toFixed(4) : "0";
        }

        return updated;
      })
    );
  };

  // Handle product selection change
  const handleProductChange = (index, productId) => {
    const product = products.find((p) => String(p.id) === String(productId));
    setLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;
        return {
          ...line,
          product_id: productId,
          matched_product_sku: product?.sku || "",
          matched_product_name: product?.name || "",
          match_confidence: productId ? "exact" : "none",
          save_mapping: true, // User manually selected, save the mapping
          // Use product's purchase_uom if available (e.g., KG for filament instead of EA)
          unit: product?.purchase_uom || line.unit,
        };
      })
    );
  };

  // Create PO from reviewed invoice
  const handleCreatePO = async () => {
    if (!vendorId) {
      setError("Please select a vendor");
      return;
    }

    if (unmappedCount > 0) {
      setError(`${unmappedCount} item(s) still need product mapping`);
      return;
    }

    setCreating(true);
    setError(null);

    try {
      // Build request payload
      const payload = {
        vendor_id: parseInt(vendorId),
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate || null,
        tax: parseFloat(tax) || 0,
        shipping: parseFloat(shipping) || 0,
        notes: notes,
        attach_document: attachDocument,
        document_type: "invoice",
        lines: lines.map((line) => ({
          product_id: parseInt(line.product_id),
          vendor_sku: line.vendor_sku,
          quantity: parseFloat(line.quantity),
          unit_cost: parseFloat(line.unit_cost),
          purchase_unit: line.unit || "EA",
          notes: line.description,
          save_mapping: line.save_mapping,
        })),
      };

      const token = localStorage.getItem("adminToken");

      // Step 1: Create the PO with JSON
      const response = await fetch(
        `${API_URL}/api/v1/purchase-orders/invoices/create-po`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to create purchase order");
      }

      // Step 2: Upload document if requested
      if (attachDocument && originalFile && data.id) {
        const formData = new FormData();
        formData.append("file", originalFile);
        formData.append("document_type", "invoice");

        const docResponse = await fetch(
          `${API_URL}/api/v1/purchase-orders/${data.id}/documents`,
          {
            method: "POST",
            headers: {
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: formData,
          }
        );

        if (!docResponse.ok) {
          // PO was created but document upload failed - log but don't fail
          console.warn("Document upload failed, but PO was created:", await docResponse.text());
        }
      }

      onSuccess(data);
    } catch (err) {
      console.error("Create PO error:", err);
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-5xl max-h-[90vh] border border-gray-800 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
          <div>
            <h3 className="text-lg font-semibold text-white">Review Parsed Invoice</h3>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-gray-400">
                {parsedInvoice.line_count} items parsed, {parsedInvoice.matched_count} matched
              </span>
              {parsedInvoice.ai_provider && (
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  parsedInvoice.ai_provider === 'anthropic'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    : parsedInvoice.ai_provider === 'ollama'
                    ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                    : 'bg-gray-500/20 text-gray-300 border border-gray-500/30'
                }`}>
                  {parsedInvoice.ai_provider === 'anthropic' && parsedInvoice.ai_model
                    ? parsedInvoice.ai_model.replace('claude-', '').replace(/-\d+$/, '')
                    : parsedInvoice.ai_provider === 'ollama' && parsedInvoice.ai_model
                    ? `Ollama: ${parsedInvoice.ai_model}`
                    : parsedInvoice.ai_provider}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content - scrollable */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Warnings */}
          {parsedInvoice.warnings?.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-3">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="text-yellow-400 text-sm">
                  {parsedInvoice.warnings.map((w, i) => (
                    <p key={i}>{w}</p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Invoice Header Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-gray-400 text-sm mb-1">Vendor *</label>
              <select
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
                className={`w-full bg-gray-800 border rounded-lg px-3 py-2 text-white ${
                  !vendorId ? "border-red-500" : "border-gray-700"
                }`}
              >
                <option value="">Select Vendor</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
              {parsedInvoice.vendor_name && !vendorId && (
                <p className="text-gray-500 text-xs mt-1">
                  Detected: {parsedInvoice.vendor_name}
                </p>
              )}
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Invoice #</label>
              <input
                type="text"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                placeholder="INV-12345"
              />
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Invoice Date</label>
              <input
                type="date"
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1">Notes</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                placeholder="Optional notes"
              />
            </div>
          </div>

          {/* Line Items Table */}
          <div className="border border-gray-800 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs text-gray-400 font-medium">#</th>
                    <th className="px-3 py-2 text-left text-xs text-gray-400 font-medium">Vendor SKU</th>
                    <th className="px-3 py-2 text-left text-xs text-gray-400 font-medium min-w-[200px]">Product Mapping</th>
                    <th className="px-3 py-2 text-right text-xs text-gray-400 font-medium">Qty</th>
                    <th className="px-3 py-2 text-left text-xs text-gray-400 font-medium">Unit</th>
                    <th className="px-3 py-2 text-right text-xs text-gray-400 font-medium">Unit Cost</th>
                    <th className="px-3 py-2 text-right text-xs text-gray-400 font-medium">Line Total</th>
                    <th className="px-3 py-2 text-center text-xs text-gray-400 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {lines.map((line, idx) => (
                    <tr key={line.key} className="hover:bg-gray-800/30">
                      <td className="px-3 py-2 text-gray-500 text-sm">{line.line_number || idx + 1}</td>
                      <td className="px-3 py-2">
                        <div className="text-white text-sm font-mono">{line.vendor_sku || "-"}</div>
                        <div className="text-gray-500 text-xs truncate max-w-[150px]" title={line.description}>
                          {line.description}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <ProductSearchSelect
                          value={line.product_id || ""}
                          products={productOptions}
                          onChange={(productId) => handleProductChange(idx, productId)}
                          placeholder="Search products..."
                          onCreateNew={(searchText) => {
                            // Open items page in new tab with search pre-filled
                            const params = new URLSearchParams();
                            params.set("search", line.vendor_sku || line.description || searchText || "");
                            window.open(`/admin/items?${params.toString()}`, "_blank");
                          }}
                        />
                        {line.match_source && line.match_confidence !== "none" && (
                          <div className="text-gray-500 text-xs mt-1">
                            via {line.match_source}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={line.quantity}
                          onChange={(e) => updateLine(idx, "quantity", e.target.value)}
                          step="0.01"
                          min="0"
                          className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-white text-sm"
                        />
                      </td>
                      <td className="px-3 py-2">
                        {(() => {
                          const selectedProduct = products.find(
                            (p) => String(p.id) === String(line.product_id)
                          );
                          const validUoms = getValidUomsForProduct(selectedProduct);
                          return (
                            <select
                              value={line.unit || "EA"}
                              onChange={(e) => updateLine(idx, "unit", e.target.value)}
                              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
                            >
                              {validUoms.map((uom) => (
                                <option key={uom} value={uom}>
                                  {uom}
                                </option>
                              ))}
                            </select>
                          );
                        })()}
                      </td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          value={line.unit_cost}
                          onChange={(e) => updateLine(idx, "unit_cost", e.target.value)}
                          step="0.01"
                          min="0"
                          className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-white text-sm"
                        />
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center">
                          <span className="text-gray-400 mr-1">$</span>
                          <input
                            type="number"
                            value={line.line_total || 0}
                            onChange={(e) => updateLine(idx, "line_total", e.target.value)}
                            step="0.01"
                            min="0"
                            className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-white text-sm"
                          />
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs border ${
                            CONFIDENCE_STYLES[line.match_confidence] || CONFIDENCE_STYLES.none
                          }`}
                        >
                          {CONFIDENCE_LABELS[line.match_confidence] || "Unmapped"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals and Options */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Options */}
            <div className="space-y-4">
              <label className="flex items-center gap-3 text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={attachDocument}
                  onChange={(e) => setAttachDocument(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  Attach original invoice to PO
                  {originalFile && (
                    <span className="text-gray-500 ml-1">({originalFile.name})</span>
                  )}
                </span>
              </label>
            </div>

            {/* Right: Totals */}
            <div className="bg-gray-800/50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between text-gray-400 text-sm">
                <span>Subtotal</span>
                <span className="text-white">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center text-gray-400 text-sm">
                <span>Tax</span>
                <input
                  type="number"
                  value={tax}
                  onChange={(e) => setTax(e.target.value)}
                  step="0.01"
                  min="0"
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-white text-sm"
                />
              </div>
              <div className="flex justify-between items-center text-gray-400 text-sm">
                <span>Shipping</span>
                <input
                  type="number"
                  value={shipping}
                  onChange={(e) => setShipping(e.target.value)}
                  step="0.01"
                  min="0"
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-right text-white text-sm"
                />
              </div>
              <div className="pt-2 border-t border-gray-700 flex justify-between text-white font-medium">
                <span>Total</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-800 flex items-center justify-between flex-shrink-0">
          <div className="text-gray-400 text-sm">
            {unmappedCount > 0 ? (
              <span className="text-red-400">
                {unmappedCount} item(s) need mapping
              </span>
            ) : (
              <span className="text-green-400">All items mapped</span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleCreatePO}
              disabled={creating || unmappedCount > 0 || !vendorId}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white flex items-center gap-2"
            >
              {creating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Creating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Create Purchase Order
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
