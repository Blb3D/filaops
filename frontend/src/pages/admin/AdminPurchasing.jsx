import { useState, useEffect } from "react";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

const statusColors = {
  draft: "bg-gray-500/20 text-gray-400",
  ordered: "bg-blue-500/20 text-blue-400",
  shipped: "bg-purple-500/20 text-purple-400",
  received: "bg-green-500/20 text-green-400",
  closed: "bg-green-700/20 text-green-300",
  cancelled: "bg-red-500/20 text-red-400",
};

/**
 * Admin interface for managing purchase orders, vendors, Amazon imports, and low-stock items.
 *
 * Renders a multi-tab UI with listing, filtering, and CRUD actions for POs and vendors; supports
 * receiving, file uploads, Amazon CSV import with product mapping and on-the-fly item creation,
 * and low-stock reporting with quick PO creation links.
 *
 * @returns {JSX.Element} The AdminPurchasing React component UI.
 */
export default function AdminPurchasing() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("orders"); // orders | vendors | import | low-stock

  // Amazon Import State
  const [importFile, setImportFile] = useState(null);
  const [importData, setImportData] = useState(null);
  const [importMappings, setImportMappings] = useState({});
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [orders, setOrders] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ status: "all", search: "" });

  // Low Stock State
  const [lowStockItems, setLowStockItems] = useState([]);
  const [lowStockSummary, setLowStockSummary] = useState(null);
  const [lowStockLoading, setLowStockLoading] = useState(false);

  // Modals
  const [showVendorModal, setShowVendorModal] = useState(false);
  const [showPOModal, setShowPOModal] = useState(false);
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [selectedPO, setSelectedPO] = useState(null);
  const [selectedVendor, setSelectedVendor] = useState(null);

  // Create New Item Modal
  const [showCreateItemModal, setShowCreateItemModal] = useState(false);
  const [createItemForAsin, setCreateItemForAsin] = useState(null);
  const [newItemForm, setNewItemForm] = useState({
    sku: "",
    name: "",
    item_type: "raw_material",
  });
  const [creatingItem, setCreatingItem] = useState(false);
  const [expandedDescriptions, setExpandedDescriptions] = useState({});
  const [productSearches, setProductSearches] = useState({}); // Per-ASIN search filters

  const token = localStorage.getItem("adminToken");

  useEffect(() => {
    if (activeTab === "orders") fetchOrders();
    else if (activeTab === "vendors") fetchVendors();
    else if (activeTab === "low-stock") fetchLowStock();
    // Import tab doesn't need data fetching on mount
    fetchProducts();
  }, [activeTab, filters.status]);

  // Fetch low stock count on mount for badge
  useEffect(() => {
    fetchLowStock();
  }, []);

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.status !== "all") params.set("status", filters.status);
      params.set("limit", "100");

      const res = await fetch(`${API_URL}/api/v1/purchase-orders?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch orders");
      setOrders(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchVendors = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/vendors?active_only=false`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch vendors");
      setVendors(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/items?limit=500`);
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || []);
      }
    } catch (err) {
      // Products fetch failure is non-critical - product selector will just be empty
    }
  };

  const fetchLowStock = async () => {
    setLowStockLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/items/low-stock`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLowStockItems(data.items || []);
        setLowStockSummary(data.summary || null);
      }
    } catch (err) {
      setError("Failed to load low stock items. Please refresh the page.");
    } finally {
      setLowStockLoading(false);
    }
  };

  const fetchPODetails = async (poId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/purchase-orders/${poId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedPO(data);
        return data;
      } else {
        setError("Failed to load purchase order details.");
      }
    } catch (err) {
      setError(`Failed to load purchase order: ${err.message || "Network error"}`);
    }
    return null;
  };

  // ============================================================================
  // Vendor CRUD
  // ============================================================================

  const handleSaveVendor = async (vendorData) => {
    try {
      const url = selectedVendor
        ? `${API_URL}/api/v1/vendors/${selectedVendor.id}`
        : `${API_URL}/api/v1/vendors`;
      const method = selectedVendor ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(vendorData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save vendor");
      }

      toast.success(selectedVendor ? "Vendor updated" : "Vendor created");
      setShowVendorModal(false);
      setSelectedVendor(null);
      fetchVendors();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDeleteVendor = async (vendorId) => {
    if (!confirm("Are you sure you want to delete this vendor?")) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/vendors/${vendorId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to delete vendor");
      toast.success("Vendor deleted");
      fetchVendors();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // ============================================================================
  // Create New Item (from Import)
  // ============================================================================

  const openCreateItemModal = (asin, amazonProduct) => {
    setCreateItemForAsin(asin);
    // Pre-fill with Amazon data
    const suggestedSku = `AMZ-${asin.slice(-8).toUpperCase()}`;
    setNewItemForm({
      sku: suggestedSku,
      name: amazonProduct.title,
      item_type:
        amazonProduct.suggested_category === "filament"
          ? "raw_material"
          : "supply",
    });
    setShowCreateItemModal(true);
  };

  const handleCreateItem = async () => {
    if (!newItemForm.sku || !newItemForm.name) {
      toast.warning("SKU and Name are required");
      return;
    }

    setCreatingItem(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/items`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sku: newItemForm.sku,
          name: newItemForm.name,
          item_type: newItemForm.item_type,
          active: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create item");
      }

      const newItem = await res.json();

      // Add to products list and map ASIN to it
      setProducts((prev) => [
        ...prev,
        { id: newItem.id, sku: newItem.sku, name: newItem.name },
      ]);
      handleMappingChange(createItemForAsin, "product_id", newItem.id);

      toast.success("Item created and mapped");
      setShowCreateItemModal(false);
      setCreateItemForAsin(null);
      setNewItemForm({ sku: "", name: "", item_type: "raw_material" });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreatingItem(false);
    }
  };

  const toggleDescription = (asin) => {
    setExpandedDescriptions((prev) => ({ ...prev, [asin]: !prev[asin] }));
  };

  // ============================================================================
  // Purchase Order CRUD
  // ============================================================================

  const handleSavePO = async (poData) => {
    try {
      const url = selectedPO
        ? `${API_URL}/api/v1/purchase-orders/${selectedPO.id}`
        : `${API_URL}/api/v1/purchase-orders`;
      const method = selectedPO ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(poData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save PO");
      }

      toast.success(selectedPO ? "Purchase order updated" : "Purchase order created");
      setShowPOModal(false);
      setSelectedPO(null);
      fetchOrders();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleStatusChange = async (poId, newStatus, extraData = {}) => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/purchase-orders/${poId}/status`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status: newStatus, ...extraData }),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update status");
      }

      toast.success(`Status updated to ${newStatus}`);
      fetchOrders();
      if (selectedPO?.id === poId) {
        fetchPODetails(poId);
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleReceive = async (receiveData) => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/purchase-orders/${selectedPO.id}/receive`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(receiveData),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to receive items");
      }

      const result = await res.json();
      toast.success(
        `Received ${result.total_quantity} items. ${result.transactions_created.length} inventory transactions created.`
      );
      setShowReceiveModal(false);
      fetchOrders();
      fetchPODetails(selectedPO.id);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleFileUpload = async (poId, file) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(
        `${API_URL}/api/v1/purchase-orders/${poId}/upload`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to upload file");
      }

      const result = await res.json();
      toast.success(
        `File uploaded to ${
          result.storage === "google_drive" ? "Google Drive" : "local storage"
        }`
      );
      fetchPODetails(poId);
      return result;
    } catch (err) {
      toast.error(err.message);
      return null;
    }
  };

  const handleDeletePO = async (poId, poNumber) => {
    if (!confirm(`Delete PO ${poNumber}? This cannot be undone.`)) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/purchase-orders/${poId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete PO");
      }

      toast.success("Purchase order deleted");
      fetchOrders();
      if (selectedPO?.id === poId) {
        setSelectedPO(null);
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleCancelPO = async (poId, poNumber) => {
    if (!confirm(`Cancel PO ${poNumber}? This will mark it as cancelled.`))
      return;

    try {
      const res = await fetch(
        `${API_URL}/api/v1/purchase-orders/${poId}/status`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status: "cancelled" }),
        }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to cancel PO");
      }

      toast.success("Purchase order cancelled");
      fetchOrders();
      if (selectedPO?.id === poId) {
        const updated = await res.json();
        setSelectedPO(updated);
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  // ============================================================================
  // Amazon Import Handlers
  // ============================================================================

  const handleImportFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setImportFile(file);
    setImportData(null);
    setImportResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/v1/import/amazon/parse`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to parse file");
      }

      const data = await res.json();
      setImportData(data);

      // Initialize mappings with suggested categories
      const mappings = {};
      data.products.forEach((p) => {
        mappings[p.asin] = {
          asin: p.asin,
          product_id: null,
          category:
            p.suggested_category === "subscription"
              ? "skip"
              : p.suggested_category,
        };
      });
      setImportMappings(mappings);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleMappingChange = (asin, field, value) => {
    setImportMappings((prev) => ({
      ...prev,
      [asin]: { ...prev[asin], [field]: value },
    }));
  };

  const executeImport = async () => {
    if (!importData) return;

    setImporting(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/import/amazon/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          orders: importData.orders,
          mappings: importMappings,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Import failed");
      }

      const result = await res.json();
      setImportResult(result);
      toast.success(
        `Import complete! ${result.pos_created} POs created with ${result.lines_created} line items.`
      );
      fetchOrders();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setImporting(false);
    }
  };

  // ============================================================================
  // Filters
  // ============================================================================

  const filteredOrders = orders.filter((o) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      o.po_number?.toLowerCase().includes(search) ||
      o.vendor_name?.toLowerCase().includes(search)
    );
  });

  const filteredVendors = vendors.filter((v) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      v.name?.toLowerCase().includes(search) ||
      v.code?.toLowerCase().includes(search) ||
      v.contact_name?.toLowerCase().includes(search)
    );
  });

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-white">Purchasing</h1>
          <p className="text-gray-400 mt-1">
            Manage vendors and purchase orders
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === "vendors" && (
            <button
              onClick={() => {
                setSelectedVendor(null);
                setShowVendorModal(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
            >
              + New Vendor
            </button>
          )}
          {activeTab === "orders" && (
            <button
              onClick={() => {
                setSelectedPO(null);
                setShowPOModal(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
            >
              + New PO
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800">
        <button
          onClick={() => setActiveTab("orders")}
          className={`pb-2 px-1 text-sm font-medium transition-colors ${
            activeTab === "orders"
              ? "text-blue-400 border-b-2 border-blue-400"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Purchase Orders
        </button>
        <button
          onClick={() => setActiveTab("vendors")}
          className={`pb-2 px-1 text-sm font-medium transition-colors ${
            activeTab === "vendors"
              ? "text-blue-400 border-b-2 border-blue-400"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Vendors
        </button>
        <button
          onClick={() => setActiveTab("import")}
          className={`pb-2 px-1 text-sm font-medium transition-colors ${
            activeTab === "import"
              ? "text-blue-400 border-b-2 border-blue-400"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Import
        </button>
        <button
          onClick={() => setActiveTab("low-stock")}
          className={`pb-2 px-1 text-sm font-medium transition-colors flex items-center gap-2 ${
            activeTab === "low-stock"
              ? "text-orange-400 border-b-2 border-orange-400"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Low Stock
          {lowStockItems.length > 0 && (
            <span className="bg-orange-500/20 text-orange-400 px-1.5 py-0.5 text-xs rounded-full">
              {lowStockItems.length}
            </span>
          )}
        </button>
      </div>

      {/* Filters - hide on import and low-stock tabs */}
      {activeTab !== "import" && activeTab !== "low-stock" && (
        <div className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder={
                activeTab === "orders"
                  ? "Search PO number or vendor..."
                  : "Search vendor name or code..."
              }
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500"
            />
          </div>
          {activeTab === "orders" && (
            <select
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="all">All Status</option>
              <option value="draft">Draft</option>
              <option value="ordered">Ordered</option>
              <option value="shipped">Shipped</option>
              <option value="received">Received</option>
              <option value="closed">Closed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          )}
        </div>
      )}

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

      {/* Purchase Orders Table */}
      {!loading && activeTab === "orders" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  PO #
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Vendor
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Order Date
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Expected
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Total
                </th>
                <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Lines
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((po) => (
                <tr
                  key={po.id}
                  className="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td className="py-3 px-4 text-white font-medium">
                    {po.po_number}
                  </td>
                  <td className="py-3 px-4 text-gray-300">{po.vendor_name}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        statusColors[po.status]
                      }`}
                    >
                      {po.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {po.order_date
                      ? new Date(po.order_date).toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {po.expected_date
                      ? new Date(po.expected_date).toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-right text-green-400 font-medium">
                    ${parseFloat(po.total_amount || 0).toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-center text-gray-400">
                    {po.line_count}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={async () => {
                        await fetchPODetails(po.id);
                      }}
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      View
                    </button>
                    {po.status === "draft" && (
                      <button
                        onClick={() => handleStatusChange(po.id, "ordered")}
                        className="text-green-400 hover:text-green-300 text-sm"
                      >
                        Order
                      </button>
                    )}
                    {(po.status === "ordered" || po.status === "shipped") && (
                      <button
                        onClick={async () => {
                          await fetchPODetails(po.id);
                          setShowReceiveModal(true);
                        }}
                        className="text-purple-400 hover:text-purple-300 text-sm"
                      >
                        Receive
                      </button>
                    )}
                    {po.status === "draft" && (
                      <button
                        onClick={() => handleDeletePO(po.id, po.po_number)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Delete
                      </button>
                    )}
                    {!["draft", "closed", "cancelled"].includes(po.status) && (
                      <button
                        onClick={() => handleCancelPO(po.id, po.po_number)}
                        className="text-orange-400 hover:text-orange-300 text-sm"
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filteredOrders.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-gray-500">
                    No purchase orders found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Vendors Table */}
      {!loading && activeTab === "vendors" && (
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
                  Contact
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Email
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Phone
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Location
                </th>
                <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  POs
                </th>
                <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Active
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredVendors.map((vendor) => (
                <tr
                  key={vendor.id}
                  className="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td className="py-3 px-4 text-white font-medium">
                    {vendor.code}
                  </td>
                  <td className="py-3 px-4 text-gray-300">{vendor.name}</td>
                  <td className="py-3 px-4 text-gray-400">
                    {vendor.contact_name || "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {vendor.email || "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {vendor.phone || "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {vendor.city && vendor.state
                      ? `${vendor.city}, ${vendor.state}`
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-center text-gray-400">
                    {vendor.po_count}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs ${
                        vendor.is_active
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {vendor.is_active ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <button
                      onClick={() => {
                        setSelectedVendor(vendor);
                        setShowVendorModal(true);
                      }}
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteVendor(vendor.id)}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {filteredVendors.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-gray-500">
                    No vendors found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Import Tab */}
      {activeTab === "import" && (
        <div className="space-y-6">
          {/* Upload Section */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              Import Amazon Business Orders
            </h3>
            <p className="text-gray-400 text-sm mb-4">
              Upload your Amazon Business CSV export to import orders as
              Purchase Orders.
            </p>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium cursor-pointer">
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
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                Select CSV File
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleImportFileSelect}
                  className="hidden"
                />
              </label>
              {importFile && (
                <span className="text-gray-300">{importFile.name}</span>
              )}
            </div>
          </div>

          {/* Summary */}
          {importData && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">
                Import Summary
              </h3>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-white">
                    {importData.order_count}
                  </div>
                  <div className="text-sm text-gray-400">Orders</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-white">
                    {importData.product_count}
                  </div>
                  <div className="text-sm text-gray-400">Unique Products</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400">
                    ${importData.total_spend.toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-400">Total Spend</div>
                </div>
              </div>

              {/* Product Mapping Table */}
              <h4 className="text-md font-medium text-white mb-3">
                Product Mapping
              </h4>
              <p className="text-gray-400 text-sm mb-4">
                Assign each Amazon product to an existing item or mark as MISC.
                Skip subscriptions/services.
              </p>
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full">
                  <thead className="bg-gray-800/50 sticky top-0">
                    <tr>
                      <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">
                        Product
                      </th>
                      <th className="text-center py-2 px-3 text-xs font-medium text-gray-400">
                        Ordered
                      </th>
                      <th className="text-center py-2 px-3 text-xs font-medium text-gray-400">
                        Recv Qty
                      </th>
                      <th className="text-right py-2 px-3 text-xs font-medium text-gray-400">
                        Spent
                      </th>
                      <th className="text-right py-2 px-3 text-xs font-medium text-gray-400">
                        CPU
                      </th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">
                        Category
                      </th>
                      <th className="text-left py-2 px-3 text-xs font-medium text-gray-400">
                        Map To
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {importData.products.map((product) => {
                      const mapping = importMappings[product.asin] || {};
                      const isExpanded = expandedDescriptions[product.asin];
                      return (
                        <tr
                          key={product.asin}
                          className="border-b border-gray-800"
                        >
                          <td className="py-2 px-3 max-w-md">
                            <div className="text-white text-sm font-medium">
                              {product.brand}
                            </div>
                            <div
                              className={`text-gray-400 text-xs cursor-pointer hover:text-gray-300 ${
                                isExpanded ? "" : "line-clamp-2"
                              }`}
                              onClick={() => toggleDescription(product.asin)}
                              title="Click to expand/collapse"
                            >
                              {product.title}
                            </div>
                            <div className="text-gray-500 text-xs mt-1">
                              ASIN: {product.asin}
                            </div>
                          </td>
                          <td className="py-2 px-3 text-center text-gray-400 text-sm">
                            {product.total_qty}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <input
                              type="number"
                              min="1"
                              value={mapping.qty_override || product.total_qty}
                              onChange={(e) =>
                                handleMappingChange(
                                  product.asin,
                                  "qty_override",
                                  parseInt(e.target.value) || product.total_qty
                                )
                              }
                              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-16 text-center"
                              title="Adjust if pack contains multiple units (e.g., 240 magnets in 1 pack)"
                            />
                          </td>
                          <td className="py-2 px-3 text-right text-green-400">
                            ${product.total_spent.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-blue-400 text-sm">
                            $
                            {(
                              product.total_spent /
                              (mapping.qty_override || product.total_qty)
                            ).toFixed(4)}
                          </td>
                          <td className="py-2 px-3">
                            <select
                              value={
                                mapping.category ||
                                product.suggested_category ||
                                "misc"
                              }
                              onChange={(e) =>
                                handleMappingChange(
                                  product.asin,
                                  "category",
                                  e.target.value
                                )
                              }
                              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-full"
                            >
                              <option value="filament">Filament</option>
                              <option value="printer_parts">
                                Printer Parts
                              </option>
                              <option value="misc">Misc</option>
                              <option value="subscription">Subscription</option>
                              <option value="skip">Skip (Don't Import)</option>
                            </select>
                          </td>
                          <td className="py-2 px-3">
                            {mapping.category !== "skip" && (
                              <div className="space-y-1">
                                <input
                                  type="text"
                                  placeholder="Search items..."
                                  value={productSearches[product.asin] || ""}
                                  onChange={(e) =>
                                    setProductSearches({
                                      ...productSearches,
                                      [product.asin]: e.target.value,
                                    })
                                  }
                                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white w-full"
                                />
                                <select
                                  value={mapping.product_id || ""}
                                  onChange={(e) => {
                                    if (e.target.value === "CREATE_NEW") {
                                      openCreateItemModal(
                                        product.asin,
                                        product
                                      );
                                    } else {
                                      handleMappingChange(
                                        product.asin,
                                        "product_id",
                                        e.target.value
                                          ? parseInt(e.target.value)
                                          : null
                                      );
                                    }
                                  }}
                                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-full"
                                >
                                  <option value="">MISC (Auto)</option>
                                  <option
                                    value="CREATE_NEW"
                                    className="text-blue-400"
                                  >
                                    + Create New Item
                                  </option>
                                  <optgroup label="Matching Items">
                                    {products
                                      .filter((p) => {
                                        const search = (
                                          productSearches[product.asin] || ""
                                        ).toLowerCase();
                                        if (!search) return true;
                                        return (
                                          p.sku
                                            .toLowerCase()
                                            .includes(search) ||
                                          p.name.toLowerCase().includes(search)
                                        );
                                      })
                                      .slice(0, 50)
                                      .map((p) => (
                                        <option key={p.id} value={p.id}>
                                          {p.sku} - {p.name}
                                        </option>
                                      ))}
                                  </optgroup>
                                </select>
                              </div>
                            )}
                            {mapping.category === "skip" && (
                              <span className="text-gray-500 text-sm">
                                Will not import
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Import Button */}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={executeImport}
                  disabled={importing}
                  className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded-lg text-white font-medium flex items-center gap-2"
                >
                  {importing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Importing...
                    </>
                  ) : (
                    <>
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
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                        />
                      </svg>
                      Import {importData.order_count} Orders
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Import Result */}
          {importResult && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
              <h4 className="text-green-400 font-medium mb-2">
                Import Complete!
              </h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>POs Created: {importResult.pos_created}</li>
                <li>Line Items: {importResult.lines_created}</li>
                <li>Skipped (duplicates): {importResult.skipped_orders}</li>
                {importResult.errors.length > 0 && (
                  <li className="text-red-400">
                    Errors: {importResult.errors.length}
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Low Stock Tab */}
      {activeTab === "low-stock" && (
        <div className="space-y-6">
          {/* Summary Cards */}
          {lowStockSummary && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4">
                <div className="text-3xl font-bold text-orange-400">
                  {lowStockSummary.total_items_low}
                </div>
                <div className="text-sm text-gray-400">
                  Items Below Reorder Point
                </div>
              </div>
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="text-3xl font-bold text-red-400">
                  ${lowStockSummary.total_shortfall_value?.toFixed(2) || "0.00"}
                </div>
                <div className="text-sm text-gray-400">
                  Est. Shortfall Value
                </div>
              </div>
            </div>
          )}

          {/* Low Stock Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-white">
                Items Below Reorder Point
              </h3>
              <button
                onClick={fetchLowStock}
                disabled={lowStockLoading}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300"
              >
                {lowStockLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {lowStockLoading ? (
              <div className="p-8 text-center text-gray-400">
                Loading low stock items...
              </div>
            ) : lowStockItems.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-green-400 text-lg font-medium mb-2">
                  All Stock Levels OK
                </div>
                <p className="text-gray-400 text-sm">
                  No items are currently below their reorder point.
                </p>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Item
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Category
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Available
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Reorder Pt
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Shortfall
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {lowStockItems.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-gray-800 hover:bg-gray-800/30"
                    >
                      <td className="py-3 px-4">
                        <div className="text-white font-medium">
                          {item.name}
                        </div>
                        <div className="text-gray-500 text-xs">{item.sku}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-sm">
                        {item.category_name || "-"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span
                          className={
                            item.available_qty <= 0
                              ? "text-red-400"
                              : "text-yellow-400"
                          }
                        >
                          {item.available_qty?.toFixed(2)} {item.unit}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {item.reorder_point?.toFixed(2)} {item.unit}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-red-400 font-medium">
                          -{item.shortfall?.toFixed(2)} {item.unit}
                        </span>
                        {item.mrp_shortage > 0 &&
                          item.shortage_source === "mrp" && (
                            <div className="text-xs text-blue-400 mt-1">
                              (MRP: {item.mrp_shortage.toFixed(2)})
                            </div>
                          )}
                        {item.mrp_shortage > 0 &&
                          item.shortage_source === "both" && (
                            <div className="text-xs text-yellow-400 mt-1">
                              (MRP: {item.mrp_shortage.toFixed(2)})
                            </div>
                          )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => {
                              setShowPOModal(true);
                              // Pre-populate with this item
                            }}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs text-white"
                          >
                            Create PO
                          </button>
                          <button
                            onClick={() =>
                              (window.location.href = `/admin?tab=items&edit=${item.id}`)
                            }
                            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
                          >
                            Edit Item
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Vendor Modal */}
      {showVendorModal && (
        <VendorModal
          vendor={selectedVendor}
          onClose={() => {
            setShowVendorModal(false);
            setSelectedVendor(null);
          }}
          onSave={handleSaveVendor}
        />
      )}

      {/* PO Modal */}
      {showPOModal && (
        <POModal
          po={selectedPO}
          vendors={vendors}
          products={products}
          onClose={() => {
            setShowPOModal(false);
            setSelectedPO(null);
          }}
          onSave={handleSavePO}
        />
      )}

      {/* PO Detail Modal */}
      {selectedPO && !showPOModal && !showReceiveModal && (
        <PODetailModal
          po={selectedPO}
          onClose={() => setSelectedPO(null)}
          onStatusChange={handleStatusChange}
          onEdit={() => setShowPOModal(true)}
          onReceive={() => setShowReceiveModal(true)}
          onUpload={(file) => handleFileUpload(selectedPO.id, file)}
        />
      )}

      {/* Receive Modal */}
      {showReceiveModal && selectedPO && (
        <ReceiveModal
          po={selectedPO}
          onClose={() => setShowReceiveModal(false)}
          onReceive={handleReceive}
        />
      )}

      {/* Create New Item Modal */}
      {showCreateItemModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-xl p-6 w-full max-w-lg border border-gray-800">
            <h3 className="text-xl font-bold text-white mb-4">
              Create New Item
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">
                  SKU *
                </label>
                <input
                  type="text"
                  value={newItemForm.sku}
                  onChange={(e) =>
                    setNewItemForm({ ...newItemForm, sku: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="e.g., FIL-PLA-BLK-1KG"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">
                  Name *
                </label>
                <textarea
                  value={newItemForm.name}
                  onChange={(e) =>
                    setNewItemForm({ ...newItemForm, name: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  rows={3}
                  placeholder="Item name"
                />
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">
                  Item Type
                </label>
                <select
                  value={newItemForm.item_type}
                  onChange={(e) =>
                    setNewItemForm({
                      ...newItemForm,
                      item_type: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  <option value="raw_material">Raw Material (Filament)</option>
                  <option value="supply">Supply</option>
                  <option value="component">Component</option>
                  <option value="finished_good">Finished Good</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCreateItemModal(false);
                  setCreateItemForAsin(null);
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateItem}
                disabled={creatingItem}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-white flex items-center gap-2"
              >
                {creatingItem ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Creating...
                  </>
                ) : (
                  "Create & Map"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Vendor Modal Component
/**
 * Render a modal form for creating or editing a vendor.
 *
 * Renders a controlled form prefilled when `vendor` is provided, validates that the vendor name is present,
 * calls `onSave` with the collected vendor data when the form is submitted, and calls `onClose` to dismiss the modal.
 *
 * @param {{id?: number, name?: string, code?: string, contact_name?: string, email?: string, phone?: string, website?: string, address_line1?: string, address_line2?: string, city?: string, state?: string, postal_code?: string, country?: string, payment_terms?: string, account_number?: string, notes?: string, is_active?: boolean}|null} vendor - Optional vendor object to edit; fields provided will prefill the form.
 * @param {() => void} onClose - Callback invoked to close the modal without saving.
 * @param {(vendorData: Object) => void} onSave - Callback invoked with the vendor form data when the user submits a valid form.
 * @returns {JSX.Element} The vendor modal element.
 */

function VendorModal({ vendor, onClose, onSave }) {
  const toast = useToast();
  const [form, setForm] = useState({
    name: vendor?.name || "",
    code: vendor?.code || "",
    contact_name: vendor?.contact_name || "",
    email: vendor?.email || "",
    phone: vendor?.phone || "",
    website: vendor?.website || "",
    address_line1: vendor?.address_line1 || "",
    address_line2: vendor?.address_line2 || "",
    city: vendor?.city || "",
    state: vendor?.state || "",
    postal_code: vendor?.postal_code || "",
    country: vendor?.country || "USA",
    payment_terms: vendor?.payment_terms || "",
    account_number: vendor?.account_number || "",
    notes: vendor?.notes || "",
    is_active: vendor?.is_active ?? true,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.warning("Vendor name is required");
      return;
    }
    onSave(form);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-2xl w-full mx-auto p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white">
              {vendor ? "Edit Vendor" : "New Vendor"}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
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

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Code (auto if empty)
                </label>
                <input
                  type="text"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="VND-001"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Contact Name
                </label>
                <input
                  type="text"
                  value={form.contact_name}
                  onChange={(e) =>
                    setForm({ ...form, contact_name: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Phone
                </label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Website
                </label>
                <input
                  type="text"
                  value={form.website}
                  onChange={(e) =>
                    setForm({ ...form, website: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>

            <div className="border-t border-gray-800 pt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">
                Address
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <input
                    type="text"
                    value={form.address_line1}
                    onChange={(e) =>
                      setForm({ ...form, address_line1: e.target.value })
                    }
                    placeholder="Address Line 1"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="text"
                    value={form.address_line2}
                    onChange={(e) =>
                      setForm({ ...form, address_line2: e.target.value })
                    }
                    placeholder="Address Line 2"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    value={form.city}
                    onChange={(e) => setForm({ ...form, city: e.target.value })}
                    placeholder="City"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    value={form.state}
                    onChange={(e) =>
                      setForm({ ...form, state: e.target.value })
                    }
                    placeholder="State"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    value={form.postal_code}
                    onChange={(e) =>
                      setForm({ ...form, postal_code: e.target.value })
                    }
                    placeholder="Postal Code"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    value={form.country}
                    onChange={(e) =>
                      setForm({ ...form, country: e.target.value })
                    }
                    placeholder="Country"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-gray-800 pt-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">
                Business Info
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Payment Terms
                  </label>
                  <input
                    type="text"
                    value={form.payment_terms}
                    onChange={(e) =>
                      setForm({ ...form, payment_terms: e.target.value })
                    }
                    placeholder="Net 30, COD, etc."
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">
                    Account Number
                  </label>
                  <input
                    type="text"
                    value={form.account_number}
                    onChange={(e) =>
                      setForm({ ...form, account_number: e.target.value })
                    }
                    placeholder="Our account with them"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Notes</label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={3}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="rounded bg-gray-800 border-gray-700"
              />
              <label htmlFor="is_active" className="text-sm text-gray-300">
                Active
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
              >
                {vendor ? "Save Changes" : "Create Vendor"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PO Modal Component (Create/Edit)
/**
 * Render a modal for creating a new purchase order or editing an existing one.
 *
 * Renders form fields for vendor, dates, financials, tracking/document links, notes,
 * and (when creating a new PO) editable line items with quantity and unit cost.
 *
 * @param {Object} props
 * @param {Object|null} props.po - Existing purchase order to edit; omit or null to create a new PO.
 * @param {Array<Object>} props.vendors - Array of vendor objects used to populate the vendor select.
 * @param {Array<Object>} props.products - Array of product/item objects used to populate line item selects.
 * @param {Function} props.onClose - Callback invoked to close the modal.
 * @param {Function} props.onSave - Callback invoked with the PO payload when the form is submitted.
 *   - For new POs the payload includes `lines` (array of {product_id, quantity_ordered, unit_cost, notes}).
 *   - For edits the payload contains header fields only (vendor_id, order_date, expected_date, tracking_number, carrier, tax_amount, shipping_cost, payment_method, payment_reference, document_url, notes).
 * @returns {JSX.Element} The modal element.
 */

function POModal({ po, vendors, products, onClose, onSave }) {
  const toast = useToast();
  const [form, setForm] = useState({
    vendor_id: po?.vendor_id || "",
    order_date: po?.order_date || "",
    expected_date: po?.expected_date || "",
    tracking_number: po?.tracking_number || "",
    carrier: po?.carrier || "",
    tax_amount: po?.tax_amount || "0",
    shipping_cost: po?.shipping_cost || "0",
    payment_method: po?.payment_method || "",
    payment_reference: po?.payment_reference || "",
    document_url: po?.document_url || "",
    notes: po?.notes || "",
    lines:
      po?.lines?.map((l) => ({
        product_id: l.product_id,
        quantity_ordered: l.quantity_ordered,
        unit_cost: l.unit_cost,
        notes: l.notes || "",
      })) || [],
  });

  const addLine = () => {
    setForm({
      ...form,
      lines: [
        ...form.lines,
        { product_id: "", quantity_ordered: 1, unit_cost: 0, notes: "" },
      ],
    });
  };

  const removeLine = (index) => {
    setForm({
      ...form,
      lines: form.lines.filter((_, i) => i !== index),
    });
  };

  const updateLine = (index, field, value) => {
    const newLines = [...form.lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setForm({ ...form, lines: newLines });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.vendor_id) {
      toast.warning("Please select a vendor");
      return;
    }
    if (!po && form.lines.length === 0) {
      toast.warning("Please add at least one line item");
      return;
    }

    const data = {
      vendor_id: parseInt(form.vendor_id),
      order_date: form.order_date || null,
      expected_date: form.expected_date || null,
      tracking_number: form.tracking_number || null,
      carrier: form.carrier || null,
      tax_amount: parseFloat(form.tax_amount) || 0,
      shipping_cost: parseFloat(form.shipping_cost) || 0,
      payment_method: form.payment_method || null,
      payment_reference: form.payment_reference || null,
      document_url: form.document_url || null,
      notes: form.notes || null,
    };

    if (!po) {
      // New PO - include lines
      data.lines = form.lines.map((l) => ({
        product_id: parseInt(l.product_id),
        quantity_ordered: parseFloat(l.quantity_ordered),
        unit_cost: parseFloat(l.unit_cost),
        notes: l.notes || null,
      }));
    }

    onSave(data);
  };

  const lineTotal = form.lines.reduce(
    (sum, l) =>
      sum +
      (parseFloat(l.quantity_ordered) || 0) * (parseFloat(l.unit_cost) || 0),
    0
  );
  const grandTotal =
    lineTotal +
    (parseFloat(form.tax_amount) || 0) +
    (parseFloat(form.shipping_cost) || 0);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-4xl w-full mx-auto p-6 max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white">
              {po ? `Edit PO ${po.po_number}` : "New Purchase Order"}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
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

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Header Info */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Vendor *
                </label>
                <select
                  value={form.vendor_id}
                  onChange={(e) =>
                    setForm({ ...form, vendor_id: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  required
                >
                  <option value="">Select vendor...</option>
                  {vendors
                    .filter((v) => v.is_active)
                    .map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.code})
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Order Date
                </label>
                <input
                  type="date"
                  value={form.order_date}
                  onChange={(e) =>
                    setForm({ ...form, order_date: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Expected Date
                </label>
                <input
                  type="date"
                  value={form.expected_date}
                  onChange={(e) =>
                    setForm({ ...form, expected_date: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>

            {/* Line Items - only for new POs */}
            {!po && (
              <div className="border-t border-gray-800 pt-4">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-sm font-medium text-gray-300">
                    Line Items
                  </h4>
                  <button
                    type="button"
                    onClick={addLine}
                    className="text-sm text-blue-400 hover:text-blue-300"
                  >
                    + Add Line
                  </button>
                </div>
                <div className="space-y-2">
                  {form.lines.map((line, index) => (
                    <div
                      key={index}
                      className="flex gap-2 items-start bg-gray-800/50 p-3 rounded-lg"
                    >
                      <div className="flex-1">
                        <select
                          value={line.product_id}
                          onChange={(e) =>
                            updateLine(index, "product_id", e.target.value)
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
                          required
                        >
                          <option value="">Select item...</option>
                          {products.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.sku} - {p.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="w-24">
                        <input
                          type="number"
                          value={line.quantity_ordered}
                          onChange={(e) =>
                            updateLine(
                              index,
                              "quantity_ordered",
                              e.target.value
                            )
                          }
                          placeholder="Qty"
                          min="0.01"
                          step="0.01"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
                          required
                        />
                      </div>
                      <div className="w-28">
                        <input
                          type="number"
                          value={line.unit_cost}
                          onChange={(e) =>
                            updateLine(index, "unit_cost", e.target.value)
                          }
                          placeholder="Unit Cost"
                          min="0"
                          step="0.01"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white"
                          required
                        />
                      </div>
                      <div className="w-24 text-right text-sm text-gray-400 py-1">
                        $
                        {(
                          (parseFloat(line.quantity_ordered) || 0) *
                          (parseFloat(line.unit_cost) || 0)
                        ).toFixed(2)}
                      </div>
                      <button
                        type="button"
                        onClick={() => removeLine(index)}
                        className="text-red-400 hover:text-red-300 p-1"
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
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </div>
                  ))}
                  {form.lines.length === 0 && (
                    <p className="text-gray-500 text-sm text-center py-4">
                      No line items. Click "Add Line" to add items.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Financials */}
            <div className="grid grid-cols-4 gap-4 border-t border-gray-800 pt-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Tax Amount
                </label>
                <input
                  type="number"
                  value={form.tax_amount}
                  onChange={(e) =>
                    setForm({ ...form, tax_amount: e.target.value })
                  }
                  min="0"
                  step="0.01"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Shipping Cost
                </label>
                <input
                  type="number"
                  value={form.shipping_cost}
                  onChange={(e) =>
                    setForm({ ...form, shipping_cost: e.target.value })
                  }
                  min="0"
                  step="0.01"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Payment Method
                </label>
                <input
                  type="text"
                  value={form.payment_method}
                  onChange={(e) =>
                    setForm({ ...form, payment_method: e.target.value })
                  }
                  placeholder="Card, Check, etc."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Payment Ref
                </label>
                <input
                  type="text"
                  value={form.payment_reference}
                  onChange={(e) =>
                    setForm({ ...form, payment_reference: e.target.value })
                  }
                  placeholder="Last 4, Check #"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>

            {/* Document & Tracking */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Document URL
                </label>
                <input
                  type="text"
                  value={form.document_url}
                  onChange={(e) =>
                    setForm({ ...form, document_url: e.target.value })
                  }
                  placeholder="Google Drive link, etc."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Tracking Number
                </label>
                <input
                  type="text"
                  value={form.tracking_number}
                  onChange={(e) =>
                    setForm({ ...form, tracking_number: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Carrier
                </label>
                <input
                  type="text"
                  value={form.carrier}
                  onChange={(e) =>
                    setForm({ ...form, carrier: e.target.value })
                  }
                  placeholder="UPS, FedEx, etc."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Notes</label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            {/* Totals */}
            {!po && (
              <div className="bg-gray-800/50 p-4 rounded-lg text-right">
                <div className="text-sm text-gray-400">
                  Subtotal: ${lineTotal.toFixed(2)}
                </div>
                <div className="text-lg font-semibold text-white mt-1">
                  Total: ${grandTotal.toFixed(2)}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
              >
                {po ? "Save Changes" : "Create PO"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// PO Detail Modal Component
// ============================================================================

function PODetailModal({
  po,
  onClose,
  onStatusChange,
  onEdit,
  onReceive,
  onUpload,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setUploading(true);
      await onUpload(file);
      setUploading(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploading(true);
      await onUpload(file);
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-3xl w-full mx-auto p-6 max-h-[90vh] overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">
                {po.po_number}
              </h3>
              <p className="text-sm text-gray-400">{po.vendor_name}</p>
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`px-3 py-1 rounded-full text-sm ${
                  statusColors[po.status]
                }`}
              >
                {po.status}
              </span>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-white"
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
          </div>

          {/* Dates */}
          <div className="grid grid-cols-4 gap-4 mb-6 text-sm">
            <div>
              <span className="text-gray-400">Order Date</span>
              <p className="text-white">
                {po.order_date
                  ? new Date(po.order_date).toLocaleDateString()
                  : "-"}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Expected</span>
              <p className="text-white">
                {po.expected_date
                  ? new Date(po.expected_date).toLocaleDateString()
                  : "-"}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Shipped</span>
              <p className="text-white">
                {po.shipped_date
                  ? new Date(po.shipped_date).toLocaleDateString()
                  : "-"}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Received</span>
              <p className="text-white">
                {po.received_date
                  ? new Date(po.received_date).toLocaleDateString()
                  : "-"}
              </p>
            </div>
          </div>

          {/* Tracking */}
          {(po.tracking_number || po.carrier) && (
            <div className="bg-gray-800/50 p-3 rounded-lg mb-6 text-sm">
              <span className="text-gray-400">Tracking: </span>
              <span className="text-white">
                {po.carrier} {po.tracking_number}
              </span>
            </div>
          )}

          {/* Lines */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-300 mb-3">
              Line Items
            </h4>
            <div className="bg-gray-800/30 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="text-left py-2 px-3 text-xs text-gray-400">
                      #
                    </th>
                    <th className="text-left py-2 px-3 text-xs text-gray-400">
                      Item
                    </th>
                    <th className="text-right py-2 px-3 text-xs text-gray-400">
                      Ordered
                    </th>
                    <th className="text-right py-2 px-3 text-xs text-gray-400">
                      Received
                    </th>
                    <th className="text-right py-2 px-3 text-xs text-gray-400">
                      Unit Cost
                    </th>
                    <th className="text-right py-2 px-3 text-xs text-gray-400">
                      Total
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {po.lines?.map((line) => (
                    <tr key={line.id} className="border-t border-gray-800">
                      <td className="py-2 px-3 text-gray-400">
                        {line.line_number}
                      </td>
                      <td className="py-2 px-3">
                        <div className="text-white">{line.product_sku}</div>
                        <div className="text-xs text-gray-400">
                          {line.product_name}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-right text-white">
                        {parseFloat(line.quantity_ordered).toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span
                          className={
                            parseFloat(line.quantity_received) >=
                            parseFloat(line.quantity_ordered)
                              ? "text-green-400"
                              : "text-yellow-400"
                          }
                        >
                          {parseFloat(line.quantity_received).toFixed(2)}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right text-gray-400">
                        ${parseFloat(line.unit_cost).toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right text-white">
                        ${parseFloat(line.line_total).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals */}
          <div className="text-right text-sm mb-6">
            <div className="text-gray-400">
              Subtotal: ${parseFloat(po.subtotal || 0).toFixed(2)}
            </div>
            <div className="text-gray-400">
              Tax: ${parseFloat(po.tax_amount || 0).toFixed(2)}
            </div>
            <div className="text-gray-400">
              Shipping: ${parseFloat(po.shipping_cost || 0).toFixed(2)}
            </div>
            <div className="text-lg font-semibold text-white mt-1">
              Total: ${parseFloat(po.total_amount || 0).toFixed(2)}
            </div>
          </div>

          {/* Document Upload / Link */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-300 mb-3">Document</h4>
            {po.document_url ? (
              <div className="flex items-center gap-4">
                <a
                  href={po.document_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-2"
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
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  View Document
                </a>
                <label className="text-gray-400 hover:text-white text-sm cursor-pointer">
                  Replace
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </label>
              </div>
            ) : (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                  isDragging
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-gray-700 hover:border-gray-600"
                }`}
              >
                {uploading ? (
                  <div className="flex items-center justify-center gap-2 text-gray-400">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                    Uploading...
                  </div>
                ) : (
                  <>
                    <svg
                      className="w-8 h-8 mx-auto mb-2 text-gray-500"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    <p className="text-sm text-gray-400 mb-2">
                      Drag & drop invoice/receipt here
                    </p>
                    <label className="text-sm text-blue-400 hover:text-blue-300 cursor-pointer">
                      or click to browse
                      <input
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,.xlsx,.csv"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                    </label>
                    <p className="text-xs text-gray-500 mt-2">
                      PDF, Images, Excel, CSV
                    </p>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Notes */}
          {po.notes && (
            <div className="bg-gray-800/30 p-3 rounded-lg mb-6">
              <span className="text-sm text-gray-400">Notes: </span>
              <span className="text-sm text-white">{po.notes}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-between items-center pt-4 border-t border-gray-800">
            <div className="flex gap-2">
              {po.status === "draft" && (
                <>
                  <button
                    onClick={onEdit}
                    className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-white"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => onStatusChange(po.id, "ordered")}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white"
                  >
                    Place Order
                  </button>
                </>
              )}
              {po.status === "ordered" && (
                <>
                  <button
                    onClick={() => onStatusChange(po.id, "shipped")}
                    className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm text-white"
                  >
                    Mark Shipped
                  </button>
                  <button
                    onClick={onReceive}
                    className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-sm text-white"
                  >
                    Receive Items
                  </button>
                </>
              )}
              {po.status === "shipped" && (
                <button
                  onClick={onReceive}
                  className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-sm text-white"
                >
                  Receive Items
                </button>
              )}
              {po.status === "received" && (
                <button
                  onClick={() => onStatusChange(po.id, "closed")}
                  className="px-3 py-1.5 bg-gray-600 hover:bg-gray-700 rounded-lg text-sm text-white"
                >
                  Close PO
                </button>
              )}
              {!["received", "closed", "cancelled"].includes(po.status) && (
                <button
                  onClick={() => onStatusChange(po.id, "cancelled")}
                  className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/30 rounded-lg text-sm text-red-400"
                >
                  Cancel
                </button>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Receive Modal Component
/**
 * Render a modal to record received quantities for a purchase order.
 *
 * Displays inputs for each PO line that has remaining quantity to receive, lets the user enter
 * quantity_received, lot_number, and notes per line, and submits a consolidated receive payload
 * to the provided onReceive handler.
 *
 * @param {Object} props
 * @param {Object} props.po - Purchase order object; must include `po_number` and `lines` where each line contains `id`, `product_sku`, `product_name`, `quantity_ordered`, and `quantity_received`.
 * @param {function} props.onClose - Invoked when the modal is dismissed without submitting.
 * @param {function} props.onReceive - Invoked with the receive payload when at least one line has quantity > 0.
 * @returns {JSX.Element} The receive modal element.
 *
 * @example
 * // receiveData shape passed to onReceive:
 * // {
 * //   lines: [
 * //     { line_id: 123, quantity_received: 5.0, lot_number: "LN001" | null, notes: "..." | null },
 * //     ...
 * //   ],
 * //   notes: "Overall receipt notes" | null
 * // }
 */

function ReceiveModal({ po, onClose, onReceive }) {
  const toast = useToast();
  const [lines, setLines] = useState(
    po.lines
      ?.filter(
        (l) => parseFloat(l.quantity_received) < parseFloat(l.quantity_ordered)
      )
      .map((l) => ({
        line_id: l.id,
        quantity_received:
          parseFloat(l.quantity_ordered) - parseFloat(l.quantity_received),
        remaining:
          parseFloat(l.quantity_ordered) - parseFloat(l.quantity_received),
        product_sku: l.product_sku,
        product_name: l.product_name,
        lot_number: "",
        notes: "",
      })) || []
  );
  const [notes, setNotes] = useState("");

  const updateLine = (index, field, value) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setLines(newLines);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const receiveData = {
      lines: lines
        .filter((l) => parseFloat(l.quantity_received) > 0)
        .map((l) => ({
          line_id: l.line_id,
          quantity_received: parseFloat(l.quantity_received),
          lot_number: l.lot_number || null,
          notes: l.notes || null,
        })),
      notes: notes || null,
    };

    if (receiveData.lines.length === 0) {
      toast.warning("Please enter quantities to receive");
      return;
    }

    onReceive(receiveData);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-3xl w-full mx-auto p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Receive Items - {po.po_number}
              </h3>
              <p className="text-sm text-gray-400">Enter quantities received</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
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

          <form onSubmit={handleSubmit} className="space-y-4">
            {lines.length === 0 ? (
              <p className="text-gray-400 text-center py-8">
                All items have been received
              </p>
            ) : (
              <div className="space-y-3">
                {lines.map((line, index) => (
                  <div
                    key={line.line_id}
                    className="bg-gray-800/50 p-4 rounded-lg"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <div className="text-white font-medium">
                          {line.product_sku}
                        </div>
                        <div className="text-sm text-gray-400">
                          {line.product_name}
                        </div>
                      </div>
                      <div className="text-sm text-gray-400">
                        Remaining: {line.remaining}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">
                          Qty to Receive
                        </label>
                        <input
                          type="number"
                          value={line.quantity_received}
                          onChange={(e) =>
                            updateLine(
                              index,
                              "quantity_received",
                              e.target.value
                            )
                          }
                          min="0"
                          max={line.remaining}
                          step="0.01"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">
                          Lot Number
                        </label>
                        <input
                          type="text"
                          value={line.lot_number}
                          onChange={(e) =>
                            updateLine(index, "lot_number", e.target.value)
                          }
                          placeholder="Optional"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">
                          Notes
                        </label>
                        <input
                          type="text"
                          value={line.notes}
                          onChange={(e) =>
                            updateLine(index, "notes", e.target.value)
                          }
                          placeholder="Optional"
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-white"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Receipt Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Optional notes for this receipt"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={lines.length === 0}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white font-medium"
              >
                Receive Items
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}