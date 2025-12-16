import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import ProductionSchedulingModal from "../../components/ProductionSchedulingModal";
import ProductionScheduler from "../../components/ProductionScheduler";
import SplitOrderModal from "../../components/SplitOrderModal";
import ScrapOrderModal from "../../components/ScrapOrderModal";
import CompleteOrderModal from "../../components/CompleteOrderModal";
import QCInspectionModal from "../../components/QCInspectionModal";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

export default function AdminProduction() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [productionOrders, setProductionOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: "all",
    search: searchParams.get("search") || "",
  });

  // Create order modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [products, setProducts] = useState([]);
  const [createForm, setCreateForm] = useState({
    product_id: "",
    quantity_ordered: 1,
    priority: 3,
    due_date: "",
    notes: "",
  });
  const [creating, setCreating] = useState(false);

  // Scheduling modal state
  const [showSchedulingModal, setShowSchedulingModal] = useState(false);
  const [selectedOrderForScheduling, setSelectedOrderForScheduling] =
    useState(null);

  // Split modal state
  const [showSplitModal, setShowSplitModal] = useState(false);
  const [selectedOrderForSplit, setSelectedOrderForSplit] = useState(null);

  // Scrap modal state
  const [showScrapModal, setShowScrapModal] = useState(false);
  const [selectedOrderForScrap, setSelectedOrderForScrap] = useState(null);

  // Complete modal state
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [selectedOrderForComplete, setSelectedOrderForComplete] =
    useState(null);

  // QC Inspection modal state
  const [showQCModal, setShowQCModal] = useState(false);
  const [selectedOrderForQC, setSelectedOrderForQC] = useState(null);

  // View mode: kanban or scheduler
  const [viewMode, setViewMode] = useState("kanban"); // kanban or scheduler

  const token = localStorage.getItem("adminToken");

  const fetchProductionOrders = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.status !== "all") params.set("status", filters.status);
      params.set("limit", "100");

      const res = await fetch(
        `${API_URL}/api/v1/production-orders/?${params}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) throw new Error("Failed to fetch production orders");

      const data = await res.json();
      setProductionOrders(data.items || data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, filters.status]);

  const fetchProducts = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/products?limit=500&active=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || data || []);
      }
    } catch (err) {
      // Products fetch failure is non-critical - product selector will just be empty
    }
  }, [token]);

  useEffect(() => {
    fetchProductionOrders();
  }, [fetchProductionOrders]);

  // Update filters if search param changes (e.g., from deep link)
  useEffect(() => {
    const searchFromParams = searchParams.get("search");
    if (searchFromParams && searchFromParams !== filters.search) {
      setFilters((prev) => ({ ...prev, search: searchFromParams }));
    }
  }, [searchParams]);

  // Fetch products when modal opens
  useEffect(() => {
    if (showCreateModal && products.length === 0) {
      fetchProducts();
    }
  }, [showCreateModal, products.length, fetchProducts]);

  const handleCreateOrder = async (e) => {
    e.preventDefault();
    if (!createForm.product_id) {
      setError("Please select a product");
      return;
    }

    setCreating(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/production-orders/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          product_id: parseInt(createForm.product_id),
          quantity_ordered: parseInt(createForm.quantity_ordered) || 1,
          priority: parseInt(createForm.priority) || 3,
          due_date: createForm.due_date || null,
          notes: createForm.notes || null,
        }),
      });

      if (res.ok) {
        setShowCreateModal(false);
        setCreateForm({
          product_id: "",
          quantity_ordered: 1,
          priority: 3,
          due_date: "",
          notes: "",
        });
        fetchProductionOrders();
      } else {
        const err = await res.json();
        setError(err.detail || "Failed to create production order");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      // Map status to the correct action endpoint
      const actionEndpoints = {
        released: "release",
        in_progress: "start",
        complete: "complete",
      };

      const action = actionEndpoints[newStatus];
      if (!action) {
        toast.error(`Invalid status transition: ${newStatus}`);
        return;
      }

      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${orderId}/${action}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (res.ok) {
        toast.success("Production order status updated");
        fetchProductionOrders();
      } else {
        const errorData = await res.json();
        toast.error(
          `Failed to update status: ${errorData.detail || "Unknown error"}`
        );
      }
    } catch (err) {
      toast.error(`Failed to update status: ${err.message || "Network error"}`);
    }
  };

  const filteredOrders = productionOrders.filter((o) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      o.code?.toLowerCase().includes(search) ||
      o.product?.name?.toLowerCase().includes(search) ||
      o.sales_order?.order_number?.toLowerCase().includes(search)
    );
  });

  // Group by status for kanban view
  const groupedOrders = {
    draft: filteredOrders.filter((o) => o.status === "draft"),
    released: filteredOrders.filter((o) => o.status === "released"),
    in_progress: filteredOrders.filter((o) => o.status === "in_progress"),
    complete: filteredOrders.filter((o) => o.status === "complete"),
    scrapped: filteredOrders.filter((o) => o.status === "scrapped"),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Production</h1>
          <p className="text-gray-400 mt-1">
            Track print jobs and production orders
          </p>
        </div>
        <div className="flex gap-3">
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode("kanban")}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                viewMode === "kanban"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Kanban
            </button>
            <button
              onClick={() => setViewMode("scheduler")}
              className={`px-4 py-2 rounded text-sm transition-colors ${
                viewMode === "scheduler"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              Scheduler
            </button>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500"
          >
            + Create Production Order
          </button>
        </div>
      </div>

      {/* Scheduler View */}
      {viewMode === "scheduler" && (
        <ProductionScheduler onScheduleUpdate={fetchProductionOrders} />
      )}

      {/* Kanban View */}
      {viewMode === "kanban" && (
        <>
          {/* Filters */}
          <div className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Search by PO code, product, or sales order..."
                value={filters.search}
                onChange={(e) =>
                  setFilters({ ...filters, search: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500"
              />
            </div>
            <select
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="all">All Status</option>
              <option value="draft">Draft</option>
              <option value="released">Released</option>
              <option value="in_progress">In Progress</option>
              <option value="complete">Complete</option>
              <option value="scrapped">Scrapped</option>
              <option value="on_hold">On Hold</option>
              <option value="split">Split (Parent)</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-6 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Draft</p>
              <p className="text-2xl font-bold text-gray-400">
                {groupedOrders.draft.length}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Released</p>
              <p className="text-2xl font-bold text-blue-400">
                {groupedOrders.released.length}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">In Progress</p>
              <p className="text-2xl font-bold text-purple-400">
                {groupedOrders.in_progress.length}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Completed Today</p>
              <p className="text-2xl font-bold text-green-400">
                {
                  groupedOrders.complete.filter((o) => {
                    const today = new Date().toDateString();
                    return (
                      o.completed_at &&
                      new Date(o.completed_at).toDateString() === today
                    );
                  }).length
                }
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Scrapped Today</p>
              <p className="text-2xl font-bold text-red-400">
                {
                  groupedOrders.scrapped.filter((o) => {
                    const today = new Date().toDateString();
                    return (
                      o.scrapped_at &&
                      new Date(o.scrapped_at).toDateString() === today
                    );
                  }).length
                }
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-sm">Total Active</p>
              <p className="text-2xl font-bold text-white">
                {groupedOrders.released.length +
                  groupedOrders.in_progress.length}
              </p>
            </div>
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

          {/* Kanban Board */}
          {!loading && (
            <div className="grid grid-cols-4 gap-4">
              {/* Draft Column */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl">
                <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                  <h3 className="font-medium text-white">Draft</h3>
                  <span className="text-gray-500 text-sm">
                    ({groupedOrders.draft.length})
                  </span>
                </div>
                <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
                  {groupedOrders.draft.map((order) => (
                    <div
                      key={order.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg p-4"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-white font-medium">
                          {order.code}
                        </span>
                        <span className="text-xs text-gray-500">
                          {order.quantity_ordered} units
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mb-3">
                        {order.product_name || "N/A"}
                      </p>
                      <button
                        onClick={() => handleStatusUpdate(order.id, "released")}
                        className="w-full py-1.5 bg-blue-600/20 text-blue-400 rounded text-sm hover:bg-blue-600/30"
                      >
                        Release
                      </button>
                    </div>
                  ))}
                  {groupedOrders.draft.length === 0 && (
                    <p className="text-gray-500 text-sm text-center py-8">
                      No draft orders
                    </p>
                  )}
                </div>
              </div>

              {/* Released Column */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl">
                <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  <h3 className="font-medium text-white">Released</h3>
                  <span className="text-gray-500 text-sm">
                    ({groupedOrders.released.length})
                  </span>
                </div>
                <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
                  {groupedOrders.released.map((order) => (
                    <div
                      key={order.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg p-4"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-white font-medium">
                          {order.code}
                        </span>
                        <span className="text-xs text-gray-500">
                          {order.quantity_ordered} units
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mb-2">
                        {order.product_name || "N/A"}
                      </p>
                      {order.scheduled_start && (
                        <p className="text-xs text-gray-500 mb-2">
                          📅 {new Date(order.scheduled_start).toLocaleString()}
                        </p>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setSelectedOrderForScheduling(order);
                            setShowSchedulingModal(true);
                          }}
                          className="flex-1 py-1.5 bg-blue-600/20 text-blue-400 rounded text-sm hover:bg-blue-600/30"
                          title="Schedule to specific machine"
                        >
                          Schedule
                        </button>
                        <button
                          onClick={() =>
                            handleStatusUpdate(order.id, "in_progress")
                          }
                          className="flex-1 py-1.5 bg-purple-600/20 text-purple-400 rounded text-sm hover:bg-purple-600/30"
                          title="Start immediately without scheduling"
                        >
                          Start Now
                        </button>
                      </div>
                      <div className="flex gap-2 mt-2">
                        {order.quantity_ordered > 1 && (
                          <button
                            onClick={() => {
                              setSelectedOrderForSplit(order);
                              setShowSplitModal(true);
                            }}
                            className="flex-1 py-1.5 bg-gray-700/50 text-gray-300 rounded text-sm hover:bg-gray-700 flex items-center justify-center gap-1"
                            title="Split order across multiple machines"
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
                                d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                              />
                            </svg>
                            Split
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setSelectedOrderForScrap(order);
                            setShowScrapModal(true);
                          }}
                          className={`${
                            order.quantity_ordered > 1 ? "flex-1" : "w-full"
                          } py-1.5 bg-red-600/10 text-red-400/80 rounded text-sm hover:bg-red-600/20`}
                          title="Mark as scrap if setup failed"
                        >
                          Scrap
                        </button>
                      </div>
                    </div>
                  ))}
                  {groupedOrders.released.length === 0 && (
                    <p className="text-gray-500 text-sm text-center py-8">
                      No released orders
                    </p>
                  )}
                </div>
              </div>

              {/* In Progress Column */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl">
                <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                  <h3 className="font-medium text-white">In Progress</h3>
                  <span className="text-gray-500 text-sm">
                    ({groupedOrders.in_progress.length})
                  </span>
                </div>
                <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
                  {groupedOrders.in_progress.map((order) => (
                    <div
                      key={order.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg p-4"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-white font-medium">
                          {order.code}
                        </span>
                        <span className="text-xs text-gray-500">
                          {order.quantity_completed}/{order.quantity_ordered}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mb-2">
                        {order.product_name || "N/A"}
                      </p>
                      {order.completion_percent > 0 && (
                        <div className="w-full bg-gray-700 rounded-full h-1.5 mb-3">
                          <div
                            className="bg-purple-500 h-1.5 rounded-full"
                            style={{ width: `${order.completion_percent}%` }}
                          ></div>
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setSelectedOrderForComplete(order);
                            setShowCompleteModal(true);
                          }}
                          className="flex-1 py-1.5 bg-green-600/20 text-green-400 rounded text-sm hover:bg-green-600/30"
                        >
                          Complete
                        </button>
                        <button
                          onClick={() => {
                            setSelectedOrderForScrap(order);
                            setShowScrapModal(true);
                          }}
                          className="flex-1 py-1.5 bg-red-600/20 text-red-400 rounded text-sm hover:bg-red-600/30"
                          title="Print failed - scrap and optionally remake"
                        >
                          Scrap
                        </button>
                      </div>
                    </div>
                  ))}
                  {groupedOrders.in_progress.length === 0 && (
                    <p className="text-gray-500 text-sm text-center py-8">
                      No active production
                    </p>
                  )}
                </div>
              </div>

              {/* Completed Column */}
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl">
                <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <h3 className="font-medium text-white">Complete</h3>
                  <span className="text-gray-500 text-sm">
                    ({groupedOrders.complete.length})
                  </span>
                </div>
                <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
                  {groupedOrders.complete.slice(0, 10).map((order) => (
                    <div
                      key={order.id}
                      className={`bg-gray-800 border rounded-lg p-4 ${
                        order.qc_status === "pending"
                          ? "border-yellow-500/50"
                          : order.qc_status === "passed"
                          ? "border-green-500/30 opacity-75"
                          : order.qc_status === "failed"
                          ? "border-red-500/50"
                          : "border-gray-700 opacity-75"
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-white font-medium">
                          {order.code}
                        </span>
                        <div className="flex items-center gap-2">
                          {/* QC Status Badge */}
                          {order.qc_status === "pending" && (
                            <span className="px-1.5 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded">
                              QC Pending
                            </span>
                          )}
                          {order.qc_status === "passed" && (
                            <span className="px-1.5 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                              QC Passed
                            </span>
                          )}
                          {order.qc_status === "failed" && (
                            <span className="px-1.5 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">
                              QC Failed
                            </span>
                          )}
                          <span className="text-xs text-gray-500">
                            {order.quantity_completed}/{order.quantity_ordered}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-400">
                        {order.product_name || "N/A"}
                      </p>
                      {order.completed_at && (
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(order.completed_at).toLocaleDateString()}
                        </p>
                      )}
                      {/* QC Action Button */}
                      {(order.qc_status === "pending" || order.qc_status === "failed") && (
                        <button
                          onClick={() => {
                            setSelectedOrderForQC(order);
                            setShowQCModal(true);
                          }}
                          className="w-full mt-3 py-1.5 bg-yellow-600/20 text-yellow-400 rounded text-sm hover:bg-yellow-600/30"
                        >
                          {order.qc_status === "pending" ? "Perform QC Inspection" : "Re-inspect"}
                        </button>
                      )}
                    </div>
                  ))}
                  {groupedOrders.complete.length === 0 && (
                    <p className="text-gray-500 text-sm text-center py-8">
                      No completed orders
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Scheduling Modal */}
      {showSchedulingModal && selectedOrderForScheduling && (
        <ProductionSchedulingModal
          productionOrder={selectedOrderForScheduling}
          onClose={() => {
            setShowSchedulingModal(false);
            setSelectedOrderForScheduling(null);
          }}
          onSchedule={() => {
            fetchProductionOrders();
            setShowSchedulingModal(false);
            setSelectedOrderForScheduling(null);
          }}
        />
      )}

      {/* Split Order Modal */}
      {showSplitModal && selectedOrderForSplit && (
        <SplitOrderModal
          productionOrder={selectedOrderForSplit}
          onClose={() => {
            setShowSplitModal(false);
            setSelectedOrderForSplit(null);
          }}
          onSplit={() => {
            fetchProductionOrders();
            setShowSplitModal(false);
            setSelectedOrderForSplit(null);
          }}
        />
      )}

      {/* Scrap Order Modal */}
      {showScrapModal && selectedOrderForScrap && (
        <ScrapOrderModal
          productionOrder={selectedOrderForScrap}
          onClose={() => {
            setShowScrapModal(false);
            setSelectedOrderForScrap(null);
          }}
          onScrap={() => {
            fetchProductionOrders();
            setShowScrapModal(false);
            setSelectedOrderForScrap(null);
          }}
        />
      )}

      {/* Complete Order Modal */}
      {showCompleteModal && selectedOrderForComplete && (
        <CompleteOrderModal
          productionOrder={selectedOrderForComplete}
          onClose={() => {
            setShowCompleteModal(false);
            setSelectedOrderForComplete(null);
          }}
          onComplete={() => {
            fetchProductionOrders();
            setShowCompleteModal(false);
            setSelectedOrderForComplete(null);
          }}
        />
      )}

      {/* QC Inspection Modal */}
      {showQCModal && selectedOrderForQC && (
        <QCInspectionModal
          productionOrder={selectedOrderForQC}
          onClose={() => {
            setShowQCModal(false);
            setSelectedOrderForQC(null);
          }}
          onComplete={() => {
            fetchProductionOrders();
            setShowQCModal(false);
            setSelectedOrderForQC(null);
          }}
        />
      )}

      {/* Create Production Order Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-white">
                Create Production Order
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateOrder} className="space-y-4">
              {/* Product Selection */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Product *
                </label>
                <select
                  value={createForm.product_id}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, product_id: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                  required
                >
                  <option value="">Select a product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} - {p.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Quantity *
                </label>
                <input
                  type="number"
                  min="1"
                  value={createForm.quantity_ordered}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      quantity_ordered: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Priority
                </label>
                <select
                  value={createForm.priority}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, priority: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                >
                  <option value="1">1 - Urgent</option>
                  <option value="2">2 - High</option>
                  <option value="3">3 - Normal</option>
                  <option value="4">4 - Low</option>
                  <option value="5">5 - Lowest</option>
                </select>
              </div>

              {/* Due Date */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Due Date
                </label>
                <input
                  type="date"
                  value={createForm.due_date}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, due_date: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Notes
                </label>
                <textarea
                  value={createForm.notes}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, notes: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white h-20"
                  placeholder="Optional notes..."
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500 disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
