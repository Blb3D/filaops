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
import ShippingTimeline from "../../components/ShippingTimeline";

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

  // Collapsible sections state
  const [expandedSections, setExpandedSections] = useState({
    materialRequirements: true,
    capacityRequirements: true,
    productionOrders: true,
    payments: true,
  });

  // Material availability check state
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [materialAvailability, setMaterialAvailability] = useState(null);

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
        } catch {
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
    } catch {
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
    } catch {
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
    } catch {
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
      } catch {
        // Routing is optional - don't fail
      }
    } catch {
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
        let errorMsg = "Failed to delete order";
        const contentType = res.headers.get("content-type") || "";
        const text = await res.text();
        if (text && contentType.includes("application/json")) {
          try {
            const errorData = JSON.parse(text);
            errorMsg = errorData.detail || errorMsg;
          } catch {
            // Ignore JSON parse error, fallback to generic message
          }
        }
        toast.error(errorMsg);
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

  const handleCheckAvailability = async () => {
    if (!order.product_id && !(order.lines?.length > 0 && order.lines[0].product_id)) {
      toast.error("Order must have a product to check availability");
      return;
    }

    setCheckingAvailability(true);
    try {
      // Check availability for production orders if they exist
      if (productionOrders.length > 0) {
        const availabilityChecks = await Promise.all(
          productionOrders.map(async (po) => {
            const res = await fetch(
              `${API_URL}/api/v1/production-orders/${po.id}/material-availability`,
              {
                headers: { Authorization: `Bearer ${token}` },
              }
            );
            if (res.ok) {
              return await res.json();
            }
            return null;
          })
        );
        setMaterialAvailability(availabilityChecks.filter(Boolean));
      } else {
        toast.info("Create a production order first to check material availability");
      }
    } catch {
      toast.error("Failed to check availability");
    } finally {
      setCheckingAvailability(false);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

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
        </div>
      </div>

      {/* Quick Actions Panel */}
      <div className="bg-gradient-to-r from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={handleCreateProductionOrder}
            disabled={
              (!order.product_id &&
                !(order.lines?.length > 0 && order.lines[0].product_id)) ||
              hasMainProductWO()
            }
            className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            {hasMainProductWO() ? "WO Exists" : "Generate Production Order"}
          </button>
          <button
            onClick={handleCheckAvailability}
            disabled={checkingAvailability || productionOrders.length === 0}
            className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {checkingAvailability ? "Checking..." : "Check Material Availability"}
          </button>
          {productionOrders.length > 0 && (
            <button
              onClick={() => navigate(`/admin/production?order=${productionOrders[0].id}`)}
              className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center justify-center gap-2 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View in Production
            </button>
          )}
        </div>
        {materialAvailability && materialAvailability.length > 0 && (
          <div className="mt-4 space-y-2">
            {materialAvailability.map((avail, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg ${
                  avail.can_release
                    ? "bg-green-900/20 border border-green-500/30"
                    : "bg-red-900/20 border border-red-500/30"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium">{avail.order_code}</span>
                  <span className={`text-sm ${avail.can_release ? "text-green-400" : "text-red-400"}`}>
                    {avail.can_release ? "✓ Materials Available" : `⚠ ${avail.shortage_count} Shortage${avail.shortage_count !== 1 ? "s" : ""}`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
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

      {/* Customer Information */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Customer</h2>
        {order.customer_name || order.customer_email ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-400">Name</div>
              <div className="text-white font-medium">
                {order.customer_name || "—"}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Email</div>
              <div className="text-white font-medium">
                {order.customer_email ? (
                  <a href={`mailto:${order.customer_email}`} className="text-blue-400 hover:underline">
                    {order.customer_email}
                  </a>
                ) : "—"}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Phone</div>
              <div className="text-white font-medium">
                {order.customer_phone || "—"}
              </div>
            </div>
            {order.customer_id && (
              <div>
                <div className="text-sm text-gray-400">Customer ID</div>
                <div className="text-white font-medium">
                  <button 
                    onClick={() => navigate(`/admin/customers/${order.customer_id}`)}
                    className="text-blue-400 hover:underline"
                  >
                    #{order.customer_id}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : order.quote_id ? (
          <div className="text-gray-400">
            Customer info available in linked quote.
            <button 
              onClick={() => navigate(`/admin/quotes`)} 
              className="text-blue-400 hover:underline ml-2"
            >
              View Quote
            </button>
          </div>
        ) : (
          <div className="text-gray-400">No customer information on file.</div>
        )}
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
          <button
            onClick={() => toggleSection("materialRequirements")}
            className="flex items-center gap-2 text-lg font-semibold text-white hover:text-gray-300"
          >
            <svg
              className={`w-5 h-5 transition-transform ${expandedSections.materialRequirements ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Material Requirements
            {hasShortages && (
              <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full">
                {materialRequirements.filter((r) => r.net_shortage > 0).length} Shortage{materialRequirements.filter((r) => r.net_shortage > 0).length !== 1 ? "s" : ""}
              </span>
            )}
          </button>
          {exploding && (
            <span className="text-gray-400 text-sm">Calculating...</span>
          )}
        </div>
        {expandedSections.materialRequirements && (
          <>
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
        </>
        )}
      </div>

      {/* Capacity Requirements */}
      {capacityRequirements.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <button
            onClick={() => toggleSection("capacityRequirements")}
            className="flex items-center gap-2 text-lg font-semibold text-white hover:text-gray-300 mb-4"
          >
            <svg
              className={`w-5 h-5 transition-transform ${expandedSections.capacityRequirements ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Capacity Requirements
          </button>
          {expandedSections.capacityRequirements && (
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
          )}
        </div>
      )}

      {/* Production Orders - Read-Only Status Display */}
      {productionOrders.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <button
            onClick={() => toggleSection("productionOrders")}
            className="flex items-center gap-2 text-lg font-semibold text-white hover:text-gray-300 mb-4"
          >
            <svg
              className={`w-5 h-5 transition-transform ${expandedSections.productionOrders ? "rotate-90" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            Production Status ({productionOrders.length})
          </button>
          {expandedSections.productionOrders && (
          <div className="space-y-3">
            {/* Overall Production Progress */}
            <ProductionProgressSummary orders={productionOrders} />
            
            {/* Individual Work Orders */}
            {productionOrders.map((po) => (
              <ProductionOrderStatusCard
                key={po.id}
                order={po}
                onViewInProduction={() =>
                  navigate(`/admin/production?search=${encodeURIComponent(po.code || `WO-${po.id}`)}`)
                }
              />
            ))}
          </div>
          )}
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

      {/* Shipping Timeline - Show if order has been shipped */}
      {order?.tracking_number && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
            </svg>
            <h2 className="text-lg font-semibold text-white">Shipping Tracking</h2>
          </div>
          <ShippingTimeline orderId={parseInt(orderId)} />
        </div>
      )}

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

/**
 * Production Progress Summary - Shows overall progress across all WOs
 */
function ProductionProgressSummary({ orders }) {
  const completed = orders.filter(o => o.status === "complete").length;
  const inProgress = orders.filter(o => o.status === "in_progress").length;
  const scrapped = orders.filter(o => o.status === "scrapped").length;
  const total = orders.length;
  const completionPercent = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mb-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">Overall Progress</span>
        <span className="text-sm text-white font-medium">{completed}/{total} Complete</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
        <div
          className="bg-green-500 h-2 rounded-full transition-all"
          style={{ width: `${completionPercent}%` }}
        />
      </div>
      <div className="flex gap-4 text-xs">
        {inProgress > 0 && (
          <span className="text-purple-400">{inProgress} In Progress</span>
        )}
        {completed > 0 && (
          <span className="text-green-400">{completed} Complete</span>
        )}
        {scrapped > 0 && (
          <span className="text-red-400">{scrapped} Scrapped</span>
        )}
      </div>
    </div>
  );
}

/**
 * Production Order Status Card - Read-only display of WO status
 */
function ProductionOrderStatusCard({ order, onViewInProduction }) {
  const statusConfig = {
    draft: { color: "bg-gray-500", text: "Draft" },
    released: { color: "bg-blue-500", text: "Released" },
    in_progress: { color: "bg-purple-500", text: "In Progress" },
    complete: { color: "bg-green-500", text: "Complete" },
    scrapped: { color: "bg-red-500", text: "Scrapped" },
    closed: { color: "bg-gray-400", text: "Closed" },
  };
  
  const status = statusConfig[order.status] || { color: "bg-gray-500", text: order.status };
  const progressPercent = order.quantity_ordered > 0
    ? ((order.quantity_completed || 0) / order.quantity_ordered) * 100
    : 0;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-white font-medium">{order.code || `WO-${order.id}`}</span>
            <span className={`px-2 py-0.5 ${status.color} text-white text-xs rounded-full`}>
              {status.text}
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            {order.product_name || order.product_sku || "N/A"}
          </p>
        </div>
        <button
          onClick={onViewInProduction}
          className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          View
        </button>
      </div>
      
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-700 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all ${
              order.status === "complete" ? "bg-green-500" :
              order.status === "scrapped" ? "bg-red-500" : "bg-blue-500"
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="text-xs text-gray-400 w-20 text-right">
          {order.quantity_completed || 0} / {order.quantity_ordered}
        </span>
      </div>
      
      {/* Operations summary if available */}
      {order.operations && order.operations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-700">
          <div className="text-xs text-gray-500 mb-2">Operations:</div>
          <div className="flex flex-wrap gap-1">
            {order.operations.slice(0, 5).map((op, idx) => (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded text-xs ${
                  op.status === "complete" ? "bg-green-500/20 text-green-400" :
                  op.status === "running" ? "bg-purple-500/20 text-purple-400" :
                  op.status === "queued" ? "bg-blue-500/20 text-blue-400" :
                  "bg-gray-500/20 text-gray-400"
                }`}
              >
                {op.sequence}. {op.operation_name || op.operation_code || "Op"}
              </span>
            ))}
            {order.operations.length > 5 && (
              <span className="text-xs text-gray-500">+{order.operations.length - 5} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
