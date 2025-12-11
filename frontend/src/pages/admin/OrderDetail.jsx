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

/**
 * Render the admin Order detail page and manage its data, interactions, and UI state.
 *
 * Fetches and displays a sales order and its related material and capacity requirements,
 * retrieves associated production orders, supports generating production orders,
 * and navigates to purchasing or production views for creating purchase or work orders.
 *
 * @returns {JSX.Element} The rendered Order detail page UI.
 */
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
  const [error, setError] = useState(null);
  const [exploding, setExploding] = useState(false);

  useEffect(() => {
    if (orderId) {
      fetchOrder();
      fetchProductionOrders();
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
        const firstLine = data.lines[0];
        if (firstLine.product_id) {
          await explodeBOM(firstLine.product_id, firstLine.quantity);
        }
      } else if (data.quote_id) {
        // Quote-based order - fetch quote to get product_id
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
      } else if (data.product_id) {
        await explodeBOM(data.product_id, data.quantity);
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
            const capacity = routing.operations.map((op) => ({
              ...op,
              setup_time_minutes: op.setup_time_minutes || 0,
              run_time_minutes: op.run_time_minutes || 0,
              total_time_minutes:
                (op.setup_time_minutes || 0) +
                (op.run_time_minutes || 0) * quantity,
              work_center_name:
                op.work_center?.name || op.work_center_name || "N/A",
              operation_name:
                op.operation_name || op.operation_code || "Operation",
            }));
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
            onClick={handleCreateProductionOrder}
            disabled={!order.product_id || productionOrders.length > 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {productionOrders.length > 0 ? "WO Exists" : "Create Work Order"}
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
                      {req.net_shortage > 0 && (
                        <button
                          onClick={() => handleCreatePurchaseOrder(req)}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Create PO
                        </button>
                      )}
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
                  ⚠️ Material shortages detected. Create purchase orders for
                  missing materials.
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
                  onClick={() => navigate(`/admin/production/${po.id}`)}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  View →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}