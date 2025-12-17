/**
 * OrderDetail - Order Command Center
 *
 * Comprehensive view for managing order fulfillment:
 * - Order header and line items
 * - Material requirements (BOM explosion)
 * - Capacity requirements (routing explosion)
 * - Action buttons (Create WO, Create PO, Schedule)
 */
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";
import RecordPaymentModal from "../../components/payments/RecordPaymentModal";
import ActivityTimeline from "../../components/ActivityTimeline";

export default function OrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const token = localStorage.getItem("adminToken");

  const [order, setOrder] = useState(null);
  const [materialRequirements, setMaterialRequirements] = useState([]);
  const [capacityRequirements, setCapacityRequirements] = useState([]);
  const [productionOrders, setProductionOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // Check if WOs exist for the main order line products (not sub-assemblies)
  const getMainProductWOs = () => {
    if (!order?.lines || order.lines.length === 0) return [];
    const lineProductIds = order.lines.map((line) => line.product_id);
    return productionOrders.filter(
      (po) => lineProductIds.includes(po.product_id) && po.sales_order_line_id
    );
  };

  const hasMainProductWO = () => {
    if (!order?.lines || order.lines.length === 0) {
      // Old style order with single product_id
      return productionOrders.some((po) => po.product_id === order?.product_id);
    }
    // Check if all line items have WOs
    const lineProductIds = order.lines.map((line) => line.product_id);
    const woProductIds = productionOrders
      .filter((po) => po.sales_order_line_id)
      .map((po) => po.product_id);
    return lineProductIds.every((pid) => woProductIds.includes(pid));
  };
  const [error, setError] = useState(null);
  const [exploding, setExploding] = useState(false);
  const [paymentSummary, setPaymentSummary] = useState(null);
  const [payments, setPayments] = useState([]);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [isRefund, setIsRefund] = useState(false);
  const [editingAddress, setEditingAddress] = useState(false);
  const [addressForm, setAddressForm] = useState({});
  const [savingAddress, setSavingAddress] = useState(false);

  // Cancel/Delete modal state
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancellationReason, setCancellationReason] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Refresh state
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (orderId) {
      fetchOrder();
      fetchProductionOrders();
      fetchPaymentData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const fetchOrder = async () => {
    if (!token) {
      setError("Not authenticated. Please log in.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    const url = `${API_URL}/api/v1/sales-orders/${orderId}`;

    try {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-cache",
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(
          `Failed to fetch order: ${res.status} ${res.statusText}`
        );
      }

      const data = await res.json();
      setOrder(data);

      // Explode BOM for material requirements
      if (
        data.order_type === "line_item" &&
        data.lines &&
        data.lines.length > 0
      ) {
        // Line-item order - use first line's product
        const firstLine = data.lines[0];
        if (firstLine.product_id) {
          await explodeBOM(firstLine.product_id, firstLine.quantity);
        }
      } else if (data.product_id) {
        // Order has product_id directly (quote-based or manual)
        await explodeBOM(data.product_id, data.quantity);
      } else if (data.quote_id) {
        // Fallback: fetch quote to get product_id (legacy orders)
        try {
          const quoteRes = await fetch(
            `${API_URL}/api/v1/quotes/${data.quote_id}`,
            {
              headers: { Authorization: `Bearer ${token}` },
            }
          );
          if (quoteRes.ok) {
            const quoteData = await quoteRes.json();
            if (quoteData.product_id) {
              await explodeBOM(quoteData.product_id, data.quantity);
            }
          }
        } catch (err) {
          // Quote fetch failure is non-critical - BOM explosion will just be skipped
        }
      }
    } catch (err) {
      if (err.message.includes("Failed to fetch")) {
        setError(
          `Network error: Cannot connect to backend at ${API_URL}. ` +
            `Please check if the backend server is running.`
        );
      } else {
        setError(err.message || "Failed to fetch order");
      }
      // Re-throw to allow handleRefresh to catch and show toast
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const fetchProductionOrders = async () => {
    if (!token || !orderId) return;
    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders?sales_order_id=${orderId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setProductionOrders(data.items || data || []);
      }
    } catch (err) {
      // Production orders fetch failure is non-critical - production list will just be empty
    }
  };

  const fetchPaymentData = async () => {
    if (!token || !orderId) return;
    try {
      // Fetch payment summary
      const summaryRes = await fetch(
        `${API_URL}/api/v1/payments/order/${orderId}/summary`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (summaryRes.ok) {
        setPaymentSummary(await summaryRes.json());
      }

      // Fetch payment history
      const paymentsRes = await fetch(
        `${API_URL}/api/v1/payments?order_id=${orderId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (paymentsRes.ok) {
        const data = await paymentsRes.json();
        setPayments(data.items || []);
      }
    } catch (err) {
      // Payment fetch failure is non-critical
    }
  };

  const handlePaymentRecorded = () => {
    setShowPaymentModal(false);
    setIsRefund(false);
    fetchPaymentData();
    fetchOrder(); // Refresh order to get updated payment_status
    toast.success(isRefund ? "Refund recorded" : "Payment recorded");
  };

  // Refresh all data
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        fetchOrder(),
        fetchProductionOrders(),
        fetchPaymentData(),
      ]);
      toast.success("Data refreshed");
    } catch (err) {
      toast.error("Failed to refresh");
    } finally {
      setRefreshing(false);
    }
  };

  const handleEditAddress = () => {
    setAddressForm({
      shipping_address_line1: order.shipping_address_line1 || "",
      shipping_address_line2: order.shipping_address_line2 || "",
      shipping_city: order.shipping_city || "",
      shipping_state: order.shipping_state || "",
      shipping_zip: order.shipping_zip || "",
      shipping_country: order.shipping_country || "USA",
    });
    setEditingAddress(true);
  };

  const handleSaveAddress = async () => {
    setSavingAddress(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${orderId}/address`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(addressForm),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update address");
      }

      toast.success("Shipping address updated");
      setEditingAddress(false);
      fetchOrder();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSavingAddress(false);
    }
  };

  const explodeBOM = async (productId, quantity) => {
    setExploding(true);
    try {
      // Use the MRP requirements endpoint which handles BOM explosion and netting
      const res = await fetch(
        `${API_URL}/api/v1/mrp/requirements?product_id=${productId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (res.ok) {
        const data = await res.json();

        // The endpoint returns requirements for quantity=1, so scale by order quantity
        // IMPORTANT: Calculate net_shortage AFTER scaling, not before
        const scaled = (data.requirements || []).map((req) => {
          const gross_qty = parseFloat(req.gross_quantity || 0) * quantity;
          const available_qty = parseFloat(req.available_quantity || 0);
          const incoming_qty = parseFloat(req.incoming_quantity || 0) || 0;
          const safety_stock = parseFloat(req.safety_stock || 0) || 0;

          // Recalculate net_shortage for scaled quantity
          const available_supply = available_qty + incoming_qty;
          let net_shortage = gross_qty - available_supply + safety_stock;

          if (net_shortage < 0) {
            net_shortage = 0;
          }

          return {
            product_id: req.product_id,
            product_sku: req.product_sku || "",
            product_name: req.product_name || "",
            gross_quantity: gross_qty,
            net_shortage: net_shortage,
            on_hand_quantity: parseFloat(req.on_hand_quantity || 0),
            available_quantity: available_qty,
            unit_cost: parseFloat(req.unit_cost || 0),
            has_bom: req.has_bom || false, // Make vs Buy indicator
          };
        });
        setMaterialRequirements(scaled);
      } else {
        // If MRP endpoint fails, try BOM explosion directly
        const bomRes = await fetch(
          `${API_URL}/api/v1/mrp/explode-bom/${productId}?quantity=${quantity}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (bomRes.ok) {
          const bomData = await bomRes.json();

          // Convert to requirements format (without inventory netting)
          const requirements = (bomData.components || []).map((comp) => ({
            product_id: comp.product_id,
            product_sku: comp.product_sku,
            product_name: comp.product_name,
            gross_quantity: parseFloat(comp.gross_quantity || 0),
            net_shortage: parseFloat(comp.gross_quantity || 0),
            on_hand_quantity: 0,
            available_quantity: 0,
            unit_cost: 0,
            has_bom: comp.has_bom || false, // Make vs Buy indicator
          }));
          setMaterialRequirements(requirements);
        } else {
          // BOM explosion failure - material requirements will be empty
        }
      }

      // Get routing for capacity requirements (optional)
      try {
        const routingRes = await fetch(
          `${API_URL}/api/v1/routings/product/${productId}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (routingRes.ok) {
          const routing = await routingRes.json();
          if (routing.operations && routing.operations.length > 0) {
            const capacity = routing.operations.map((op) => {
              // Ensure numeric values (API may return strings for decimals)
              const setupTime = parseFloat(op.setup_time_minutes) || 0;
              const runTime = parseFloat(op.run_time_minutes) || 0;
              return {
                ...op,
                setup_time_minutes: setupTime,
                run_time_minutes: runTime,
                total_time_minutes: setupTime + runTime * quantity,
                work_center_name:
                  op.work_center?.name || op.work_center_name || "N/A",
                operation_name:
                  op.operation_name || op.operation_code || "Operation",
              };
            });
            setCapacityRequirements(capacity);
          }
        }
      } catch (routingErr) {
        // Routing is optional - don't fail
      }
    } catch (err) {
      // BOM explosion failure - material requirements section will be empty
    } finally {
      setExploding(false);
    }
  };

  const handleCreateProductionOrder = async () => {
    const hasProduct =
      order?.product_id ||
      (order?.lines && order.lines.length > 0 && order.lines[0].product_id);
    if (!order || !hasProduct) {
      toast.error("Order must have a product to create production order");
      return;
    }

    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${orderId}/generate-production-orders`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create production order");
      }

      toast.success("Production order created successfully!");
      fetchProductionOrders();
      fetchOrder();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleCreatePurchaseOrder = async (materialReq) => {
    navigate(
      `/admin/purchasing?material_id=${materialReq.product_id}&qty=${materialReq.net_shortage}`
    );
  };

  const handleCreateWorkOrder = async (materialReq) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/production-orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          product_id: materialReq.product_id,
          quantity_ordered: Math.ceil(materialReq.net_shortage),
          sales_order_id: parseInt(orderId),
          status: "draft",
          notes: `Created from SO ${order.order_number} for sub-assembly`,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create work order");
      }

      toast.success(`Work order created for ${materialReq.product_name}`);
      fetchOrder(); // Refresh to update requirements
      fetchProductionOrders();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Check if order can be cancelled
  const canCancelOrder = () => {
    return order && ["pending", "confirmed", "on_hold"].includes(order.status);
  };

  // Check if order can be deleted
  const canDeleteOrder = () => {
    return order && ["cancelled", "pending"].includes(order.status);
  };

  // Handle cancel order
  const handleCancelOrder = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${orderId}/cancel`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ cancellation_reason: cancellationReason }),
        }
      );

      if (res.ok) {
        toast.success(`Order ${order.order_number} cancelled`);
        setShowCancelModal(false);
        setCancellationReason("");
        fetchOrder();
      } else {
        const errorData = await res.json();
        toast.error(errorData.detail || "Failed to cancel order");
      }
    } catch (err) {
      toast.error(err.message || "Failed to cancel order");
    }
  };

  // Handle delete order
  const handleDeleteOrder = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/sales-orders/${orderId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok || res.status === 204) {
        toast.success(`Order ${order.order_number} deleted`);
        navigate("/admin/orders");
      } else {
        const errorData = await res.json();
        toast.error(errorData.detail || "Failed to delete order");
      }
    } catch (err) {
      toast.error(err.message || "Failed to delete order");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-white">Loading order...</div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-400">Error: {error || "Order not found"}</div>
      </div>
    );
  }

  const totalMaterialCost = materialRequirements.reduce(
    (sum, req) => sum + req.gross_quantity * (req.unit_cost || 0),
    0
  );
  const totalCapacityHours = capacityRequirements.reduce(
    (sum, op) => sum + (op.total_time_minutes || 0) / 60,
    0
  );
  const hasShortages = materialRequirements.some((req) => req.net_shortage > 0);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <button
            onClick={() => navigate("/admin/orders")}
            className="text-gray-400 hover:text-white mb-2"
          >
            ← Back to Orders
          </button>
          <h1 className="text-2xl font-bold text-white">
            Order: {order.order_number}
          </h1>
          <p className="text-gray-400 mt-1">Order Command Center</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
            title="Refresh order data"
          >
            {refreshing ? "Refreshing..." : "↻ Refresh"}
          </button>
          <button
            onClick={handleCreateProductionOrder}
            disabled={
              (!order.product_id &&
                !(order.lines?.length > 0 && order.lines[0].product_id)) ||
              hasMainProductWO()
            }
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {hasMainProductWO() ? "WO Exists" : "Create Work Order"}
          </button>
          {order.status !== "shipped" && order.status !== "delivered" && (
            <button
              onClick={() => navigate(`/admin/shipping?orderId=${order.id}`)}
              disabled={
                productionOrders.length === 0 ||
                !productionOrders.every((po) => po.status === "complete") ||
                materialRequirements.some((req) => req.net_shortage > 0)
              }
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
              title={
                productionOrders.length === 0
                  ? "Create work order first"
                  : !productionOrders.every((po) => po.status === "complete")
                  ? "Production must be complete"
                  : materialRequirements.some((req) => req.net_shortage > 0)
                  ? "Material shortages must be resolved"
                  : "Ship order"
              }
            >
              Ship Order
            </button>
          )}
          {canCancelOrder() && (
            <button
              onClick={() => setShowCancelModal(true)}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg"
            >
              Cancel Order
            </button>
          )}
          {canDeleteOrder() && (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg"
            >
              Delete Order
            </button>
          )}
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Order Summary</h2>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-400">Product</div>
            <div className="text-white font-medium">
              {order.product_name || "N/A"}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Quantity</div>
            <div className="text-white font-medium">{order.quantity}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Status</div>
            <div className="text-white font-medium">{order.status}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Total</div>
            <div className="text-white font-medium">
              ${parseFloat(order.total_price || 0).toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      {/* Shipping Address */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white">Shipping Address</h2>
          {!editingAddress && (
            <button
              onClick={handleEditAddress}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              Edit
            </button>
          )}
        </div>

        {editingAddress ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">
                  Address Line 1
                </label>
                <input
                  type="text"
                  value={addressForm.shipping_address_line1}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_address_line1: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                  placeholder="Street address"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-1">
                  Address Line 2
                </label>
                <input
                  type="text"
                  value={addressForm.shipping_address_line2}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_address_line2: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                  placeholder="Apt, suite, etc."
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">City</label>
                <input
                  type="text"
                  value={addressForm.shipping_city}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_city: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  State
                </label>
                <input
                  type="text"
                  value={addressForm.shipping_state}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_state: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  ZIP Code
                </label>
                <input
                  type="text"
                  value={addressForm.shipping_zip}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_zip: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Country
                </label>
                <input
                  type="text"
                  value={addressForm.shipping_country}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      shipping_country: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingAddress(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAddress}
                disabled={savingAddress}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
              >
                {savingAddress ? "Saving..." : "Save Address"}
              </button>
            </div>
          </div>
        ) : (
          <div>
            {order.shipping_address_line1 ? (
              <div className="text-white">
                <div>{order.shipping_address_line1}</div>
                {order.shipping_address_line2 && (
                  <div>{order.shipping_address_line2}</div>
                )}
                <div>
                  {order.shipping_city}, {order.shipping_state}{" "}
                  {order.shipping_zip}
                </div>
                <div className="text-gray-400">
                  {order.shipping_country || "USA"}
                </div>
              </div>
            ) : (
              <div className="text-yellow-400 flex items-center gap-2">
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
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                No shipping address on file. Click Edit to add one.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Material Requirements */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white">
            Material Requirements
          </h2>
          {exploding && (
            <span className="text-gray-400 text-sm">Calculating...</span>
          )}
        </div>

        {materialRequirements.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {order.product_id || (order.lines && order.lines.length > 0)
              ? "No BOM found for this product. Add a BOM to see material requirements."
              : "No product assigned to this order"}
          </div>
        ) : (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left p-2 text-gray-400">Component</th>
                  <th className="text-right p-2 text-gray-400">Required</th>
                  <th className="text-right p-2 text-gray-400">On Hand</th>
                  <th className="text-right p-2 text-gray-400">Available</th>
                  <th className="text-right p-2 text-gray-400">Shortage</th>
                  <th className="text-right p-2 text-gray-400">Cost</th>
                  <th className="text-center p-2 text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {materialRequirements.map((req, idx) => (
                  <tr
                    key={idx}
                    className={`border-b border-gray-800 ${
                      req.net_shortage > 0 ? "bg-red-900/20" : ""
                    }`}
                  >
                    <td className="p-2 text-white">
                      {req.product_sku} - {req.product_name}
                    </td>
                    <td className="p-2 text-right text-white">
                      {req.gross_quantity?.toFixed(2) || "0.00"}
                    </td>
                    <td className="p-2 text-right text-gray-300">
                      {req.on_hand_quantity?.toFixed(2) || "0.00"}
                    </td>
                    <td className="p-2 text-right text-gray-300">
                      {req.available_quantity?.toFixed(2) || "0.00"}
                    </td>
                    <td className="p-2 text-right">
                      <span
                        className={
                          req.net_shortage > 0
                            ? "text-red-400 font-semibold"
                            : "text-green-400"
                        }
                      >
                        {req.net_shortage?.toFixed(2) || "0.00"}
                      </span>
                    </td>
                    <td className="p-2 text-right text-gray-300">
                      $
                      {(
                        (req.gross_quantity || 0) * (req.unit_cost || 0)
                      ).toFixed(2)}
                    </td>
                    <td className="p-2 text-center">
                      {req.net_shortage > 0 &&
                        (req.has_bom ? (
                          <button
                            onClick={() => handleCreateWorkOrder(req)}
                            className="text-purple-400 hover:text-purple-300 text-sm"
                          >
                            Create WO
                          </button>
                        ) : (
                          <button
                            onClick={() => handleCreatePurchaseOrder(req)}
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            Create PO
                          </button>
                        ))}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-800 font-semibold">
                  <td colSpan="5" className="p-2 text-right text-white">
                    Total Material Cost:
                  </td>
                  <td className="p-2 text-right text-white">
                    ${totalMaterialCost.toFixed(2)}
                  </td>
                  <td className="p-2"></td>
                </tr>
              </tfoot>
            </table>

            {hasShortages && (
              <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-sm">
                  ⚠️ Material shortages detected. Create{" "}
                  <span className="text-purple-400">Work Orders</span> for
                  sub-assemblies or{" "}
                  <span className="text-blue-400">Purchase Orders</span> for raw
                  materials.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Capacity Requirements */}
      {capacityRequirements.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Capacity Requirements
          </h2>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left p-2 text-gray-400">Operation</th>
                <th className="text-left p-2 text-gray-400">Work Center</th>
                <th className="text-right p-2 text-gray-400">Setup (min)</th>
                <th className="text-right p-2 text-gray-400">Run (min)</th>
                <th className="text-right p-2 text-gray-400">Total (hrs)</th>
              </tr>
            </thead>
            <tbody>
              {capacityRequirements.map((op, idx) => (
                <tr key={idx} className="border-b border-gray-800">
                  <td className="p-2 text-white">
                    {op.operation_name || op.operation_code || `OP${idx + 1}`}
                  </td>
                  <td className="p-2 text-gray-300">{op.work_center_name}</td>
                  <td className="p-2 text-right text-gray-300">
                    {op.setup_time_minutes?.toFixed(1) || "0.0"}
                  </td>
                  <td className="p-2 text-right text-gray-300">
                    {((op.run_time_minutes || 0) * order.quantity).toFixed(1)}
                  </td>
                  <td className="p-2 text-right text-white">
                    {(op.total_time_minutes / 60).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-gray-800 font-semibold">
                <td colSpan="4" className="p-2 text-right text-white">
                  Total Time:
                </td>
                <td className="p-2 text-right text-white">
                  {totalCapacityHours.toFixed(2)} hrs
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Production Orders */}
      {productionOrders.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Work Orders</h2>
          <div className="space-y-2">
            {productionOrders.map((po) => (
              <div
                key={po.id}
                className="flex justify-between items-center p-3 bg-gray-800 rounded-lg"
              >
                <div>
                  <div className="text-white font-medium">
                    {po.code || `WO-${po.id}`}
                  </div>
                  <div className="text-sm text-gray-400">
                    Status: {po.status} | Qty: {po.quantity_ordered}
                  </div>
                </div>
                <button
                  onClick={() =>
                    navigate(
                      `/admin/production?search=${encodeURIComponent(
                        po.code || `WO-${po.id}`
                      )}`
                    )
                  }
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  View →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Payments Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white">Payments</h2>
          <div className="flex gap-2">
            {paymentSummary && paymentSummary.total_paid > 0 && (
              <button
                onClick={() => {
                  setIsRefund(true);
                  setShowPaymentModal(true);
                }}
                className="px-3 py-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded text-sm"
              >
                Refund
              </button>
            )}
            <button
              onClick={() => {
                setIsRefund(false);
                setShowPaymentModal(true);
              }}
              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm flex items-center gap-1"
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
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
              Record Payment
            </button>
          </div>
        </div>

        {/* Payment Summary */}
        {paymentSummary && (
          <div className="grid grid-cols-4 gap-4 mb-4 p-4 bg-gray-800/50 rounded-lg">
            <div>
              <div className="text-sm text-gray-400">Order Total</div>
              <div className="text-white font-medium">
                ${parseFloat(paymentSummary.order_total || 0).toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Paid</div>
              <div className="text-green-400 font-medium">
                ${parseFloat(paymentSummary.total_paid || 0).toFixed(2)}
              </div>
            </div>
            {paymentSummary.total_refunded > 0 && (
              <div>
                <div className="text-sm text-gray-400">Refunded</div>
                <div className="text-red-400 font-medium">
                  ${parseFloat(paymentSummary.total_refunded || 0).toFixed(2)}
                </div>
              </div>
            )}
            <div>
              <div className="text-sm text-gray-400">Balance Due</div>
              <div
                className={`font-medium ${
                  paymentSummary.balance_due > 0
                    ? "text-yellow-400"
                    : "text-green-400"
                }`}
              >
                ${parseFloat(paymentSummary.balance_due || 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Payment History */}
        {payments.length > 0 ? (
          <div className="space-y-2">
            {payments.map((payment) => (
              <div
                key={payment.id}
                className="flex justify-between items-center p-3 bg-gray-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      payment.amount < 0 ? "bg-red-500/20" : "bg-green-500/20"
                    }`}
                  >
                    {payment.amount < 0 ? (
                      <svg
                        className="w-4 h-4 text-red-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
                        />
                      </svg>
                    ) : (
                      <svg
                        className="w-4 h-4 text-green-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                        />
                      </svg>
                    )}
                  </div>
                  <div>
                    <div className="text-white font-medium">
                      {payment.payment_number}
                    </div>
                    <div className="text-sm text-gray-400">
                      {payment.payment_method}
                      {payment.check_number && ` #${payment.check_number}`}
                      {payment.transaction_id && ` - ${payment.transaction_id}`}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`font-medium ${
                      payment.amount < 0 ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    ${Math.abs(parseFloat(payment.amount)).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(payment.payment_date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-500">
            No payments recorded yet
          </div>
        )}
      </div>

      {/* Activity Timeline */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Activity</h2>
        <ActivityTimeline orderId={parseInt(orderId)} />
      </div>

      {/* Record Payment Modal */}
      {showPaymentModal && (
        <RecordPaymentModal
          orderId={parseInt(orderId)}
          isRefund={isRefund}
          onClose={() => {
            setShowPaymentModal(false);
            setIsRefund(false);
          }}
          onSuccess={handlePaymentRecorded}
        />
      )}

      {/* Cancel Order Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/70"
              onClick={() => {
                setShowCancelModal(false);
                setCancellationReason("");
              }}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-md w-full mx-auto p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Cancel Order {order.order_number}?
              </h3>
              <p className="text-gray-400 mb-4">
                This will cancel the order. The order can still be deleted after
                cancellation.
              </p>
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-2">
                  Cancellation Reason (optional)
                </label>
                <textarea
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                  rows={3}
                  placeholder="Enter reason for cancellation..."
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowCancelModal(false);
                    setCancellationReason("");
                  }}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Keep Order
                </button>
                <button
                  onClick={handleCancelOrder}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-500"
                >
                  Cancel Order
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Order Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/70"
              onClick={() => setShowDeleteConfirm(false)}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-md w-full mx-auto p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Delete Order {order.order_number}?
              </h3>
              <p className="text-gray-400 mb-4">
                This action cannot be undone. All order data, including line
                items and payment records, will be permanently deleted.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Keep Order
                </button>
                <button
                  onClick={handleDeleteOrder}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500"
                >
                  Delete Permanently
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
