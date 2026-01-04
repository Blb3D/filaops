import { useState, useEffect, useRef, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";
import VendorModal from "../../components/purchasing/VendorModal";
import VendorDetailPanel from "../../components/purchasing/VendorDetailPanel";
import POCreateModal from "../../components/purchasing/POCreateModal";
import PODetailModal from "../../components/purchasing/PODetailModal";
import ReceiveModal from "../../components/purchasing/ReceiveModal";
import QuickBooksExportModal from "../../components/purchasing/QuickBooksExportModal";
import InvoiceUploadModal from "../../components/purchasing/InvoiceUploadModal";
import InvoiceReviewModal from "../../components/purchasing/InvoiceReviewModal";

// Purchasing Trend Chart Component
function PurchasingChart({ data, period, onPeriodChange, loading }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [chartWidth, setChartWidth] = useState(300);
  const chartRef = useRef(null);

  const parseLocalDate = (dateStr) => {
    if (!dateStr) return null;
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day);
  };

  const formatDateKey = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  const fillDateRange = (rawData, startDate, endDate) => {
    if (!startDate || !endDate) return rawData || [];
    const dataMap = {};
    (rawData || []).forEach(d => { dataMap[d.date] = d; });
    const start = parseLocalDate(startDate.split('T')[0]);
    const end = parseLocalDate(endDate.split('T')[0]);
    if (!start || !end) return rawData || [];
    const filledData = [];
    const current = new Date(start);
    while (current <= end) {
      const dateKey = formatDateKey(current);
      filledData.push(dataMap[dateKey] || { date: dateKey, received: 0, spend: 0 });
      current.setDate(current.getDate() + 1);
    }
    return filledData;
  };

  const periods = [
    { key: "WTD", label: "Week" },
    { key: "MTD", label: "Month" },
    { key: "QTD", label: "Quarter" },
    { key: "YTD", label: "Year" },
  ];

  const chartHeight = 100;

  if (loading) {
    return (
      <div className="h-32 flex items-center justify-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  const dataPoints = fillDateRange(data?.data, data?.start_date, data?.end_date);

  const cumulativeData = dataPoints.reduce((acc, d) => {
    const prev = acc[acc.length - 1] || { cumulativeSpend: 0, cumulativeReceived: 0 };
    acc.push({
      ...d,
      cumulativeSpend: prev.cumulativeSpend + (d.spend || 0),
      cumulativeReceived: prev.cumulativeReceived + (d.received || 0),
    });
    return acc;
  }, []);

  const maxCumulativeSpend = cumulativeData.length > 0 ? cumulativeData[cumulativeData.length - 1].cumulativeSpend : 1;
  const maxDailyReceived = Math.max(...dataPoints.map(d => d.received || 0), 1);

  const generateSpendPath = () => {
    if (cumulativeData.length === 0) return "";
    const points = cumulativeData.map((d, i) => {
      const x = (i / Math.max(cumulativeData.length - 1, 1)) * 100;
      const y = 100 - (d.cumulativeSpend / Math.max(maxCumulativeSpend, 1)) * 100;
      return `${x},${y}`;
    });
    return `M ${points.join(" L ")}`;
  };

  const formatCurrency = (value) => {
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
    return `$${value.toFixed(0)}`;
  };

  const handleMouseMove = (e, index) => {
    if (chartRef.current) {
      const rect = chartRef.current.getBoundingClientRect();
      setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      setChartWidth(chartRef.current.offsetWidth);
    }
    setHoveredIndex(index);
  };

  const getHoveredData = () => {
    if (hoveredIndex === null || !cumulativeData[hoveredIndex]) return null;
    const d = cumulativeData[hoveredIndex];
    const localDate = parseLocalDate(d.date);
    return {
      date: localDate ? localDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
      received: d.received || 0,
      dailySpend: d.spend || 0,
      cumulativeReceived: d.cumulativeReceived,
      cumulativeSpend: d.cumulativeSpend,
    };
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1">
          {periods.map((p) => (
            <button
              key={p.key}
              onClick={() => onPeriodChange(p.key)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                period === p.key ? "bg-orange-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <p className="text-sm font-semibold text-orange-400">{data?.total_received || 0}</p>
            <p className="text-xs text-gray-500">POs received</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-green-400">{formatCurrency(data?.total_spend || 0)}</p>
            <p className="text-xs text-gray-500">spend</p>
          </div>
          {(data?.pipeline_ordered > 0) && (
            <div>
              <p className="text-sm font-semibold text-yellow-400">{data?.pipeline_ordered || 0}</p>
              <p className="text-xs text-gray-500">pending</p>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-4 mb-2 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-2 h-3 bg-orange-500/30 rounded-sm"></div>
          <span className="text-gray-500">Daily Received</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-green-500"></div>
          <span className="text-gray-400">Cumulative Spend</span>
        </div>
      </div>

      {dataPoints.length > 0 ? (
        <div ref={chartRef} className="relative" style={{ height: chartHeight }} onMouseLeave={() => setHoveredIndex(null)}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
            <line x1="0" y1="50" x2="100" y2="50" stroke="#374151" strokeWidth="0.5" />
            {dataPoints.map((d, i) => {
              const barWidth = 100 / Math.max(dataPoints.length, 1) * 0.6;
              const x = (i / Math.max(dataPoints.length - 1, 1)) * 100 - barWidth / 2;
              const barHeight = ((d.received || 0) / maxDailyReceived) * 100;
              return (
                <rect key={`bar-${i}`} x={Math.max(0, x)} y={100 - barHeight} width={barWidth} height={barHeight} fill="url(#purchasingBarGradient)" opacity="0.4" />
              );
            })}
            <path d={generateSpendPath()} fill="none" stroke="#22c55e" strokeWidth="2" vectorEffect="non-scaling-stroke" />
            {dataPoints.map((_, i) => {
              const sliceWidth = 100 / dataPoints.length;
              return <rect key={`hover-${i}`} x={i * sliceWidth} y={0} width={sliceWidth} height={100} fill="transparent" onMouseMove={(e) => handleMouseMove(e, i)} style={{ cursor: 'crosshair' }} />;
            })}
            {hoveredIndex !== null && cumulativeData[hoveredIndex] && (
              <circle cx={(hoveredIndex / Math.max(cumulativeData.length - 1, 1)) * 100} cy={100 - (cumulativeData[hoveredIndex].cumulativeSpend / Math.max(maxCumulativeSpend, 1)) * 100} r="3" fill="#22c55e" stroke="white" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            )}
            <defs>
              <linearGradient id="purchasingBarGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#f97316" />
                <stop offset="100%" stopColor="#f97316" stopOpacity="0.2" />
              </linearGradient>
            </defs>
          </svg>
          {hoveredIndex !== null && getHoveredData() && (
            <div className="absolute z-10 bg-gray-800 border border-gray-700 rounded-lg shadow-lg p-3 pointer-events-none" style={{ left: Math.min(mousePos.x + 10, chartWidth - 150), top: Math.max(mousePos.y - 70, 0), minWidth: '140px' }}>
              {(() => {
                const d = getHoveredData();
                return (
                  <>
                    <div className="text-white font-medium text-sm mb-2">{d.date}</div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between gap-4"><span className="text-orange-400">Received:</span><span className="text-white font-medium">{d.received}</span></div>
                      <div className="flex justify-between gap-4"><span className="text-green-400">Spend:</span><span className="text-white">${d.dailySpend.toFixed(2)}</span></div>
                      <div className="border-t border-gray-700 my-1 pt-1">
                        <div className="flex justify-between gap-4"><span className="text-gray-400">Total POs:</span><span className="text-white">{d.cumulativeReceived}</span></div>
                        <div className="flex justify-between gap-4"><span className="text-gray-400">Total Spend:</span><span className="text-white">${d.cumulativeSpend.toFixed(2)}</span></div>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </div>
      ) : (
        <div className="h-24 flex items-center justify-center text-gray-500 text-sm">No POs received for this period</div>
      )}

      {dataPoints.length > 0 && (
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>{dataPoints[0]?.date ? parseLocalDate(dataPoints[0].date)?.toLocaleDateString() : ""}</span>
          <span>{dataPoints[dataPoints.length - 1]?.date ? parseLocalDate(dataPoints[dataPoints.length - 1].date)?.toLocaleDateString() : ""}</span>
        </div>
      )}
    </div>
  );
}

// Alias for backward compatibility with existing code
const POModal = POCreateModal;

const statusColors = {
  draft: "bg-gray-500/20 text-gray-400",
  ordered: "bg-blue-500/20 text-blue-400",
  shipped: "bg-purple-500/20 text-purple-400",
  received: "bg-green-500/20 text-green-400",
  closed: "bg-green-700/20 text-green-300",
  cancelled: "bg-red-500/20 text-red-400",
};

export default function AdminPurchasing() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "orders";
  const [activeTab, setActiveTab] = useState(initialTab); // orders | vendors | import | low-stock

  // Initial items for PO modal (from URL params)
  const [initialItemsForPO, setInitialItemsForPO] = useState([]);

  // Track if we've already processed the create_po URL param
  const createPOProcessedRef = useRef(false);

  // Sync tab with URL
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

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
  const [selectedLowStockIds, setSelectedLowStockIds] = useState(new Set());

  // QuickBooks Export Modal
  const [showQBExportModal, setShowQBExportModal] = useState(false);

  // Invoice Import Modals
  const [showInvoiceUpload, setShowInvoiceUpload] = useState(false);
  const [showInvoiceReview, setShowInvoiceReview] = useState(false);
  const [parsedInvoice, setParsedInvoice] = useState(null);
  const [invoiceFile, setInvoiceFile] = useState(null);

  // Company Settings (for auto-calc tax)
  const [companySettings, setCompanySettings] = useState(null);

  // Modals
  const [showVendorModal, setShowVendorModal] = useState(false);
  const [showVendorDetail, setShowVendorDetail] = useState(false);
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

  // Trend chart state
  const [purchasingTrend, setPurchasingTrend] = useState(null);
  const [trendPeriod, setTrendPeriod] = useState("MTD");
  const [trendLoading, setTrendLoading] = useState(false);

  const token = localStorage.getItem("adminToken");

  // Handle create_po URL param - auto-open PO modal with pre-filled item
  useEffect(() => {
    const createPO = searchParams.get("create_po");
    const productId = searchParams.get("product_id");
    const quantity = searchParams.get("quantity");

    // Only process if we have the create_po flag and product_id
    if (createPO !== "true" || !productId) {
      // Reset the ref when there's no create_po param
      createPOProcessedRef.current = false;
      return;
    }

    // Don't process again if we've already handled this
    if (createPOProcessedRef.current) {
      return;
    }

    // Wait for products to load
    if (products.length === 0) {
      console.log("[AdminPurchasing] Waiting for products to load...");
      return;
    }

    // Mark as processed BEFORE doing anything else
    createPOProcessedRef.current = true;

    console.log(`[AdminPurchasing] Looking for product ID: ${productId} in ${products.length} products`);

    // Find the product in the products list
    const product = products.find(p => String(p.id) === String(productId));

    if (product) {
      console.log(`[AdminPurchasing] Found product: ${product.sku}`);

      // Build initial items for the PO modal
      const initialItems = [{
        id: product.id,
        sku: product.sku,
        name: product.name,
        unit: product.unit || "EA",
        shortfall: quantity ? parseFloat(quantity) : 1,
        last_cost: product.last_cost || product.cost || 0,
      }];

      setInitialItemsForPO(initialItems);
      setSelectedPO(null);
      setShowPOModal(true);

      // Ensure we're on the orders tab
      setActiveTab("orders");

      toast.info(`Creating PO for ${product.sku}`);
    } else {
      console.warn(`[AdminPurchasing] Product ID ${productId} not found in products list`);
      toast.warning(`Product not found. Opening empty PO form.`);

      // Still open the modal but without pre-filled data
      setSelectedPO(null);
      setShowPOModal(true);
      setActiveTab("orders");
    }

    // Clear the URL params after processing
    const newParams = new URLSearchParams(searchParams);
    newParams.delete("create_po");
    newParams.delete("product_id");
    newParams.delete("quantity");
    setSearchParams(newParams, { replace: true });
  }, [searchParams, products, setSearchParams, toast]);

  // Build shortage map from lowStockItems for PO modal product enhancement
  // This includes both reorder point shortages and MRP-driven shortages
  const shortageMap = useMemo(() => {
    const map = {};
    lowStockItems.forEach(item => {
      map[item.id] = {
        needs_reorder: true,
        shortfall: item.shortfall,
        mrp_shortage: item.mrp_shortage,
        shortage_source: item.shortage_source, // "reorder_point", "mrp", or "both"
      };
    });
    return map;
  }, [lowStockItems]);

  // Enhanced products with shortage data merged in
  // This allows the PO modal to show MRP shortages, not just reorder point items
  const enhancedProducts = useMemo(() => {
    return products.map(product => {
      const shortage = shortageMap[product.id];
      if (shortage) {
        return { ...product, ...shortage };
      }
      return product;
    });
  }, [products, shortageMap]);

  // Group selected low-stock items by vendor for bulk PO creation
  const selectedItemsByVendor = useMemo(() => {
    const grouped = {};
    lowStockItems
      .filter(item => selectedLowStockIds.has(item.id))
      .forEach(item => {
        const vendorId = item.preferred_vendor_id || 'no_vendor';
        const vendorName = item.preferred_vendor_name || 'No Preferred Vendor';
        if (!grouped[vendorId]) {
          grouped[vendorId] = {
            vendorId: vendorId === 'no_vendor' ? null : vendorId,
            vendorName,
            items: [],
            totalValue: 0,
          };
        }
        grouped[vendorId].items.push(item);
        grouped[vendorId].totalValue += (item.shortfall || 0) * (item.last_cost || 0);
      });
    return Object.values(grouped);
  }, [lowStockItems, selectedLowStockIds]);

  // Low stock checkbox handlers
  const toggleLowStockItem = (itemId) => {
    setSelectedLowStockIds(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  const toggleAllLowStock = () => {
    if (selectedLowStockIds.size === lowStockItems.length) {
      setSelectedLowStockIds(new Set());
    } else {
      setSelectedLowStockIds(new Set(lowStockItems.map(i => i.id)));
    }
  };

  const clearLowStockSelection = () => {
    setSelectedLowStockIds(new Set());
  };

  const fetchPurchasingTrend = async (period) => {
    if (!token) return;
    setTrendLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/dashboard/purchasing-trend?period=${period}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setPurchasingTrend(data);
      } else {
        console.error("Purchasing trend API error:", res.status);
      }
    } catch (err) {
      console.error("Failed to fetch purchasing trend:", err);
    } finally {
      setTrendLoading(false);
    }
  };

  useEffect(() => {
    fetchPurchasingTrend(trendPeriod);
  }, [trendPeriod]);

  useEffect(() => {
    if (activeTab === "orders") fetchOrders();
    else if (activeTab === "vendors") fetchVendors();
    else if (activeTab === "low-stock") fetchLowStock();
    // Import tab doesn't need data fetching on mount
    fetchProducts();
  }, [activeTab, filters.status]);

  // Fetch vendors, low stock count, and company settings on mount
  useEffect(() => {
    fetchVendors(false); // Silent fetch - don't show loading spinner
    fetchLowStock();
    fetchCompanySettings();
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
      const data = await res.json();
      // Handle both array and {items: [...]} responses, and error objects
      setOrders(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      setError(err.message);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchVendors = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/vendors?active_only=false`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch vendors");
      const data = await res.json();
      // Handle both array and {items: [...]} responses, and error objects
      setVendors(Array.isArray(data) ? data : (data.items || []));
    } catch (err) {
      if (showLoading) setError(err.message);
      setVendors([]);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/items?limit=2000`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        console.log(`[AdminPurchasing] Loaded ${data.items?.length || 0} products`);
        setProducts(data.items || []);
      } else {
        console.warn(`[AdminPurchasing] Failed to fetch products: ${res.status}`);
      }
    } catch (err) {
      // Products fetch failure is non-critical - product selector will just be empty
      console.error("[AdminPurchasing] Error fetching products:", err);
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
    } catch {
      setError("Failed to load low stock items. Please refresh the page.");
    } finally {
      setLowStockLoading(false);
    }
  };

  const fetchCompanySettings = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/settings/company`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCompanySettings(data);
      }
    } catch (err) {
      // Non-critical - auto-calc tax just won't work
      console.error("Failed to fetch company settings:", err);
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
      // Refresh products and low stock data to update inventory levels
      fetchProducts();
      fetchLowStock();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // handleFileUpload removed - file uploads are now handled via DocumentUploadPanel

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

  // Create PO from selected low-stock items for a specific vendor
  const handleCreatePOFromSelection = async (vendorGroup) => {
    if (!vendorGroup.vendorId) {
      toast.warning("Items without a preferred vendor cannot be bulk-ordered. Please set preferred vendors first.");
      return;
    }

    // Build initial items for PO modal
    const initialItems = vendorGroup.items.map(item => ({
      id: item.id,
      sku: item.sku,
      name: item.name,
      unit: item.unit || "EA",
      shortfall: item.reorder_quantity || item.shortfall || 1,
      last_cost: item.last_cost || 0,
    }));

    // Set initial items and open PO modal
    setInitialItemsForPO(initialItems);
    setSelectedPO(null);

    // Ensure company settings are loaded
    if (!companySettings) {
      await fetchCompanySettings();
    }

    setShowPOModal(true);
    setActiveTab("orders");

    // Clear selection after creating PO
    clearLowStockSelection();

    toast.info(`Creating PO for ${vendorGroup.vendorName} with ${initialItems.length} items`);
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
            <>
              <button
                onClick={() => setShowInvoiceUpload(true)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white font-medium flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Import Invoice
              </button>
              <button
                onClick={async () => {
                  setSelectedPO(null);
                  // Ensure company settings are loaded for auto-calc tax
                  if (!companySettings) {
                    await fetchCompanySettings();
                  }
                  setShowPOModal(true);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium"
              >
                + New PO
              </button>
            </>
          )}
        </div>
      </div>

      {/* Purchasing Trend Chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <PurchasingChart
          data={purchasingTrend}
          period={trendPeriod}
          onPeriodChange={setTrendPeriod}
          loading={trendLoading}
        />
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

      {/* Loading - only show for orders and vendors tabs */}
      {loading && (activeTab === "orders" || activeTab === "vendors") && (
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
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Received
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
                      ? new Date(po.order_date + "T00:00:00").toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {po.expected_date
                      ? new Date(po.expected_date + "T00:00:00").toLocaleDateString()
                      : "-"}
                  </td>
                  <td className="py-3 px-4 text-gray-400">
                    {po.received_date
                      ? new Date(po.received_date + "T00:00:00").toLocaleDateString()
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
                  <td colSpan={9} className="py-12 text-center text-gray-500">
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
                  className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer"
                  onClick={() => {
                    setSelectedVendor(vendor);
                    setShowVendorDetail(true);
                  }}
                >
                  <td className="py-3 px-4 text-white font-medium">
                    {vendor.code}
                  </td>
                  <td className="py-3 px-4 text-blue-400 hover:text-blue-300">
                    {vendor.name}
                  </td>
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
                  <td className="py-3 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => {
                        setSelectedVendor(vendor);
                        setShowVendorDetail(true);
                      }}
                      className="text-gray-400 hover:text-white text-sm"
                    >
                      View
                    </button>
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
          {/* Enhanced Summary Cards */}
          {lowStockSummary && (
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="text-3xl font-bold text-red-400">
                  {lowStockSummary.critical_count || 0}
                </div>
                <div className="text-sm text-gray-400">Critical (Out of Stock)</div>
              </div>
              <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4">
                <div className="text-3xl font-bold text-orange-400">
                  {lowStockSummary.urgent_count || 0}
                </div>
                <div className="text-sm text-gray-400">Urgent (&lt;50% Reorder)</div>
              </div>
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                <div className="text-3xl font-bold text-yellow-400">
                  {lowStockSummary.low_count || 0}
                </div>
                <div className="text-sm text-gray-400">Low Stock</div>
              </div>
              <div className="bg-gray-700/30 border border-gray-600 rounded-xl p-4">
                <div className="text-3xl font-bold text-white">
                  ${lowStockSummary.total_shortfall_value?.toFixed(0) || "0"}
                </div>
                <div className="text-sm text-gray-400">Shortfall Value</div>
              </div>
            </div>
          )}

          {/* MRP Shortage Alert */}
          {lowStockSummary?.mrp_shortage_count > 0 && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex items-center gap-3">
              <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-blue-300 text-sm">
                <strong>{lowStockSummary.mrp_shortage_count}</strong> items have MRP-driven shortages from active sales orders
              </span>
            </div>
          )}

          {/* Low Stock Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Items Requiring Attention
                </h3>
                <p className="text-sm text-gray-400 mt-0.5">
                  {lowStockItems.length} items below reorder point or with MRP shortages
                  {selectedLowStockIds.size > 0 && (
                    <span className="ml-2 text-blue-400">({selectedLowStockIds.size} selected)</span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {/* QuickBooks Export Button */}
                <button
                  onClick={() => setShowQBExportModal(true)}
                  className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-sm text-white flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Export to QB
                </button>

                {/* Create PO Dropdown - shows when items are selected */}
                {selectedLowStockIds.size > 0 && selectedItemsByVendor.length > 0 && (
                  <div className="relative group">
                    <button className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      Create PO ({selectedLowStockIds.size})
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    <div className="absolute right-0 mt-1 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                      {selectedItemsByVendor.map((group) => (
                        <button
                          key={group.vendorId || 'no_vendor'}
                          onClick={() => handleCreatePOFromSelection(group)}
                          disabled={!group.vendorId}
                          className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-700 first:rounded-t-lg last:rounded-b-lg ${
                            !group.vendorId ? 'text-gray-500 cursor-not-allowed' : 'text-white'
                          }`}
                        >
                          <div className="font-medium">{group.vendorName}</div>
                          <div className="text-xs text-gray-400">
                            {group.items.length} items · ${group.totalValue.toFixed(2)}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Clear Selection */}
                {selectedLowStockIds.size > 0 && (
                  <button
                    onClick={clearLowStockSelection}
                    className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-300"
                  >
                    Clear
                  </button>
                )}

                <button
                  onClick={fetchLowStock}
                  disabled={lowStockLoading}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 flex items-center gap-2"
                >
                  <svg className={`w-4 h-4 ${lowStockLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  {lowStockLoading ? "Refreshing..." : "Refresh"}
                </button>
              </div>
            </div>

            {lowStockLoading ? (
              <div className="p-8 text-center text-gray-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3"></div>
                Loading low stock items...
              </div>
            ) : lowStockItems.length === 0 ? (
              <div className="p-12 text-center">
                <svg className="w-16 h-16 mx-auto text-green-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
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
                    <th className="text-center py-3 px-2 text-xs font-medium text-gray-400 uppercase w-10">
                      <input
                        type="checkbox"
                        checked={lowStockItems.length > 0 && selectedLowStockIds.size === lowStockItems.length}
                        onChange={toggleAllLowStock}
                        className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
                      />
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                      Urgency
                    </th>
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
                  {lowStockItems.map((item) => {
                    // Determine urgency level
                    const isCritical = item.available_qty <= 0;
                    const isUrgent = !isCritical && item.reorder_point && item.available_qty <= item.reorder_point * 0.5;
                    const hasMrpShortage = item.mrp_shortage > 0;

                    return (
                      <tr
                        key={item.id}
                        className={`border-b border-gray-800 hover:bg-gray-800/30 ${
                          isCritical ? 'bg-red-500/5' : isUrgent ? 'bg-orange-500/5' : ''
                        } ${selectedLowStockIds.has(item.id) ? 'bg-blue-500/10' : ''}`}
                      >
                        <td className="py-3 px-2 text-center">
                          <input
                            type="checkbox"
                            checked={selectedLowStockIds.has(item.id)}
                            onChange={() => toggleLowStockItem(item.id)}
                            className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900"
                          />
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            {isCritical && (
                              <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs font-medium">
                                CRITICAL
                              </span>
                            )}
                            {isUrgent && (
                              <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 rounded text-xs font-medium">
                                URGENT
                              </span>
                            )}
                            {!isCritical && !isUrgent && (
                              <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs font-medium">
                                LOW
                              </span>
                            )}
                            {hasMrpShortage && (
                              <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs" title="MRP shortage from active orders">
                                MRP
                              </span>
                            )}
                          </div>
                        </td>
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
                              isCritical
                                ? "text-red-400 font-medium"
                                : isUrgent
                                ? "text-orange-400"
                                : "text-yellow-400"
                            }
                          >
                            {item.available_qty?.toFixed(2)} {item.unit}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right text-gray-400">
                          {item.reorder_point?.toFixed(2) || "-"} {item.unit}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-red-400 font-medium">
                            -{item.shortfall?.toFixed(2)} {item.unit}
                          </span>
                          {item.mrp_shortage > 0 && item.shortage_source === "mrp" && (
                            <div className="text-xs text-blue-400 mt-1">
                              (MRP: {item.mrp_shortage.toFixed(2)})
                            </div>
                          )}
                          {item.mrp_shortage > 0 && item.shortage_source === "both" && (
                            <div className="text-xs text-purple-400 mt-1">
                              +MRP: {item.mrp_shortage.toFixed(2)}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={async () => {
                                setSelectedPO(null);
                                if (!companySettings) {
                                  await fetchCompanySettings();
                                }
                                setShowPOModal(true);
                                // TODO: Pre-populate with this item
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
                    );
                  })}
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

      {/* Vendor Detail Panel */}
      {showVendorDetail && selectedVendor && (
        <VendorDetailPanel
          vendor={selectedVendor}
          onClose={() => {
            setShowVendorDetail(false);
            setSelectedVendor(null);
          }}
          onEdit={(vendor) => {
            setShowVendorDetail(false);
            setSelectedVendor(vendor);
            setShowVendorModal(true);
          }}
          onCreatePO={async () => {
            setShowVendorDetail(false);
            // Pre-select the vendor for the new PO
            setSelectedPO(null);
            if (!companySettings) {
              await fetchCompanySettings();
            }
            setShowPOModal(true);
            // TODO: POCreateModal could accept preselectedVendorId prop
          }}
          onViewPO={async (poId) => {
            setShowVendorDetail(false);
            await fetchPODetails(poId);
          }}
        />
      )}

      {/* PO Modal */}
      {showPOModal && (
        <POModal
          po={selectedPO}
          vendors={vendors}
          products={enhancedProducts}
          companySettings={companySettings}
          initialItems={initialItemsForPO}
          onClose={() => {
            setShowPOModal(false);
            setSelectedPO(null);
            setInitialItemsForPO([]); // Clear initial items when closing
          }}
          onSave={handleSavePO}
          onProductsRefresh={fetchProducts}
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

      {/* QuickBooks Export Modal */}
      {showQBExportModal && (
        <QuickBooksExportModal
          isOpen={showQBExportModal}
          onClose={() => setShowQBExportModal(false)}
        />
      )}

      {/* Invoice Upload Modal */}
      {showInvoiceUpload && (
        <InvoiceUploadModal
          vendors={vendors}
          onClose={() => setShowInvoiceUpload(false)}
          onParsed={(parsed, file) => {
            setParsedInvoice(parsed);
            setInvoiceFile(file);
            setShowInvoiceUpload(false);
            setShowInvoiceReview(true);
          }}
        />
      )}

      {/* Invoice Review Modal */}
      {showInvoiceReview && parsedInvoice && (
        <InvoiceReviewModal
          parsedInvoice={parsedInvoice}
          originalFile={invoiceFile}
          vendors={vendors}
          products={products}
          onClose={() => {
            setShowInvoiceReview(false);
            setParsedInvoice(null);
            setInvoiceFile(null);
          }}
          onSuccess={(createdPO) => {
            setShowInvoiceReview(false);
            setParsedInvoice(null);
            setInvoiceFile(null);
            toast.success(`Created PO ${createdPO.po_number}`);
            fetchOrders(); // Refresh the PO list
          }}
        />
      )}
    </div>
  );
}
