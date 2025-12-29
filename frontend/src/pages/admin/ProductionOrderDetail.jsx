/**
 * ProductionOrderDetail - Production Order Command Center
 *
 * Detailed view for managing a single production order:
 * - Order status and progress
 * - Material requirements and availability
 * - Blocking issues analysis
 * - Action buttons (Release, Start, Complete, etc.)
 */
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";
import BlockingIssuesPanel from "../../components/orders/BlockingIssuesPanel";

export default function ProductionOrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const token = localStorage.getItem("adminToken");

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (orderId) {
      fetchOrder();
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

    try {
      const res = await fetch(`${API_URL}/api/v1/production-orders/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error(`Failed to fetch production order: ${res.statusText}`);
      }

      const data = await res.json();
      setOrder(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (action) => {
    setUpdating(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${orderId}/${action}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Failed to ${action} order`);
      }

      toast.success(`Order ${action} successfully`);
      fetchOrder();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: "bg-gray-500/20 text-gray-400",
      released: "bg-blue-500/20 text-blue-400",
      in_progress: "bg-purple-500/20 text-purple-400",
      complete: "bg-green-500/20 text-green-400",
      scrapped: "bg-red-500/20 text-red-400",
      on_hold: "bg-yellow-500/20 text-yellow-400",
      cancelled: "bg-gray-500/20 text-gray-400",
    };
    return colors[status] || "bg-gray-500/20 text-gray-400";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => navigate("/admin/production")}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Back to Production
          </button>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="p-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
          <p className="text-gray-400 mb-4">Production order not found</p>
          <button
            onClick={() => navigate("/admin/production")}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Back to Production
          </button>
        </div>
      </div>
    );
  }

  const progress = order.quantity_ordered > 0
    ? Math.round((order.quantity_completed / order.quantity_ordered) * 100)
    : 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <button
            onClick={() => navigate("/admin/production")}
            className="text-gray-400 hover:text-white mb-2"
          >
            ← Back to Production
          </button>
          <h1 className="text-2xl font-bold text-white">
            Production Order: {order.code}
          </h1>
          <p className="text-gray-400 mt-1">Production Command Center</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchOrder}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            ↻ Refresh
          </button>
          {order.status === "draft" && (
            <button
              onClick={() => handleStatusUpdate("release")}
              disabled={updating}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Release
            </button>
          )}
          {order.status === "released" && (
            <button
              onClick={() => handleStatusUpdate("start")}
              disabled={updating}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              Start Production
            </button>
          )}
          {order.status === "in_progress" && (
            <button
              onClick={() => handleStatusUpdate("complete")}
              disabled={updating}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              Complete
            </button>
          )}
        </div>
      </div>

      {/* Order Summary */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Order Summary</h2>
        <div className="grid grid-cols-5 gap-4">
          <div>
            <div className="text-sm text-gray-400">Product</div>
            <div className="text-white font-medium">{order.product_name || order.product_sku || "N/A"}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Quantity</div>
            <div className="text-white font-medium">
              {order.quantity_completed || 0} / {order.quantity_ordered}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Status</div>
            <span className={`inline-block px-2 py-1 rounded-full text-sm ${getStatusColor(order.status)}`}>
              {order.status}
            </span>
          </div>
          <div>
            <div className="text-sm text-gray-400">Priority</div>
            <div className="text-white font-medium">{order.priority || "Normal"}</div>
          </div>
          <div>
            <div className="text-sm text-gray-400">Due Date</div>
            <div className="text-white font-medium">
              {order.due_date ? new Date(order.due_date).toLocaleDateString() : "Not set"}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Progress</span>
            <span className="text-white">{progress}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Blocking Issues Panel */}
      <BlockingIssuesPanel
        orderType="production"
        orderId={order.id}
        onActionClick={(action) => console.log('Blocking issue action:', action)}
      />

      {/* Linked Sales Order */}
      {order.sales_order_id && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Linked Sales Order</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white font-medium">{order.sales_order_code || `SO-${order.sales_order_id}`}</p>
              <p className="text-gray-400 text-sm">{order.customer_name || "Customer"}</p>
            </div>
            <button
              onClick={() => navigate(`/admin/orders/${order.sales_order_id}`)}
              className="px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30"
            >
              View Sales Order
            </button>
          </div>
        </div>
      )}

      {/* Notes */}
      {order.notes && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Notes</h2>
          <p className="text-gray-300">{order.notes}</p>
        </div>
      )}
    </div>
  );
}
