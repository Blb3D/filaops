import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

/**
 * Render a centered fullscreen modal dialog that displays the provided title and children.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the modal is visible.
 * @param {() => void} props.onClose - Callback invoked to close the modal; also called when the backdrop is clicked.
 * @param {string} props.title - Header title shown at the top of the modal.
 * @param {React.ReactNode} props.children - Content rendered inside the modal container.
 * @returns {JSX.Element|null} The modal element when visible, `null` otherwise.
 */
function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:p-0">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-2xl w-full mx-auto p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

// Purchase Request Modal - Creates actual PO
function PurchaseRequestModal({ line, onClose, token, onSuccess }) {
  const [quantity, setQuantity] = useState(line?.shortage || 1);
  const [vendorId, setVendorId] = useState("");
  const [unitCost, setUnitCost] = useState(line?.component_cost || 0);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [vendors, setVendors] = useState([]);
  const [loadingVendors, setLoadingVendors] = useState(true);
  const [error, setError] = useState(null);
  const [createdPO, setCreatedPO] = useState(null);

  // Fetch vendors on mount
  useEffect(() => {
    const fetchVendors = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/vendors/?active_only=true`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setVendors(data);
        }
      } catch (err) {
        setError("Failed to load vendors. Please refresh the page.");
      } finally {
        setLoadingVendors(false);
      }
    };
    fetchVendors();
  }, [token]);

  const handleSubmit = async () => {
    if (!vendorId) {
      setError("Please select a vendor");
      return;
    }
    if (quantity <= 0) {
      setError("Quantity must be greater than 0");
      return;
    }
    if (unitCost < 0) {
      setError("Unit cost cannot be negative");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/purchase-orders/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          vendor_id: parseInt(vendorId),
          notes: notes || `PO for ${line.component_name}`,
          lines: [
            {
              product_id: line.component_id,
              quantity_ordered: quantity,
              unit_cost: unitCost,
              notes: `From BOM shortage`,
            },
          ],
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create PO");
      }

      const po = await res.json();
      setCreatedPO(po);
      if (onSuccess) onSuccess(po);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Success state - show created PO
  if (createdPO) {
    return (
      <div className="text-center py-4">
        <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h4 className="text-white font-medium mb-2">Purchase Order Created</h4>
        <p className="text-gray-400 text-sm mb-2">
          {createdPO.po_number} for {quantity} {line.component_unit} of{" "}
          {line.component_name}
        </p>
        <p className="text-gray-500 text-xs mb-4">
          Total: ${(quantity * unitCost).toFixed(2)} • Status: Draft
        </p>
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => (window.location.href = "/admin/purchasing")}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            View in Purchasing
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-2 rounded-lg text-sm">
          {error}
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-sm text-gray-400 mb-1">Component</div>
        <div className="text-white font-medium">{line.component_name}</div>
        <div className="text-gray-500 text-xs">{line.component_sku}</div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Current Stock:</span>
          <span className="text-white ml-2">
            {(line.inventory_available || 0).toFixed(2)} {line.component_unit}
          </span>
        </div>
        <div>
          <span className="text-gray-400">Shortage:</span>
          <span className="text-red-400 ml-2">
            {(line.shortage || 0).toFixed(2)} {line.component_unit}
          </span>
        </div>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Vendor *</label>
        <select
          value={vendorId}
          onChange={(e) => setVendorId(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          disabled={loadingVendors}
        >
          <option value="">
            {loadingVendors ? "Loading vendors..." : "Select vendor..."}
          </option>
          {vendors.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name} ({v.code})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Quantity to Order *
          </label>
          <input
            type="number"
            step="0.01"
            value={quantity}
            onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Unit Cost ($) *
          </label>
          <input
            type="number"
            step="0.01"
            value={unitCost}
            onChange={(e) => setUnitCost(parseFloat(e.target.value) || 0)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          />
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-3 text-sm">
        <span className="text-gray-400">Line Total:</span>
        <span className="text-white font-medium ml-2">
          ${(quantity * unitCost).toFixed(2)}
        </span>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">
          Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          placeholder="Additional notes for the purchase order..."
        />
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={handleSubmit}
          disabled={loading || !vendorId || quantity <= 0}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create Purchase Order"}
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/**
 * Render a detailed, editable view of a BOM including lines, cost rollup, routing/process path, and actions for adding/updating/deleting lines, exploding the BOM, and creating production or purchase requests.
 *
 * @param {Object} bom - The BOM object to display and manage; expected to include fields like id, code, version, product_id, product, lines, and total_cost.
 * @param {() => void} onClose - Callback invoked when the detail view should be closed.
 * @param {() => void} onUpdate - Callback invoked after mutating the BOM (add/update/delete/recalculate) to trigger parent refresh.
 * @param {string} token - Bearer token used for authenticated API requests performed by the view.
 * @param {(bom: Object) => void} onCreateProductionOrder - Callback invoked with the BOM when the user requests to create a production order.
 * @returns {JSX.Element} The BOM detail view component.
 */
function BOMDetailView({
  bom,
  onClose,
  onUpdate,
  token,
  onCreateProductionOrder,
}) {
  const toast = useToast();
  const [lines, setLines] = useState(bom.lines || []);
  const [loading, setLoading] = useState(false);
  const [editingLine, setEditingLine] = useState(null);
  const [purchaseLine, setPurchaseLine] = useState(null);
  const [newLine, setNewLine] = useState({
    component_id: "",
    quantity: "1",
    sequence: lines.length + 1,
    scrap_factor: "0",
    notes: "",
  });
  const [showAddLine, setShowAddLine] = useState(false);
  const [products, setProducts] = useState([]);

  // Sub-assembly state
  const [showExploded, setShowExploded] = useState(false);
  const [explodedData, setExplodedData] = useState(null);
  const [costRollup, setCostRollup] = useState(null);
  const [expandedSubs, setExpandedSubs] = useState(new Set());

  // Process Path / Routing state
  const [routingTemplates, setRoutingTemplates] = useState([]);
  const [productRouting, setProductRouting] = useState(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [timeOverrides, setTimeOverrides] = useState({});
  const [applyingTemplate, setApplyingTemplate] = useState(false);
  const [showProcessPath, setShowProcessPath] = useState(true);

  useEffect(() => {
    fetchProducts();
    fetchCostRollup();
    fetchRoutingTemplates();
    fetchProductRouting();
  }, []);

  const fetchCostRollup = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/bom/${bom.id}/cost-rollup`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setCostRollup(data);
      }
    } catch (err) {
      // Cost rollup fetch failure is non-critical - cost display will just be empty
    }
  };

  const fetchRoutingTemplates = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/routings?templates_only=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setRoutingTemplates(data.items || data);
      }
    } catch (err) {
      // Routing templates fetch failure is non-critical - templates list will just be empty
    }
  };

  const fetchProductRouting = async () => {
    if (!bom.product_id) return;
    try {
      const res = await fetch(
        `${API_URL}/api/v1/routings?product_id=${bom.product_id}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        const items = data.items || data;
        // Find the active routing for this product
        const activeRouting = items.find((r) => r.is_active && !r.is_template);
        if (activeRouting) {
          // Fetch full routing with operations
          const detailRes = await fetch(
            `${API_URL}/api/v1/routings/${activeRouting.id}`,
            {
              headers: { Authorization: `Bearer ${token}` },
            }
          );
          if (detailRes.ok) {
            const routingDetail = await detailRes.json();
            setProductRouting(routingDetail);
            // Initialize time overrides from existing routing
            const overrides = {};
            routingDetail.operations?.forEach((op) => {
              if (op.operation_code) {
                overrides[op.operation_code] = {
                  run_time_minutes: parseFloat(op.run_time_minutes || 0),
                  setup_time_minutes: parseFloat(op.setup_time_minutes || 0),
                };
              }
            });
            setTimeOverrides(overrides);
          }
        }
      }
    } catch (err) {
      // Product routing fetch failure is non-critical - routing section will just be empty
    }
  };

  const handleApplyTemplate = async () => {
    if (!selectedTemplateId || !bom.product_id) return;

    setApplyingTemplate(true);
    try {
      // Convert timeOverrides to the format expected by the API
      const overrides = Object.entries(timeOverrides)
        .filter(
          ([_, val]) =>
            val.run_time_minutes !== undefined ||
            val.setup_time_minutes !== undefined
        )
        .map(([code, val]) => ({
          operation_code: code,
          run_time_minutes: val.run_time_minutes,
          setup_time_minutes: val.setup_time_minutes,
        }));

      const res = await fetch(`${API_URL}/api/v1/routings/apply-template`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          product_id: bom.product_id,
          template_id: parseInt(selectedTemplateId),
          overrides,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        setProductRouting(result);
        // Update time overrides from result
        const newOverrides = {};
        result.operations?.forEach((op) => {
          if (op.operation_code) {
            newOverrides[op.operation_code] = {
              run_time_minutes: parseFloat(op.run_time_minutes || 0),
              setup_time_minutes: parseFloat(op.setup_time_minutes || 0),
            };
          }
        });
        setTimeOverrides(newOverrides);
        setSelectedTemplateId("");
      } else {
        const errData = await res.json();
        toast.error(`Failed to apply routing template: ${errData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to apply routing template: ${err.message || "Network error"}`);
    } finally {
      setApplyingTemplate(false);
    }
  };

  const updateOperationTime = (opCode, field, value) => {
    setTimeOverrides((prev) => ({
      ...prev,
      [opCode]: {
        ...prev[opCode],
        [field]: parseFloat(value) || 0,
      },
    }));
  };

  // Save operation time to server and refresh routing
  const saveOperationTime = async (operationId, field, value) => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/routings/operations/${operationId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            [field]: parseFloat(value) || 0,
          }),
        }
      );

      if (res.ok) {
        // Refresh the routing to get updated costs
        await fetchProductRouting();
      } else {
        const errData = await res.json();
        toast.error(`Failed to update operation: ${errData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to update operation: ${err.message || "Network error"}`);
    }
  };

  // Calculate total process cost from routing
  const calculateProcessCost = () => {
    if (!productRouting) return 0;
    return parseFloat(productRouting.total_cost || 0);
  };

  // Format minutes to hours:minutes
  const formatTime = (minutes) => {
    const mins = parseFloat(minutes || 0);
    if (mins < 60) return `${mins.toFixed(0)}m`;
    const hrs = Math.floor(mins / 60);
    const remainingMins = Math.round(mins % 60);
    return remainingMins > 0 ? `${hrs}h ${remainingMins}m` : `${hrs}h`;
  };

  const fetchExploded = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom/${bom.id}/explode`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setExplodedData(data);
        setShowExploded(true);
      } else {
        toast.error("Failed to load exploded BOM view. Please try again.");
      }
    } catch (err) {
      toast.error(`Failed to load exploded BOM: ${err.message || "Network error"}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleSubAssembly = (componentId) => {
    const newExpanded = new Set(expandedSubs);
    if (newExpanded.has(componentId)) {
      newExpanded.delete(componentId);
    } else {
      newExpanded.add(componentId);
    }
    setExpandedSubs(newExpanded);
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/products?limit=500&is_raw_material=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || data);
      }
    } catch (err) {
      setError("Failed to load products. Please refresh the page.");
    }
  };

  const handleAddLine = async () => {
    if (!newLine.component_id) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom/${bom.id}/lines`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          component_id: parseInt(newLine.component_id),
          quantity: parseFloat(newLine.quantity),
          sequence: parseInt(newLine.sequence),
          scrap_factor: parseFloat(newLine.scrap_factor),
          notes: newLine.notes || null,
        }),
      });

      if (res.ok) {
        const addedLine = await res.json();
        setLines([...lines, addedLine]);
        setNewLine({
          component_id: "",
          quantity: "1",
          sequence: lines.length + 2,
          scrap_factor: "0",
          notes: "",
        });
        setShowAddLine(false);
        onUpdate();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to add BOM line: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to add BOM line: ${err.message || "Network error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateLine = async (lineId, updates) => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/bom/${bom.id}/lines/${lineId}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(updates),
        }
      );

      if (res.ok) {
        const updatedLine = await res.json();
        setLines(lines.map((l) => (l.id === lineId ? updatedLine : l)));
        setEditingLine(null);
        onUpdate();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to update BOM line: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to update BOM line: ${err.message || "Network error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteLine = async (lineId) => {
    if (!confirm("Are you sure you want to delete this line?")) return;

    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/bom/${bom.id}/lines/${lineId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.ok) {
        setLines(lines.filter((l) => l.id !== lineId));
        onUpdate();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to delete BOM line: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to delete BOM line: ${err.message || "Network error"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/bom/${bom.id}/recalculate`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.ok) {
        onUpdate();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to recalculate BOM cost: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to recalculate BOM cost: ${err.message || "Network error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* BOM Header Info */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">Code:</span>
          <span className="text-white ml-2">{bom.code}</span>
        </div>
        <div>
          <span className="text-gray-400">Version:</span>
          <span className="text-white ml-2">
            {bom.version} ({bom.revision})
          </span>
        </div>
        <div>
          <span className="text-gray-400">Product:</span>
          <span className="text-white ml-2">
            {bom.product?.name || bom.product_id}
          </span>
        </div>
        <div>
          <span className="text-gray-400">
            {productRouting ? "Material Cost:" : "Total Cost:"}
          </span>
          <span className="text-white ml-2">
            ${parseFloat(bom.total_cost || 0).toFixed(2)}
          </span>
          {productRouting && (
            <>
              <span className="text-gray-400 ml-4">+ Process:</span>
              <span className="text-amber-400 ml-1">
                ${calculateProcessCost().toFixed(2)}
              </span>
              <span className="text-gray-400 ml-4">= Total:</span>
              <span className="text-green-400 ml-1 font-semibold">
                $
                {(
                  parseFloat(bom.total_cost || 0) + calculateProcessCost()
                ).toFixed(2)}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Cost Rollup Display */}
      {costRollup && costRollup.has_sub_assemblies && (
        <div className="bg-gradient-to-r from-purple-600/10 to-blue-600/10 border border-purple-500/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5 text-purple-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              <span className="text-purple-300 font-medium">
                Multi-Level BOM
              </span>
            </div>
            <span className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded-full">
              {costRollup.sub_assembly_count} Sub-Assemblies
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Direct Cost:</span>
              <span className="text-white ml-2">
                ${parseFloat(costRollup.direct_cost || 0).toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Sub-Assembly Cost:</span>
              <span className="text-purple-400 ml-2">
                ${parseFloat(costRollup.sub_assembly_cost || 0).toFixed(2)}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Rolled-Up Total:</span>
              <span className="text-green-400 ml-2 font-semibold">
                ${parseFloat(costRollup.rolled_up_cost || 0).toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={handleRecalculate}
          disabled={loading}
          className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          Recalculate Cost
        </button>
        <button
          onClick={() => setShowAddLine(true)}
          disabled={loading}
          className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
        >
          Add Component
        </button>
        <button
          onClick={fetchExploded}
          disabled={loading}
          className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50 flex items-center gap-1"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 10h16M4 14h16M4 18h16"
            />
          </svg>
          Explode BOM
        </button>
        <button
          onClick={() => onCreateProductionOrder(bom)}
          className="px-3 py-1.5 bg-gradient-to-r from-orange-600 to-amber-600 text-white rounded-lg text-sm hover:from-orange-500 hover:to-amber-500 flex items-center gap-1"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          Create Production Order
        </button>
      </div>

      {/* BOM Lines Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800">
            <tr>
              <th className="text-left py-2 px-3 text-gray-400">#</th>
              <th className="text-left py-2 px-3 text-gray-400">Component</th>
              <th className="text-left py-2 px-3 text-gray-400">Qty Needed</th>
              <th className="text-left py-2 px-3 text-gray-400">Unit Cost</th>
              <th className="text-left py-2 px-3 text-gray-400">Line Cost</th>
              <th className="text-left py-2 px-3 text-gray-400">Inventory</th>
              <th className="text-right py-2 px-3 text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr
                key={line.id}
                className={`border-b border-gray-800 ${
                  !line.is_available ? "bg-red-500/5" : ""
                }`}
              >
                <td className="py-2 px-3 text-gray-500">{line.sequence}</td>
                <td className="py-2 px-3">
                  <div className="flex items-center gap-2">
                    <div>
                      <div className="text-white font-medium flex items-center gap-1.5">
                        {line.component_name || `Product #${line.component_id}`}
                        {line.has_bom && (
                          <span
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded text-xs"
                            title="Sub-assembly - has its own BOM"
                          >
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                              />
                            </svg>
                            Sub
                          </span>
                        )}
                      </div>
                      <div className="text-gray-500 text-xs">
                        {line.component_sku}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="py-2 px-3 text-gray-300">
                  {editingLine === line.id ? (
                    <input
                      type="number"
                      defaultValue={line.quantity}
                      step="0.01"
                      className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                      onBlur={(e) =>
                        handleUpdateLine(line.id, {
                          quantity: parseFloat(e.target.value),
                        })
                      }
                    />
                  ) : (
                    <span>
                      {parseFloat(line.quantity).toFixed(2)}{" "}
                      {line.component_unit || ""}
                    </span>
                  )}
                </td>
                <td className="py-2 px-3 text-gray-400">
                  ${parseFloat(line.component_cost || 0).toFixed(2)}/
                  {line.component_unit || "ea"}
                </td>
                <td className="py-2 px-3 text-green-400 font-medium">
                  ${parseFloat(line.line_cost || 0).toFixed(2)}
                </td>
                <td className="py-2 px-3">
                  {line.is_available ? (
                    <span className="inline-flex items-center gap-1 text-green-400">
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-xs">
                        In Stock ({line.inventory_available?.toFixed(1)})
                      </span>
                    </span>
                  ) : (
                    <div className="space-y-1">
                      <span className="inline-flex items-center gap-1 text-red-400">
                        <svg
                          className="w-4 h-4"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="text-xs">
                          Need {line.shortage?.toFixed(2)}
                        </span>
                      </span>
                      <button
                        onClick={() => setPurchaseLine(line)}
                        className="block text-xs text-blue-400 hover:text-blue-300 underline"
                      >
                        Create PO
                      </button>
                    </div>
                  )}
                </td>
                <td className="py-2 px-3 text-right">
                  <button
                    onClick={() =>
                      setEditingLine(editingLine === line.id ? null : line.id)
                    }
                    className="text-blue-400 hover:text-blue-300 px-2"
                  >
                    {editingLine === line.id ? "Done" : "Edit"}
                  </button>
                  <button
                    onClick={() => handleDeleteLine(line.id)}
                    className="text-red-400 hover:text-red-300 px-2"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {lines.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-gray-500">
                  No components added yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Process Path / Routing Section */}
      {showProcessPath && (
        <div className="bg-gradient-to-r from-amber-600/10 to-orange-600/10 border border-amber-500/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5 text-amber-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                />
              </svg>
              <span className="text-amber-300 font-medium">Process Path</span>
            </div>
            {productRouting && (
              <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-1 rounded-full">
                {productRouting.operations?.length || 0} Operations
              </span>
            )}
          </div>

          {/* No routing yet - show template selector */}
          {!productRouting && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400">
                No routing defined. Select a template to create one:
              </p>
              <div className="flex gap-2">
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
                >
                  <option value="">Select a routing template...</option>
                  {routingTemplates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} - {t.name || "Unnamed"} ({t.operation_count || 0}{" "}
                      ops, {formatTime(t.total_run_time_minutes)})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleApplyTemplate}
                  disabled={!selectedTemplateId || applyingTemplate}
                  className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-700 disabled:opacity-50"
                >
                  {applyingTemplate ? "Applying..." : "Apply Template"}
                </button>
              </div>
            </div>
          )}

          {/* Existing routing - show operations */}
          {productRouting && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">
                  Routing:{" "}
                  <span className="text-white">
                    {productRouting.code || productRouting.routing_code}
                  </span>
                </span>
                <span className="text-gray-400">
                  Total Time:{" "}
                  <span className="text-amber-400 font-medium">
                    {formatTime(productRouting.total_run_time_minutes)}
                  </span>
                </span>
              </div>

              {/* Operations table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-800/50">
                    <tr>
                      <th className="text-left py-2 px-3 text-gray-400">#</th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Operation
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Work Center
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Run Time
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Setup
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Cost
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(productRouting.operations || []).map((op, idx) => (
                      <tr
                        key={op.id || idx}
                        className="border-b border-gray-800"
                      >
                        <td className="py-2 px-3 text-gray-500">
                          {op.sequence}
                        </td>
                        <td className="py-2 px-3">
                          <div className="text-white font-medium">
                            {op.operation_name || op.operation_code}
                          </div>
                          {op.operation_code && op.operation_name && (
                            <div className="text-gray-500 text-xs">
                              {op.operation_code}
                            </div>
                          )}
                        </td>
                        <td className="py-2 px-3 text-gray-400">
                          {op.work_center_name || op.work_center_code}
                        </td>
                        <td className="py-2 px-3">
                          <input
                            type="number"
                            step="0.1"
                            value={
                              timeOverrides[op.operation_code]
                                ?.run_time_minutes ??
                              parseFloat(op.run_time_minutes || 0)
                            }
                            onChange={(e) =>
                              updateOperationTime(
                                op.operation_code,
                                "run_time_minutes",
                                e.target.value
                              )
                            }
                            onBlur={(e) =>
                              saveOperationTime(
                                op.id,
                                "run_time_minutes",
                                e.target.value
                              )
                            }
                            className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
                          />
                          <span className="text-gray-500 text-xs ml-1">
                            min
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <input
                            type="number"
                            step="0.1"
                            value={
                              timeOverrides[op.operation_code]
                                ?.setup_time_minutes ??
                              parseFloat(op.setup_time_minutes || 0)
                            }
                            onChange={(e) =>
                              updateOperationTime(
                                op.operation_code,
                                "setup_time_minutes",
                                e.target.value
                              )
                            }
                            onBlur={(e) =>
                              saveOperationTime(
                                op.id,
                                "setup_time_minutes",
                                e.target.value
                              )
                            }
                            className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
                          />
                          <span className="text-gray-500 text-xs ml-1">
                            min
                          </span>
                        </td>
                        <td className="py-2 px-3 text-green-400">
                          ${parseFloat(op.calculated_cost || 0).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Actions for existing routing */}
              <div className="flex gap-2 pt-2 border-t border-gray-700">
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm"
                >
                  <option value="">Change template...</option>
                  {routingTemplates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.code} - {t.name || "Unnamed"}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleApplyTemplate}
                  disabled={!selectedTemplateId || applyingTemplate}
                  className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-700 disabled:opacity-50"
                >
                  {applyingTemplate ? "Applying..." : "Apply"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Line Form */}
      {showAddLine && (
        <div className="bg-gray-800 rounded-lg p-4 space-y-4">
          <h4 className="font-medium text-white">Add Component</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Component
              </label>
              <select
                value={newLine.component_id}
                onChange={(e) =>
                  setNewLine({ ...newLine, component_id: e.target.value })
                }
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
              >
                <option value="">Select component...</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.sku}) - ${parseFloat(p.cost || 0).toFixed(2)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Quantity
              </label>
              <input
                type="number"
                step="0.01"
                value={newLine.quantity}
                onChange={(e) =>
                  setNewLine({ ...newLine, quantity: e.target.value })
                }
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Scrap Factor %
              </label>
              <input
                type="number"
                step="0.1"
                value={newLine.scrap_factor}
                onChange={(e) =>
                  setNewLine({ ...newLine, scrap_factor: e.target.value })
                }
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Notes</label>
              <input
                type="text"
                value={newLine.notes}
                onChange={(e) =>
                  setNewLine({ ...newLine, notes: e.target.value })
                }
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleAddLine}
              disabled={loading || !newLine.component_id}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Add Component
            </button>
            <button
              onClick={() => setShowAddLine(false)}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex justify-end pt-4 border-t border-gray-800">
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          Close
        </button>
      </div>

      {/* Purchase Request Modal */}
      <Modal
        isOpen={!!purchaseLine}
        onClose={() => setPurchaseLine(null)}
        title="Create Purchase Request"
      >
        {purchaseLine && (
          <PurchaseRequestModal
            line={purchaseLine}
            onClose={() => setPurchaseLine(null)}
            token={token}
          />
        )}
      </Modal>

      {/* Exploded BOM View Modal */}
      {showExploded && explodedData && (
        <div className="fixed inset-0 z-[60] overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/80"
              onClick={() => setShowExploded(false)}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-4xl w-full mx-auto p-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-white">
                    Exploded BOM View
                  </h3>
                  <p className="text-sm text-gray-400">
                    All components flattened through sub-assemblies
                  </p>
                </div>
                <button
                  onClick={() => setShowExploded(false)}
                  className="text-gray-400 hover:text-white p-1"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-white">
                    {explodedData.total_components}
                  </div>
                  <div className="text-xs text-gray-400">Total Components</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-purple-400">
                    {explodedData.max_depth}
                  </div>
                  <div className="text-xs text-gray-400">Max Depth</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-400">
                    ${parseFloat(explodedData.total_cost || 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-400">Total Cost</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {explodedData.unique_components}
                  </div>
                  <div className="text-xs text-gray-400">Unique Parts</div>
                </div>
              </div>

              {/* Exploded Lines Table */}
              <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-800 sticky top-0">
                    <tr>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Level
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Component
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Qty/Unit
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Extended Qty
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Unit Cost
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Line Cost
                      </th>
                      <th className="text-left py-2 px-3 text-gray-400">
                        Stock
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {explodedData.lines?.map((line, idx) => (
                      <tr
                        key={idx}
                        className={`border-b border-gray-800 ${
                          line.is_sub_assembly ? "bg-purple-500/5" : ""
                        }`}
                      >
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-1">
                            {/* Indent based on level */}
                            <span
                              style={{ marginLeft: `${line.level * 12}px` }}
                              className="text-gray-500"
                            >
                              {line.level === 0 ? "" : "└─"}
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-xs ${
                                line.level === 0
                                  ? "bg-blue-500/20 text-blue-400"
                                  : line.level === 1
                                  ? "bg-green-500/20 text-green-400"
                                  : line.level === 2
                                  ? "bg-yellow-500/20 text-yellow-400"
                                  : "bg-gray-500/20 text-gray-400"
                              }`}
                            >
                              L{line.level}
                            </span>
                          </div>
                        </td>
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-2">
                            <div>
                              <div className="text-white font-medium flex items-center gap-1">
                                {line.component_name}
                                {line.is_sub_assembly && (
                                  <span className="text-purple-400 text-xs">
                                    (Sub)
                                  </span>
                                )}
                              </div>
                              <div className="text-gray-500 text-xs">
                                {line.component_sku}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-2 px-3 text-gray-400">
                          {parseFloat(line.quantity_per_unit || 0).toFixed(2)}
                        </td>
                        <td className="py-2 px-3 text-white font-medium">
                          {parseFloat(line.extended_quantity || 0).toFixed(2)}
                        </td>
                        <td className="py-2 px-3 text-gray-400">
                          ${parseFloat(line.unit_cost || 0).toFixed(2)}
                        </td>
                        <td className="py-2 px-3 text-green-400">
                          ${parseFloat(line.line_cost || 0).toFixed(2)}
                        </td>
                        <td className="py-2 px-3">
                          {line.inventory_available >=
                          line.extended_quantity ? (
                            <span className="text-green-400 text-xs">
                              OK ({line.inventory_available?.toFixed(1)})
                            </span>
                          ) : (
                            <span className="text-red-400 text-xs">
                              Low ({line.inventory_available?.toFixed(1)})
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex justify-end pt-4 border-t border-gray-800 mt-4">
                <button
                  onClick={() => setShowExploded(false)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Create BOM Form
function CreateBOMForm({ onClose, onCreate, token }) {
  const [formData, setFormData] = useState({
    product_id: "",
    name: "",
    revision: "1.0",
  });
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/products?limit=500&is_raw_material=false`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || data);
      }
    } catch (err) {
      setError("Failed to load products. Please refresh the page.");
    }
  }, [token]);

  useEffect(() => {
    fetchProducts();
    // Check if user just created an item and came back
    const bomPending = sessionStorage.getItem("bom_creation_pending");
    if (bomPending) {
      sessionStorage.removeItem("bom_creation_pending");
      // Refresh products list after a short delay to allow item creation to complete
      setTimeout(() => {
        fetchProducts();
      }, 500);
    }
  }, [fetchProducts]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.product_id) {
      setError("Please select a product");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          product_id: parseInt(formData.product_id),
          name: formData.name || null,
          revision: formData.revision,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create BOM");
      }

      const newBom = await res.json();
      onCreate(newBom);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="block text-sm text-gray-400">Product *</label>
          <Link
            to="/admin/items?action=new"
            className="text-xs text-blue-400 hover:text-blue-300 underline"
            onClick={() => {
              // Store that we're coming from BOM creation
              sessionStorage.setItem("bom_creation_pending", "true");
            }}
          >
            + Create New Item
          </Link>
        </div>
        <select
          value={formData.product_id}
          onChange={(e) =>
            setFormData({ ...formData, product_id: e.target.value })
          }
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          required
        >
          <option value="">Select a product...</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.sku})
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Don't see the product?{" "}
          <Link
            to="/admin/items?action=new"
            className="text-blue-400 hover:text-blue-300 underline"
            onClick={() =>
              sessionStorage.setItem("bom_creation_pending", "true")
            }
          >
            Create it first
          </Link>
          , then return here.
        </p>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">
          BOM Name (optional)
        </label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Auto-generated if empty"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Revision</label>
        <input
          type="text"
          value={formData.revision}
          onChange={(e) =>
            setFormData({ ...formData, revision: e.target.value })
          }
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
        />
      </div>

      <div className="flex gap-2 pt-4">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create BOM"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

// Production Order Modal
function CreateProductionOrderModal({
  bom,
  quoteContext,
  onClose,
  token,
  onSuccess,
}) {
  // Calculate max producible based on inventory
  const calculateMaxProducible = () => {
    if (!bom.lines || bom.lines.length === 0) return Infinity;

    let maxUnits = Infinity;
    for (const line of bom.lines) {
      const qtyPerUnit = parseFloat(line.quantity) || 0;
      const available = parseFloat(line.inventory_available) || 0;
      if (qtyPerUnit > 0) {
        const canMake = Math.floor(available / qtyPerUnit);
        maxUnits = Math.min(maxUnits, canMake);
      }
    }
    return maxUnits === Infinity ? 0 : maxUnits;
  };

  const maxProducible = calculateMaxProducible();
  const quotedQty = quoteContext?.quantity || 1;

  // Default to quoted quantity if available
  const [quantity, setQuantity] = useState(quotedQty);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [createBackorder, setCreateBackorder] = useState(false);

  // Check if we can fulfill the entire order
  const canFulfillAll = maxProducible >= quantity;
  const backorderQty = quantity - maxProducible;

  // Find limiting component
  const getLimitingComponent = () => {
    if (!bom.lines || bom.lines.length === 0) return null;

    let limitingLine = null;
    let minUnits = Infinity;

    for (const line of bom.lines) {
      const qtyPerUnit = parseFloat(line.quantity) || 0;
      const available = parseFloat(line.inventory_available) || 0;
      if (qtyPerUnit > 0) {
        const canMake = Math.floor(available / qtyPerUnit);
        if (canMake < minUnits) {
          minUnits = canMake;
          limitingLine = line;
        }
      }
    }
    return limitingLine;
  };

  const limitingComponent = getLimitingComponent();

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Generate a production order code (PO-YYYY-NNN format)
      const year = new Date().getFullYear();
      const timestamp = Date.now().toString().slice(-4);
      const poCode = `PO-${year}-${timestamp}`;

      // Determine actual quantity to produce
      const produceQty =
        createBackorder && !canFulfillAll ? maxProducible : quantity;

      const res = await fetch(
        `${API_URL}/api/v1/production-orders?auto_start_print=false`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            code: poCode,
            product_id: bom.product_id,
            product_sku: bom.product_sku || `PROD-${bom.product_id}`,
            product_name: bom.product_name || `Product #${bom.product_id}`,
            quantity: produceQty,
            priority: "normal",
            notes:
              createBackorder && backorderQty > 0
                ? `${
                    notes ? notes + "\n" : ""
                  }Partial fulfillment: ${produceQty} of ${quantity} ordered. Backorder: ${backorderQty} units pending materials.`
                : notes || null,
          }),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create production order");
      }

      const newOrder = await res.json();

      // TODO: If createBackorder is true, could also create a backorder record
      // For now, just include it in the notes

      onSuccess(newOrder);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="bg-gray-800 rounded-lg p-4">
        <div className="text-sm text-gray-400 mb-1">Product</div>
        <div className="text-white font-medium">
          {bom.product_name || `Product #${bom.product_id}`}
        </div>
        <div className="text-gray-500 text-xs">{bom.product_sku}</div>
      </div>

      {/* Quote Context Banner */}
      {quoteContext && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span>
              From Quote: <strong>{quotedQty} units</strong> ordered
            </span>
          </div>
        </div>
      )}

      {/* Inventory Status */}
      <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Inventory Status</span>
          <span
            className={`text-sm font-medium ${
              maxProducible >= quotedQty
                ? "text-green-400"
                : maxProducible > 0
                ? "text-yellow-400"
                : "text-red-400"
            }`}
          >
            Can produce: {maxProducible} units
          </span>
        </div>
        {limitingComponent && maxProducible < quotedQty && (
          <div className="text-xs text-gray-500">
            Limiting factor:{" "}
            <span className="text-yellow-400">
              {limitingComponent.component_name}
            </span>{" "}
            ({limitingComponent.inventory_available?.toFixed(2)}{" "}
            {limitingComponent.component_unit} available)
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-400">BOM:</span>
          <span className="text-white ml-2">{bom.code}</span>
        </div>
        <div>
          <span className="text-gray-400">Version:</span>
          <span className="text-white ml-2">v{bom.version}</span>
        </div>
        <div>
          <span className="text-gray-400">Components:</span>
          <span className="text-white ml-2">{bom.lines?.length || 0}</span>
        </div>
        <div>
          <span className="text-gray-400">Unit Cost:</span>
          <span className="text-green-400 ml-2">
            ${parseFloat(bom.total_cost || 0).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Quantity Input with Quick Set Buttons */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">
          Quantity to Produce
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          />
          {quoteContext && (
            <button
              type="button"
              onClick={() => setQuantity(quotedQty)}
              className={`px-3 py-2 rounded-lg text-sm ${
                quantity === quotedQty
                  ? "bg-blue-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              Quoted ({quotedQty})
            </button>
          )}
          {maxProducible > 0 && maxProducible !== quotedQty && (
            <button
              type="button"
              onClick={() => setQuantity(maxProducible)}
              className={`px-3 py-2 rounded-lg text-sm ${
                quantity === maxProducible
                  ? "bg-green-600 text-white"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              Max ({maxProducible})
            </button>
          )}
        </div>
      </div>

      {/* Partial Fulfillment Warning & Option */}
      {!canFulfillAll && quantity > 0 && maxProducible > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 text-yellow-400 text-sm font-medium mb-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Insufficient Inventory
          </div>
          <p className="text-sm text-gray-300 mb-3">
            You can only produce <strong>{maxProducible}</strong> of{" "}
            <strong>{quantity}</strong> units with current inventory.
          </p>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={createBackorder}
              onChange={(e) => setCreateBackorder(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-300">
              Create partial order ({maxProducible} units) + backorder (
              {backorderQty} units)
            </span>
          </label>
        </div>
      )}

      {/* Zero Inventory Warning */}
      {maxProducible === 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 text-red-400 text-sm font-medium">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            No inventory available - cannot produce any units
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Order materials before creating a production order.
          </p>
        </div>
      )}

      <div>
        <label className="block text-sm text-gray-400 mb-1">
          Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          placeholder="Production notes..."
        />
      </div>

      <div className="bg-gray-800 rounded-lg p-3">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Estimated Total Cost:</span>
          <span className="text-green-400 font-medium">
            $
            {(
              parseFloat(bom.total_cost || 0) *
              (createBackorder && !canFulfillAll ? maxProducible : quantity)
            ).toFixed(2)}
          </span>
        </div>
        {createBackorder && !canFulfillAll && (
          <div className="flex justify-between text-sm mt-1">
            <span className="text-gray-500">
              Backorder ({backorderQty} units):
            </span>
            <span className="text-gray-400">
              ${(parseFloat(bom.total_cost || 0) * backorderQty).toFixed(2)}{" "}
              (pending)
            </span>
          </div>
        )}
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={handleSubmit}
          disabled={
            loading || quantity < 1 || (maxProducible === 0 && !createBackorder)
          }
          className="flex-1 px-4 py-2 bg-gradient-to-r from-orange-600 to-amber-600 text-white rounded-lg hover:from-orange-500 hover:to-amber-500 disabled:opacity-50"
        >
          {loading
            ? "Creating..."
            : createBackorder && !canFulfillAll
            ? `Create Order (${maxProducible} units)`
            : "Create Production Order"}
        </button>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/**
 * Render the Bill of Materials administration interface including list view, filters, and modals for viewing, creating, copying, deleting BOMs, and creating production orders.
 *
 * The component manages fetching BOM data, URL-driven auto-opening of a BOM, local UI state for modals and selected items, and user actions (view, copy, delete, create production order). It obtains an auth token from localStorage and uses toast notifications for user feedback.
 *
 * @returns {JSX.Element} A React element representing the Admin BOM management UI.
 */
export default function AdminBOM() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [boms, setBoms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBOM, setSelectedBOM] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showProductionModal, setShowProductionModal] = useState(false);
  const [productionBOM, setProductionBOM] = useState(null);
  const [filters, setFilters] = useState({
    search: searchParams.get("search") || "",
    active: searchParams.get("active") || "all",
  });

  const token = localStorage.getItem("adminToken");
  const productId = searchParams.get("product");
  const quotedQuantity = searchParams.get("quantity");
  const quoteId = searchParams.get("quote_id");

  // Store quote context for production order creation
  const [quoteContext, setQuoteContext] = useState(null);

  useEffect(() => {
    fetchBOMs();
  }, [filters]);

  // Auto-open BOM for a specific product if passed in URL
  useEffect(() => {
    if (productId && boms.length > 0) {
      const matchingBOM = boms.find(
        (b) => b.product_id === parseInt(productId)
      );
      if (matchingBOM) {
        // Store quote context before clearing params
        if (quotedQuantity || quoteId) {
          setQuoteContext({
            quantity: parseInt(quotedQuantity) || 1,
            quoteId: quoteId ? parseInt(quoteId) : null,
          });
        }
        handleViewBOM(matchingBOM.id);
        // Clear the params after opening
        setSearchParams({});
      }
    }
  }, [productId, boms]);

  const fetchBOMs = async () => {
    if (!token) return;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.search) params.set("search", filters.search);
      if (filters.active !== "all")
        params.set("active", filters.active === "active");

      const res = await fetch(`${API_URL}/api/v1/admin/bom?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to fetch BOMs");

      const data = await res.json();
      setBoms(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewBOM = async (bomId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom/${bomId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to fetch BOM details");

      const data = await res.json();
      setSelectedBOM(data);
    } catch (err) {
      setError(`Failed to load BOM: ${err.message || "Unknown error"}`);
    }
  };

  const handleDeleteBOM = async (bomId) => {
    if (!confirm("Are you sure you want to delete this BOM?")) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom/${bomId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        toast.success("BOM deleted");
        fetchBOMs();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to delete BOM: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to delete BOM: ${err.message || "Network error"}`);
    }
  };

  const handleCopyBOM = async (bomId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/bom/${bomId}/copy`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        toast.success("BOM copied");
        fetchBOMs();
      } else {
        const errorData = await res.json();
        toast.error(`Failed to copy BOM: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to copy BOM: ${err.message || "Network error"}`);
    }
  };

  const handleCreateProductionOrder = (bom) => {
    setProductionBOM(bom);
    setShowProductionModal(true);
  };

  const handleProductionOrderCreated = (newOrder) => {
    setShowProductionModal(false);
    setProductionBOM(null);
    setSelectedBOM(null);
    // Navigate to production orders page to see the new order
    navigate(`/admin/production?order=${newOrder.id}`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Bill of Materials</h1>
          <p className="text-gray-400 mt-1">
            Manage product BOMs and components
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500"
        >
          + Create BOM
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by code, name, or product..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500"
          />
        </div>
        <select
          value={filters.active}
          onChange={(e) => setFilters({ ...filters, active: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
        >
          <option value="all">All Status</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* BOM List */}
      {!loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Code
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Name
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Product
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Version
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Components
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Total Cost
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Status
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {boms.map((bom) => (
                <tr
                  key={bom.id}
                  className="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td className="py-3 px-4 text-white font-medium">
                    {bom.code}
                  </td>
                  <td className="py-3 px-4 text-gray-300">{bom.name}</td>
                  <td className="py-3 px-4 text-gray-400">
                    {bom.product?.name || `#${bom.product_id}`}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    v{bom.version} ({bom.revision})
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {bom.line_count || 0}
                  </td>
                  <td className="py-3 px-4 text-green-400 font-medium">
                    ${parseFloat(bom.total_cost || 0).toFixed(2)}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        bom.active
                          ? "bg-green-500/20 text-green-400"
                          : "bg-gray-500/20 text-gray-400"
                      }`}
                    >
                      {bom.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={() => handleViewBOM(bom.id)}
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      View
                    </button>
                    <button
                      onClick={() => handleCopyBOM(bom.id)}
                      className="text-purple-400 hover:text-purple-300 text-sm"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() => handleDeleteBOM(bom.id)}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {boms.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-gray-500">
                    No BOMs found. Create your first BOM to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* BOM Detail Modal */}
      <Modal
        isOpen={!!selectedBOM}
        onClose={() => setSelectedBOM(null)}
        title={`BOM: ${selectedBOM?.code}`}
      >
        {selectedBOM && (
          <BOMDetailView
            bom={selectedBOM}
            onClose={() => setSelectedBOM(null)}
            onUpdate={() => {
              fetchBOMs();
              handleViewBOM(selectedBOM.id);
            }}
            token={token}
            onCreateProductionOrder={handleCreateProductionOrder}
          />
        )}
      </Modal>

      {/* Production Order Modal */}
      <Modal
        isOpen={showProductionModal}
        onClose={() => {
          setShowProductionModal(false);
          setProductionBOM(null);
        }}
        title="Create Production Order"
      >
        {productionBOM && (
          <CreateProductionOrderModal
            bom={productionBOM}
            quoteContext={quoteContext}
            onClose={() => {
              setShowProductionModal(false);
              setProductionBOM(null);
              setQuoteContext(null);
            }}
            token={token}
            onSuccess={handleProductionOrderCreated}
          />
        )}
      </Modal>

      {/* Create BOM Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New BOM"
      >
        <CreateBOMForm
          onClose={() => setShowCreateModal(false)}
          onCreate={(newBom) => {
            setShowCreateModal(false);
            fetchBOMs();
            handleViewBOM(newBom.id);
          }}
          token={token}
        />
      </Modal>
    </div>
  );
}