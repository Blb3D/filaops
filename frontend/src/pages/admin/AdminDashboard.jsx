import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { API_URL } from "../../config/api";
import StatCard from "../../components/StatCard";

// Recent Order Row
function RecentOrderRow({ order }) {
  const statusColors = {
    pending: "bg-yellow-500/20 text-yellow-400",
    confirmed: "bg-blue-500/20 text-blue-400",
    in_production: "bg-purple-500/20 text-purple-400",
    ready_to_ship: "bg-cyan-500/20 text-cyan-400",
    shipped: "bg-green-500/20 text-green-400",
    completed: "bg-green-500/20 text-green-400",
    cancelled: "bg-red-500/20 text-red-400",
  };

  return (
    <tr className="border-b border-gray-800 hover:bg-gray-900/50">
      <td className="py-3 px-4 text-white font-medium">{order.order_number}</td>
      <td className="py-3 px-4 text-gray-400">
        {order.product_name || order.customer_name}
      </td>
      <td className="py-3 px-4">
        <span
          className={`px-2 py-1 rounded-full text-xs ${
            statusColors[order.status] || "bg-gray-500/20 text-gray-400"
          }`}
        >
          {order.status?.replace(/_/g, " ")}
        </span>
      </td>
      <td className="py-3 px-4 text-gray-400">
        ${parseFloat(order.grand_total || order.total_price || 0).toFixed(2)}
      </td>
    </tr>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [recentOrders, setRecentOrders] = useState([]);
  const [pendingBOMs, setPendingBOMs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Format revenue with smart display (show actual $ under 1k, otherwise Xk)
  const formatRevenue = (amount) => {
    if (amount < 1000) {
      return `$${amount.toFixed(0)}`;
    }
    return `$${(amount / 1000).toFixed(1)}k`;
  };

  const fetchDashboardData = async () => {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      setError("Authentication required");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      // Fetch summary stats
      const summaryRes = await fetch(
        `${API_URL}/api/v1/admin/dashboard/summary`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!summaryRes.ok) throw new Error("Failed to fetch dashboard summary");
      const summaryData = await summaryRes.json();
      setStats(summaryData);

      // Fetch recent orders
      const ordersRes = await fetch(
        `${API_URL}/api/v1/admin/dashboard/recent-orders?limit=5`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (ordersRes.ok) {
        const ordersData = await ordersRes.json();
        setRecentOrders(ordersData);
      }

      // Fetch pending BOMs
      const bomsRes = await fetch(
        `${API_URL}/api/v1/admin/dashboard/pending-bom-reviews?limit=5`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (bomsRes.ok) {
        const bomsData = await bomsRes.json();
        setPendingBOMs(bomsData);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-red-400 flex flex-col">
        <h3 className="font-semibold mb-2">Error loading dashboard</h3>
        <p className="text-sm">{error}</p>
        <button
          onClick={fetchDashboardData}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Welcome to the FilaOps Admin Panel</p>
      </div>

      {/* Alerts Section */}
      {(stats?.orders?.overdue > 0 ||
        stats?.inventory?.low_stock_count > 0 ||
        stats?.production?.ready_to_start > 0) && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <svg
              className="w-5 h-5 text-yellow-400"
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
            <h3 className="font-semibold text-yellow-400">Action Required</h3>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            {stats?.orders?.overdue > 0 && (
              <Link
                to="/admin/orders?status=overdue"
                className="text-yellow-300 hover:text-yellow-200"
              >
                {stats.orders.overdue} Overdue Order
                {stats.orders.overdue !== 1 ? "s" : ""} →
              </Link>
            )}
            {stats?.inventory?.low_stock_count > 0 && (
              <Link
                to="/admin/purchasing?tab=lowstock"
                className="text-yellow-300 hover:text-yellow-200"
              >
                {stats.inventory.low_stock_count} Low Stock Item
                {stats.inventory.low_stock_count !== 1 ? "s" : ""} →
              </Link>
            )}
            {stats?.production?.ready_to_start > 0 && (
              <Link
                to="/admin/production?status=released&materials_available=true"
                className="text-green-300 hover:text-green-200"
              >
                {stats.production.ready_to_start} Production Order
                {stats.production.ready_to_start !== 1 ? "s" : ""} Ready to Start →
              </Link>
            )}
          </div>
        </div>
      )}

      {/* SALES Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Sales
          </h2>
          <div className="flex-1 h-px bg-gray-800"></div>
          <Link
            to="/admin/orders"
            className="text-xs text-blue-400 hover:text-blue-300"
            aria-label="View all Sales"
          >
            View all →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Pending Quotes"
            value={stats?.quotes?.pending || 0}
            subtitle="Awaiting review"
            color="warning"
            to="/admin/quotes"
          />
          <StatCard
            title="Orders in Progress"
            value={
              (stats?.orders?.confirmed || 0) +
              (stats?.orders?.in_production || 0)
            }
            subtitle={`${stats?.orders?.confirmed || 0} confirmed, ${
              stats?.orders?.in_production || 0
            } in production`}
            color="primary"
            to="/admin/orders"
          />
          <StatCard
            title="Ready to Ship"
            value={stats?.orders?.ready_to_ship || 0}
            subtitle={`${stats?.orders?.overdue || 0} overdue`}
            color={stats?.orders?.overdue > 0 ? "danger" : "success"}
            to="/admin/shipping"
          />
          <StatCard
            title="Revenue (30 Days)"
            value={formatRevenue(stats?.revenue?.last_30_days || 0)}
            subtitle={`${stats?.revenue?.orders_last_30_days || 0} orders`}
            color="success"
            to="/admin/payments"
          />
        </div>
      </div>

      {/* INVENTORY Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Inventory
          </h2>
          <div className="flex-1 h-px bg-gray-800"></div>
          <Link
            to="/admin/items"
            className="text-xs text-blue-400 hover:text-blue-300"
            aria-label="View all Inventory"
          >
            View all →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="Low Stock Items"
            value={stats?.inventory?.low_stock_count || 0}
            subtitle="Below reorder point or MRP shortage"
            color={stats?.inventory?.low_stock_count > 0 ? "danger" : "success"}
            to="/admin/purchasing?tab=lowstock"
          />
          <StatCard
            title="Active BOMs"
            value={stats?.boms?.active || 0}
            subtitle={`${stats?.boms?.needs_review || 0} need review`}
            color="secondary"
            to="/admin/bom"
          />
          <StatCard
            title="Orders Needing Materials"
            value={stats?.inventory?.active_orders || 0}
            subtitle="For MRP planning"
            color="neutral"
            to="/admin/purchasing"
          />
        </div>
      </div>

      {/* OPERATIONS Section */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
            Operations
          </h2>
          <div className="flex-1 h-px bg-gray-800"></div>
          <Link
            to="/admin/production"
            className="text-xs text-blue-400 hover:text-blue-300"
            aria-label="View all Operations"
          >
            View all →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            title="In Production"
            value={stats?.production?.in_progress || 0}
            subtitle={`${stats?.production?.scheduled || 0} scheduled, ${stats?.production?.ready_to_start || 0} ready to start`}
            color="primary"
            to="/admin/production"
          />
          <StatCard
            title="Manufacturing"
            value={
              (stats?.production?.in_progress || 0) +
              (stats?.production?.scheduled || 0)
            }
            subtitle="Active work orders"
            color="secondary"
            to="/admin/manufacturing"
          />
          <StatCard
            title="Ready to Ship"
            value={stats?.orders?.ready_to_ship || 0}
            subtitle="Awaiting shipment"
            color="neutral"
            to="/admin/shipping"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Orders */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center">
            <h3 className="font-semibold text-white">Recent Orders</h3>
            <Link
              to="/admin/orders"
              className="text-sm text-blue-400 hover:text-blue-300"
              aria-label="View all Orders"
            >
              View all →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Order
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Product
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Status
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.length > 0 ? (
                  recentOrders.map((order) => (
                    <RecentOrderRow key={order.id} order={order} />
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-gray-500">
                      No recent orders
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pending BOM Reviews */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center">
            <h3 className="font-semibold text-white">BOMs Needing Review</h3>
            <Link
              to="/admin/bom"
              aria-label="View all BOMs"
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              View all →
            </Link>
          </div>
          <div className="divide-y divide-gray-800">
            {pendingBOMs.length > 0 ? (
              pendingBOMs.map((bom) => (
                <div
                  key={bom.id}
                  className="px-6 py-4 hover:bg-gray-800/50 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-white font-medium">{bom.code}</p>
                      <p className="text-sm text-gray-400">{bom.name}</p>
                    </div>
                    <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full">
                      Needs Review
                    </span>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-gray-500">
                    <span>{bom.line_count || 0} components</span>
                    <span>
                      ${parseFloat(bom.total_cost || 0).toFixed(2)} cost
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-6 py-8 text-center text-gray-500">
                No BOMs pending review
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
