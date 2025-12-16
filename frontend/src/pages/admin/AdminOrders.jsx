import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import SalesOrderWizard from "../../components/SalesOrderWizard";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

const statusColors = {
  pending: "bg-yellow-500/20 text-yellow-400",
  confirmed: "bg-blue-500/20 text-blue-400",
  in_production: "bg-purple-500/20 text-purple-400",
  ready_to_ship: "bg-cyan-500/20 text-cyan-400",
  shipped: "bg-green-500/20 text-green-400",
  completed: "bg-green-500/20 text-green-400",
  cancelled: "bg-red-500/20 text-red-400",
};

const paymentColors = {
  pending: "bg-yellow-500/20 text-yellow-400",
  paid: "bg-green-500/20 text-green-400",
  failed: "bg-red-500/20 text-red-400",
  refunded: "bg-gray-500/20 text-gray-400",
};

export default function AdminOrders() {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: "all",
    search: "",
  });
  const [selectedOrder, setSelectedOrder] = useState(null);

  // Create order modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [generatingPO, setGeneratingPO] = useState(false);

  // Cancel/Delete modal state
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancellingOrder, setCancellingOrder] = useState(null);
  const [cancellationReason, setCancellationReason] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletingOrder, setDeletingOrder] = useState(null);

  const token = localStorage.getItem("adminToken");

  // Check if returning from customer/item creation
  useEffect(() => {
    const pendingData = sessionStorage.getItem("pendingOrderData");
    if (pendingData) {
      // Open the order modal if we have pending data
      setShowCreateModal(true);
    }
  }, []);

  // Fetch orders on mount, when filters change, or when navigating back to this page
  useEffect(() => {
    fetchOrders();
  }, [filters.status, location.key]);

  const fetchOrders = async () => {
    if (!token) return;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.status !== "all") params.set("status", filters.status);
      params.set("limit", "100");

      const res = await fetch(`${API_URL}/api/v1/sales-orders/?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to fetch orders");

      const data = await res.json();
      setOrders(data.items || data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${orderId}/status`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (res.ok) {
        toast.success("Order status updated");
        fetchOrders();
        if (selectedOrder?.id === orderId) {
          const updated = await res.json();
          setSelectedOrder(updated);
        }
      } else {
        const errorData = await res.json();
        toast.error(`Failed to update order status: ${errorData.detail || "Unknown error"}`);
      }
    } catch (err) {
      toast.error(`Failed to update order status: ${err.message || "Network error"}`);
    }
  };

  const handleGenerateProductionOrder = async (orderId) => {
    setGeneratingPO(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${orderId}/generate-production-orders`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      const data = await res.json();

      if (res.ok) {
        if (data.created_orders?.length > 0) {
          toast.success(`Production Order(s) created: ${data.created_orders.join(", ")}`);
        } else if (data.existing_orders?.length > 0) {
          toast.info(`Production Order(s) already exist: ${data.existing_orders.join(", ")}`);
        }
        fetchOrders();
        setSelectedOrder(null);
      } else {
        setError(data.detail || "Failed to generate production order");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGeneratingPO(false);
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      o.order_number?.toLowerCase().includes(search) ||
      o.product_name?.toLowerCase().includes(search) ||
      o.user?.email?.toLowerCase().includes(search)
    );
  });

  const getNextStatus = (currentStatus) => {
    const flow = {
      pending: "confirmed",
      confirmed: "in_production",
      in_production: "ready_to_ship",
      ready_to_ship: "shipped",
      shipped: "completed",
    };
    return flow[currentStatus];
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: "Pending",
      confirmed: "Confirmed",
      in_production: "In Production",
      ready_to_ship: "Ready to Ship",
      shipped: "Shipped",
      completed: "Completed",
      cancelled: "Cancelled",
    };
    return labels[status] || status?.replace(/_/g, " ");
  };

  // Check if order can be cancelled
  const canCancelOrder = (order) => {
    return ["pending", "confirmed", "on_hold"].includes(order.status);
  };

  // Check if order can be deleted
  const canDeleteOrder = (order) => {
    return ["cancelled", "pending"].includes(order.status);
  };

  // Handle cancel order
  const handleCancelOrder = async () => {
    if (!cancellingOrder) return;

    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${cancellingOrder.id}/cancel`,
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
        toast.success(`Order ${cancellingOrder.order_number} cancelled`);
        setShowCancelModal(false);
        setCancellingOrder(null);
        setCancellationReason("");
        fetchOrders();
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
    if (!deletingOrder) return;

    try {
      const res = await fetch(
        `${API_URL}/api/v1/sales-orders/${deletingOrder.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (res.ok || res.status === 204) {
        toast.success(`Order ${deletingOrder.order_number} deleted`);
        setShowDeleteConfirm(false);
        setDeletingOrder(null);
        fetchOrders();
      } else {
        const errorData = await res.json();
        toast.error(errorData.detail || "Failed to delete order");
      }
    } catch (err) {
      toast.error(err.message || "Failed to delete order");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Order Management</h1>
          <p className="text-gray-400 mt-1">View and manage sales orders</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchOrders}
            disabled={loading}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
            title="Refresh orders"
          >
            {loading ? "Loading..." : "↻ Refresh"}
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500 flex items-center gap-2"
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          Create Order
        </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by order number, product, or customer..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500"
          />
        </div>
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="in_production">In Production</option>
          <option value="ready_to_ship">Ready to Ship</option>
          <option value="shipped">Shipped</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-4 text-red-300 hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* Orders Table */}
      {!loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Order #
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Customer
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Product
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Qty
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Total
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Payment
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Created
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((order) => (
                <tr
                  key={order.id}
                  className="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td className="py-3 px-4 text-white font-medium">
                    {order.order_number}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {order.user?.email || "N/A"}
                  </td>
                  <td className="py-3 px-4 text-gray-300">
                    {order.product_name}
                  </td>
                  <td className="py-3 px-4 text-gray-400">{order.quantity}</td>
                  <td className="py-3 px-4 text-green-400 font-medium">
                    $
                    {parseFloat(
                      order.grand_total || order.total_price || 0
                    ).toFixed(2)}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        statusColors[order.status] ||
                        "bg-gray-500/20 text-gray-400"
                      }`}
                    >
                      {order.status?.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        paymentColors[order.payment_status] ||
                        "bg-gray-500/20 text-gray-400"
                      }`}
                    >
                      {order.payment_status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-500 text-sm">
                    {new Date(order.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={() => navigate(`/admin/orders/${order.id}`)}
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      View
                    </button>
                    {getNextStatus(order.status) && (
                      <button
                        onClick={() =>
                          handleStatusUpdate(
                            order.id,
                            getNextStatus(order.status)
                          )
                        }
                        className="text-green-400 hover:text-green-300 text-sm"
                        title={`Advance to: ${getStatusLabel(getNextStatus(order.status))}`}
                      >
                        → {getStatusLabel(getNextStatus(order.status))}
                      </button>
                    )}
                    {canCancelOrder(order) && (
                      <button
                        onClick={() => {
                          setCancellingOrder(order);
                          setShowCancelModal(true);
                        }}
                        className="text-yellow-400 hover:text-yellow-300 text-sm"
                        title="Cancel order"
                      >
                        Cancel
                      </button>
                    )}
                    {canDeleteOrder(order) && (
                      <button
                        onClick={() => {
                          setDeletingOrder(order);
                          setShowDeleteConfirm(true);
                        }}
                        className="text-red-400 hover:text-red-300 text-sm"
                        title="Delete order"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filteredOrders.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-gray-500">
                    No orders found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Order Wizard */}
      <SalesOrderWizard
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={() => {
          setShowCreateModal(false);
          fetchOrders();
        }}
      />

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/70"
              onClick={() => setSelectedOrder(null)}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-2xl w-full mx-auto p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-white">
                  Order: {selectedOrder.order_number}
                </h3>
                <button
                  onClick={() => setSelectedOrder(null)}
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

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Product:</span>
                    <p className="text-white">{selectedOrder.product_name}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Material:</span>
                    <p className="text-white">
                      {selectedOrder.material_type} /{" "}
                      {selectedOrder.color || "N/A"}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Quantity:</span>
                    <p className="text-white">{selectedOrder.quantity}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Unit Price:</span>
                    <p className="text-white">
                      ${parseFloat(selectedOrder.unit_price || 0).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Grand Total:</span>
                    <p className="text-green-400 font-semibold">
                      ${parseFloat(selectedOrder.grand_total || 0).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Source:</span>
                    <p className="text-white">
                      {selectedOrder.source} ({selectedOrder.order_type})
                    </p>
                  </div>
                </div>

                {/* Shipping Info */}
                {selectedOrder.shipping_address && (
                  <div className="bg-gray-800 p-4 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-300 mb-2">
                      Shipping Address
                    </h4>
                    <p className="text-white text-sm whitespace-pre-line">
                      {selectedOrder.shipping_address}
                    </p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col gap-4 pt-4 border-t border-gray-800">
                  {/* Generate Production Order Button */}
                  {selectedOrder.status !== "cancelled" &&
                    selectedOrder.status !== "completed" && (
                      <button
                        onClick={() =>
                          handleGenerateProductionOrder(selectedOrder.id)
                        }
                        disabled={generatingPO}
                        className="w-full px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 flex items-center justify-center gap-2"
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
                            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                          />
                        </svg>
                        {generatingPO
                          ? "Generating..."
                          : "Generate Production Order"}
                      </button>
                    )}

                  {/* Status Flow */}
                  <div className="flex gap-2 flex-wrap">
                    {[
                      "confirmed",
                      "in_production",
                      "ready_to_ship",
                      "shipped",
                      "completed",
                    ].map((status) => (
                      <button
                        key={status}
                        onClick={() =>
                          handleStatusUpdate(selectedOrder.id, status)
                        }
                        disabled={selectedOrder.status === status}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                          selectedOrder.status === status
                            ? "bg-blue-600 text-white"
                            : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
                        }`}
                      >
                        {status.replace(/_/g, " ")}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Order Modal */}
      {showCancelModal && cancellingOrder && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/70"
              onClick={() => {
                setShowCancelModal(false);
                setCancellingOrder(null);
                setCancellationReason("");
              }}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-md w-full mx-auto p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Cancel Order {cancellingOrder.order_number}?
              </h3>
              <p className="text-gray-400 mb-4">
                This will cancel the order. The order can still be deleted after cancellation.
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
                    setCancellingOrder(null);
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
      {showDeleteConfirm && deletingOrder && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
            <div
              className="fixed inset-0 bg-black/70"
              onClick={() => {
                setShowDeleteConfirm(false);
                setDeletingOrder(null);
              }}
            />
            <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-md w-full mx-auto p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Delete Order {deletingOrder.order_number}?
              </h3>
              <p className="text-gray-400 mb-4">
                This action cannot be undone. All order data, including line items and payment records, will be permanently deleted.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeletingOrder(null);
                  }}
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
