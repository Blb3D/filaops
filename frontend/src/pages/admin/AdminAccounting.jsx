/* eslint-disable react-hooks/exhaustive-deps */
import { useState, useEffect } from "react";
import { API_URL } from "../../config/api";
import { useFeatureFlags } from "../../hooks/useFeatureFlags";
import { useToast } from "../../components/Toast";

// =============================================================================
// SHARED COMPONENTS
// =============================================================================

// Reusable error alert with retry button
function ErrorAlert({ message, onRetry }) {
  return (
    <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 flex items-center gap-3">
      <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div className="flex-1">
        <p className="text-red-400 font-medium text-sm">{message}</p>
        <p className="text-gray-500 text-xs mt-1">Check that the backend server is running.</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 text-sm flex items-center gap-1.5"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Retry
        </button>
      )}
    </div>
  );
}

// Skeleton loading placeholder
function Skeleton({ className = "", variant = "rect" }) {
  const baseClass = "animate-pulse bg-gray-700/50 rounded";
  if (variant === "text") {
    return <div className={`${baseClass} h-4 ${className}`} />;
  }
  if (variant === "circle") {
    return <div className={`${baseClass} rounded-full ${className}`} />;
  }
  return <div className={`${baseClass} ${className}`} />;
}

// Table skeleton for loading states
function TableSkeleton({ rows = 5, cols = 3 }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800">
        <Skeleton className="h-6 w-48" />
      </div>
      <div className="divide-y divide-gray-800">
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            {[...Array(cols)].map((_, j) => (
              <Skeleton key={j} className={`h-4 ${j === 0 ? 'w-32' : 'w-20'}`} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// Card skeleton for summary cards
function CardSkeleton() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <Skeleton className="h-4 w-24 mb-2" />
      <Skeleton className="h-8 w-32" />
    </div>
  );
}

// Help icon with tooltip for contextual help
function HelpIcon({ label }) {
  const [showTooltip, setShowTooltip] = useState(false);
  return (
    <div className="relative inline-block">
      <svg
        className="w-4 h-4 text-gray-500 hover:text-gray-400 cursor-help"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      {showTooltip && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-gray-800 border border-gray-700 rounded-lg shadow-lg text-xs text-gray-300 leading-relaxed">
          {label}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-800" />
          </div>
        </div>
      )}
    </div>
  );
}

// Tab components
function DashboardTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/accounting/dashboard`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setData(await res.json());
      } else {
        setError(`Failed to load: ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      console.error("Error fetching dashboard:", err);
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
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
      <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 flex items-center gap-3">
        <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div className="flex-1">
          <p className="text-red-400 font-medium text-sm">{error}</p>
          <p className="text-gray-500 text-xs mt-1">Check that the backend server is running.</p>
        </div>
        <button
          onClick={fetchDashboard}
          className="px-3 py-1 bg-red-600/20 text-red-400 rounded hover:bg-red-600/30 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  // Check if there's no shipped orders yet (common for new installations)
  const hasNoShippedOrders = data?.revenue?.mtd_orders === 0 && data?.revenue?.ytd_orders === 0;
  const hasOutstandingOrders = data?.payments?.outstanding_orders > 0;

  return (
    <div className="space-y-6">
      {/* Helpful hint for new users */}
      {hasNoShippedOrders && hasOutstandingOrders && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-blue-400 font-medium text-sm">Revenue appears after shipping</p>
            <p className="text-gray-400 text-xs mt-1">
              You have {data?.payments?.outstanding_orders} orders awaiting fulfillment.
              Revenue is recognized when orders ship (accrual accounting per GAAP).
              Record payments via the order detail page.
            </p>
          </div>
        </div>
      )}

      {/* Revenue & Payments Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Revenue MTD
            <span
              className="ml-1 text-xs"
              title="Revenue recognized at shipment per GAAP (excludes tax)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(data?.revenue?.mtd)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {data?.revenue?.mtd_orders || 0} orders shipped
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Revenue YTD
            <span
              className="ml-1 text-xs"
              title="Year-to-date from fiscal year start"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(data?.revenue?.ytd)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {data?.revenue?.ytd_orders || 0} orders shipped
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Cash Received MTD
            <span
              className="ml-1 text-xs"
              title="Actual payments collected (cash basis)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {formatCurrency(data?.payments?.mtd_received)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            YTD: {formatCurrency(data?.payments?.ytd_received)}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Accounts Receivable
            <span
              className="ml-1 text-xs"
              title="Outstanding balance owed by customers"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-yellow-400">
            {formatCurrency(data?.payments?.outstanding)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {data?.payments?.outstanding_orders || 0} unpaid orders
          </div>
        </div>
      </div>

      {/* Tax & COGS Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Sales Tax Liability MTD
            <span
              className="ml-1 text-xs"
              title="Tax collected on behalf of government (not revenue)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-blue-400">
            {formatCurrency(data?.tax?.mtd_collected)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            YTD: {formatCurrency(data?.tax?.ytd_collected)}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            COGS MTD
            <span
              className="ml-1 text-xs"
              title="Direct material costs of shipped goods"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-red-400">
            {formatCurrency(data?.cogs?.mtd)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Cost of goods sold</div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Gross Profit MTD
            <span
              className="ml-1 text-xs"
              title="Revenue - COGS (before operating expenses)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {formatCurrency(data?.profit?.mtd_gross)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {(data?.profit?.mtd_margin_pct || 0).toFixed(1)}% margin
          </div>
        </div>
      </div>
    </div>
  );
}

function SalesJournalTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exportError, setExportError] = useState(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  useEffect(() => {
    fetchJournal();
  }, [startDate, endDate]);

  const fetchJournal = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/sales-journal?${params}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error("Error fetching journal:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExportError(null); // Clear previous errors
    try {
      const params = new URLSearchParams({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });

      // Use fetch with Authorization header to keep credentials secure
      // (avoids exposing tokens in URL query strings, browser history, and server logs)
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/sales-journal/export?${params}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        setExportError(`Export failed: ${res.statusText}`);
        console.error("Export failed:", res.statusText);
        return;
      }

      // Convert response to Blob and trigger download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sales-journal-${startDate}-to-${endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setExportError(`Export error: ${err.message}`);
      console.error("Export error:", err);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  return (
    <div className="space-y-4">
      {/* Filters & Export */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
            min="2000-01-01"
            max="2099-12-31"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
            min="2000-01-01"
            max="2099-12-31"
          />
        </div>
        <div className="flex-1"></div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport()}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 text-sm"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Export Error Message */}
      {exportError && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>{exportError}</span>
          <button
            onClick={() => setExportError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            ✕
          </button>
        </div>
      )}

      {/* Totals */}
      {data?.totals && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Orders</div>
            <div className="text-lg font-semibold text-white">
              {data.totals.order_count}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Subtotal</div>
            <div className="text-lg font-semibold text-white">
              {formatCurrency(data.totals.subtotal)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Tax</div>
            <div className="text-lg font-semibold text-blue-400">
              {formatCurrency(data.totals.tax)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Shipping</div>
            <div className="text-lg font-semibold text-white">
              {formatCurrency(data.totals.shipping)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Grand Total</div>
            <div className="text-lg font-semibold text-green-400">
              {formatCurrency(data.totals.grand_total)}
            </div>
          </div>
        </div>
      )}

      {/* Journal Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Date
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Order
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Product
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Subtotal
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Tax
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Total
                </th>
                <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : data?.entries?.length > 0 ? (
                data.entries.map((entry) => (
                  <tr
                    key={entry.order_id}
                    className="border-t border-gray-800 hover:bg-gray-800/50"
                  >
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {entry.date
                        ? new Date(entry.date).toLocaleDateString()
                        : "-"}
                    </td>
                    <td className="py-3 px-4 text-white font-medium">
                      {entry.order_number}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {entry.product_name || "-"}
                    </td>
                    <td className="py-3 px-4 text-right text-white">
                      {formatCurrency(entry.subtotal)}
                    </td>
                    <td className="py-3 px-4 text-right text-blue-400">
                      {formatCurrency(entry.tax_amount)}
                    </td>
                    <td className="py-3 px-4 text-right text-green-400 font-medium">
                      {formatCurrency(entry.grand_total)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          entry.payment_status === "paid"
                            ? "bg-green-500/20 text-green-400"
                            : entry.payment_status === "partial"
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-gray-500/20 text-gray-400"
                        }`}
                      >
                        {entry.payment_status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-500">
                    No sales in this period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PaymentsTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [exportError, setExportError] = useState(null);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split("T")[0];
  });

  const fetchPayments = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const params = new URLSearchParams({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/payments-journal?${params}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        setData(await res.json());
      } else {
        setFetchError(`Failed to load: ${res.status} ${res.statusText}`);
      }
    } catch (err) {
      console.error("Error fetching payments:", err);
      setFetchError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [startDate, endDate]);

  const handleExport = async () => {
    setExportError(null); // Clear previous errors
    try {
      const params = new URLSearchParams({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });

      // Use fetch with Authorization header to keep credentials secure
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/payments-journal/export?${params}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        setExportError(`Export failed: ${res.statusText}`);
        console.error("Export failed:", res.statusText);
        return;
      }

      // Convert response to Blob and trigger download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `payments-journal-${startDate}-to-${endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setExportError(`Export error: ${err.message}`);
      console.error("Export error:", err);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  return (
    <div className="space-y-4">
      {/* Filters & Export */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            min="2000-01-01"
            max="2099-12-31"
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            min="2000-01-01"
            max="2099-12-31"
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex-1"></div>
        <button
          onClick={handleExport}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 text-sm"
        >
          Export CSV
        </button>
      </div>

      {/* Export Error Message */}
      {exportError && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>{exportError}</span>
          <button
            onClick={() => setExportError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            ✕
          </button>
        </div>
      )}

      {/* Fetch Error Message */}
      {fetchError && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-red-400 font-medium text-sm">{fetchError}</p>
            <p className="text-gray-500 text-xs mt-1">Check that the backend server is running.</p>
          </div>
          <button
            onClick={fetchPayments}
            className="px-3 py-1 bg-red-600/20 text-red-400 rounded hover:bg-red-600/30 text-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Summary Cards */}
      {data?.totals && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Payments</div>
            <div className="text-lg font-semibold text-green-400">
              {formatCurrency(data.totals.payments)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Refunds</div>
            <div className="text-lg font-semibold text-red-400">
              {formatCurrency(data.totals.refunds)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Net</div>
            <div className="text-lg font-semibold text-white">
              {formatCurrency(data.totals.net)}
            </div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-xs text-gray-400">Transactions</div>
            <div className="text-lg font-semibold text-white">
              {data.totals.count}
            </div>
          </div>
        </div>
      )}

      {/* By Method */}
      {data?.by_method && Object.keys(data.by_method).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">
            By Payment Method
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data.by_method).map(([method, amount]) => (
              <div key={method} className="bg-gray-800/50 rounded-lg p-3">
                <div className="text-xs text-gray-400 capitalize">{method}</div>
                <div className="text-lg font-semibold text-white">
                  {formatCurrency(amount)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Payments Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Date
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Payment #
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Order
                </th>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Method
                </th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Amount
                </th>
                <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                  Type
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : data?.entries?.length > 0 ? (
                data.entries.map((entry, idx) => (
                  <tr
                    key={idx}
                    className="border-t border-gray-800 hover:bg-gray-800/50"
                  >
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {entry.date
                        ? new Date(entry.date).toLocaleDateString()
                        : "-"}
                    </td>
                    <td className="py-3 px-4 text-white font-medium">
                      {entry.payment_number}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {entry.order_number || "-"}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm capitalize">
                      {entry.payment_method}
                    </td>
                    <td
                      className={`py-3 px-4 text-right font-medium ${
                        entry.amount >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {formatCurrency(entry.amount)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          entry.payment_type === "payment"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {entry.payment_type}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="text-gray-500 mb-2">No payments recorded in this period</div>
                    <p className="text-gray-600 text-xs max-w-md mx-auto">
                      Payments are recorded via the "Record Payment" button on order detail pages.
                      Go to Orders → select an order → click "Record Payment".
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function COGSTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchCOGS();
  }, [days]);

  const fetchCOGS = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/cogs-summary?days=${days}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error("Error fetching COGS:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Period Selector */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-400">Period:</label>
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last 365 days</option>
          </select>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Orders Shipped</div>
          <div className="text-2xl font-bold text-white">
            {data?.orders_shipped || 0}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Revenue
            <span
              className="ml-1 text-xs"
              title="Revenue excludes tax (tax is a liability)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {formatCurrency(data?.revenue)}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Total COGS
            <span
              className="ml-1 text-xs"
              title="Production costs only (materials, labor, packaging)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-red-400">
            {formatCurrency(data?.cogs?.total)}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">
            Gross Profit
            <span
              className="ml-1 text-xs"
              title="Revenue - COGS (before operating expenses)"
            >
              ℹ️
            </span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {formatCurrency(data?.gross_profit)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {(data?.gross_margin_pct || 0).toFixed(1)}% margin
          </div>
        </div>
      </div>

      {/* COGS Breakdown */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="text-lg font-semibold text-white mb-4">
          COGS Breakdown
          <span className="ml-2 text-xs text-gray-400 font-normal">
            (Production costs only)
          </span>
        </h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Materials</span>
            <span className="text-white font-medium">
              {formatCurrency(data?.cogs?.materials)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Labor</span>
            <span className="text-white font-medium">
              {formatCurrency(data?.cogs?.labor)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Packaging</span>
            <span className="text-white font-medium">
              {formatCurrency(data?.cogs?.packaging)}
            </span>
          </div>
          <div className="border-t border-gray-700 pt-3 flex items-center justify-between">
            <span className="text-white font-semibold">Total COGS</span>
            <span className="text-red-400 font-bold">
              {formatCurrency(data?.cogs?.total)}
            </span>
          </div>
          {data?.shipping_expense > 0 && (
            <>
              <div className="border-t border-gray-700 pt-3 mt-3">
                <div className="text-xs text-gray-500 mb-2">
                  Operating Expenses (not in COGS)
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Shipping Expense</span>
                  <span className="text-gray-400 font-medium">
                    {formatCurrency(data?.shipping_expense)}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function TaxCenterTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exportError, setExportError] = useState(null);
  const [period, setPeriod] = useState("quarter");

  useEffect(() => {
    fetchTaxSummary();
  }, [period]);

  const fetchTaxSummary = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/tax-summary?period=${period}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error("Error fetching tax summary:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExportError(null); // Clear previous errors
    try {
      // Use fetch with Authorization header to keep credentials secure
      const res = await fetch(
        `${API_URL}/api/v1/admin/accounting/tax-summary/export?period=${period}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) {
        setExportError(`Export failed: ${res.statusText}`);
        console.error("Export failed:", res.statusText);
        return;
      }

      // Convert response to Blob and trigger download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tax-summary-${period}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setExportError(`Export error: ${err.message}`);
      console.error("Export error:", err);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Period Selector & Export */}
      <div className="flex flex-wrap items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Period</label>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          >
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>
        </div>
        <div className="flex-1"></div>
        <button
          onClick={handleExport}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          Export for Filing
        </button>
      </div>

      {/* Export Error Message */}
      {exportError && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-400 text-sm flex items-center gap-2">
          <span>⚠️</span>
          <span>{exportError}</span>
          <button
            onClick={() => setExportError(null)}
            className="ml-auto text-red-400 hover:text-red-300"
          >
            ✕
          </button>
        </div>
      )}

      {/* Pending Tax Hint */}
      {data?.pending?.order_count > 0 && data?.summary?.order_count === 0 && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-blue-400 font-medium text-sm">Tax is recognized when orders ship</p>
            <p className="text-gray-400 text-xs mt-1">
              You have {data.pending.order_count} pending order{data.pending.order_count > 1 ? "s" : ""} with{" "}
              {formatCurrency(data.pending.tax_amount)} in tax.
              This will appear here when those orders are shipped (accrual accounting per GAAP).
            </p>
          </div>
        </div>
      )}

      {/* Period Header */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-blue-400">{data?.period}</h3>
        <p className="text-sm text-gray-400 mt-1">
          {data?.period_start
            ? new Date(data.period_start).toLocaleDateString()
            : ""}{" "}
          -{" "}
          {data?.period_end
            ? new Date(data.period_end).toLocaleDateString()
            : ""}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Total Sales</div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(data?.summary?.total_sales)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {data?.summary?.order_count || 0} orders
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Taxable Sales</div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(data?.summary?.taxable_sales)}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-gray-400 text-sm mb-1">Non-Taxable Sales</div>
          <div className="text-2xl font-bold text-gray-400">
            {formatCurrency(data?.summary?.non_taxable_sales)}
          </div>
        </div>
        <div className="bg-gray-900 border border-blue-500/50 rounded-xl p-5">
          <div className="text-blue-400 text-sm mb-1">Tax Collected</div>
          <div className="text-2xl font-bold text-blue-400">
            {formatCurrency(data?.summary?.tax_collected)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Amount to remit</div>
        </div>
        {data?.pending?.order_count > 0 && (
          <div className="bg-gray-900 border border-yellow-500/50 rounded-xl p-5">
            <div className="text-yellow-400 text-sm mb-1">Pending Tax</div>
            <div className="text-2xl font-bold text-yellow-400">
              {formatCurrency(data.pending.tax_amount)}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {data.pending.order_count} unshipped order{data.pending.order_count > 1 ? "s" : ""}
            </div>
          </div>
        )}
      </div>

      {/* Tax by Rate */}
      {data?.by_rate?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">By Tax Rate</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Rate
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Taxable Sales
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Tax Collected
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Orders
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.by_rate.map((rate, idx) => (
                  <tr key={idx} className="border-t border-gray-800">
                    <td className="py-2 px-4 text-white">
                      {rate.rate_pct.toFixed(2)}%
                    </td>
                    <td className="py-2 px-4 text-right text-white">
                      {formatCurrency(rate.taxable_sales)}
                    </td>
                    <td className="py-2 px-4 text-right text-blue-400 font-medium">
                      {formatCurrency(rate.tax_collected)}
                    </td>
                    <td className="py-2 px-4 text-right text-gray-400">
                      {rate.order_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Monthly Breakdown */}
      {data?.monthly_breakdown?.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">
            Monthly Breakdown
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Month
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Taxable Sales
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Tax Collected
                  </th>
                  <th className="text-right py-2 px-4 text-xs font-medium text-gray-400 uppercase">
                    Orders
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.monthly_breakdown.map((month, idx) => (
                  <tr key={idx} className="border-t border-gray-800">
                    <td className="py-2 px-4 text-white">{month.month}</td>
                    <td className="py-2 px-4 text-right text-white">
                      {formatCurrency(month.taxable_sales)}
                    </td>
                    <td className="py-2 px-4 text-right text-blue-400 font-medium">
                      {formatCurrency(month.tax_collected)}
                    </td>
                    <td className="py-2 px-4 text-right text-gray-400">
                      {month.order_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function GLReportsTab({ token }) {
  const [activeReport, setActiveReport] = useState("trial-balance");
  const [trialBalance, setTrialBalance] = useState(null);
  const [inventoryVal, setInventoryVal] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchTrialBalance = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/trial-balance`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setTrialBalance(await res.json());
        setLastUpdated(new Date());
      } else {
        setError(`Failed to load: ${res.status}`);
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchInventoryValuation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/inventory-valuation`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setInventoryVal(await res.json());
        setLastUpdated(new Date());
      } else {
        setError(`Failed to load: ${res.status}`);
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchLedger = async (accountCode) => {
    if (!accountCode) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/ledger/${accountCode}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setLedger(await res.json());
        setLastUpdated(new Date());
      } else {
        setError(`Failed to load: ${res.status}`);
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (activeReport === "trial-balance") fetchTrialBalance();
    else if (activeReport === "inventory") fetchInventoryValuation();
    else if (activeReport === "ledger" && selectedAccount) fetchLedger(selectedAccount);
  };

  const formatLastUpdated = (date) => {
    if (!date) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  useEffect(() => {
    if (activeReport === "trial-balance") fetchTrialBalance();
    if (activeReport === "inventory") fetchInventoryValuation();
  }, [activeReport]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  return (
    <div className="space-y-4">
      {/* Report Selector with Refresh */}
      <div className="flex items-center justify-between gap-2 bg-gray-900 border border-gray-800 rounded-xl p-2">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveReport("trial-balance")}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              activeReport === "trial-balance"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800"
            }`}
          >
            Trial Balance
          </button>
          <button
            onClick={() => setActiveReport("inventory")}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              activeReport === "inventory"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800"
            }`}
          >
            Inventory Valuation
          </button>
          <button
            onClick={() => setActiveReport("ledger")}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              activeReport === "ledger"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:bg-gray-800"
            }`}
          >
            Transaction Ledger
          </button>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-gray-500">
              Updated {formatLastUpdated(lastUpdated)}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh data"
          >
            <svg
              className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Loading skeleton based on active report */}
      {loading && activeReport === "trial-balance" && <TableSkeleton rows={8} cols={3} />}
      {loading && activeReport === "inventory" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <TableSkeleton rows={4} cols={5} />
        </div>
      )}
      {loading && activeReport === "ledger" && <TableSkeleton rows={10} cols={6} />}

      {/* Error display with retry */}
      {error && (
        <ErrorAlert
          message={error}
          onRetry={() => {
            if (activeReport === "trial-balance") fetchTrialBalance();
            else if (activeReport === "inventory") fetchInventoryValuation();
            else if (activeReport === "ledger" && selectedAccount) fetchLedger(selectedAccount);
          }}
        />
      )}

      {/* Trial Balance */}
      {activeReport === "trial-balance" && trialBalance && !loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-gray-800 flex justify-between items-center">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-white">Trial Balance</h3>
                <HelpIcon label="Shows all GL account balances. Debits should equal credits. Click any account to view its transaction ledger." />
              </div>
              <p className="text-sm text-gray-400">As of {trialBalance.as_of_date}</p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              trialBalance.is_balanced
                ? "bg-green-500/20 text-green-400"
                : "bg-red-500/20 text-red-400"
            }`}>
              {trialBalance.is_balanced ? "Balanced" : "Out of Balance"}
            </div>
          </div>
          <table className="w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Account</th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Debit</th>
                <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Credit</th>
              </tr>
            </thead>
            <tbody>
              {trialBalance.accounts?.map((acct) => (
                <tr key={acct.account_code} className="border-t border-gray-800 hover:bg-gray-800/50 cursor-pointer"
                    onClick={() => { setSelectedAccount(acct.account_code); setActiveReport("ledger"); fetchLedger(acct.account_code); }}>
                  <td className="py-3 px-4">
                    <span className="text-gray-500 mr-2">{acct.account_code}</span>
                    <span className="text-white">{acct.account_name}</span>
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {acct.debit_balance > 0 ? formatCurrency(acct.debit_balance) : "-"}
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {acct.credit_balance > 0 ? formatCurrency(acct.credit_balance) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-800/50 font-semibold">
              <tr>
                <td className="py-3 px-4 text-white">Total</td>
                <td className="py-3 px-4 text-right text-white">{formatCurrency(trialBalance.total_debits)}</td>
                <td className="py-3 px-4 text-right text-white">{formatCurrency(trialBalance.total_credits)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Inventory Valuation */}
      {activeReport === "inventory" && inventoryVal && !loading && (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">Inventory Valuation</h3>
            <HelpIcon label="Compares physical inventory value to GL balances. Variances indicate missing journal entries or manual adjustments that weren't recorded." />
          </div>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="text-gray-400 text-sm mb-1">Inventory Value</div>
              <div className="text-2xl font-bold text-white">{formatCurrency(inventoryVal.total_inventory_value)}</div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <div className="text-gray-400 text-sm mb-1">GL Balance</div>
              <div className="text-2xl font-bold text-white">{formatCurrency(inventoryVal.total_gl_balance)}</div>
            </div>
            <div className={`bg-gray-900 border rounded-xl p-5 ${
              inventoryVal.is_reconciled ? "border-green-500/50" : "border-red-500/50"
            }`}>
              <div className="text-gray-400 text-sm mb-1">Variance</div>
              <div className={`text-2xl font-bold ${
                inventoryVal.is_reconciled ? "text-green-400" : "text-red-400"
              }`}>
                {formatCurrency(inventoryVal.total_variance)}
              </div>
              <div className="text-xs mt-1">
                {inventoryVal.is_reconciled ? "Reconciled" : "Needs Review"}
              </div>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-white">By Category</h3>
                <HelpIcon label="Breakdown by inventory type: Raw Materials (1200), WIP (1210), Finished Goods (1220), Packaging (1230)." />
              </div>
            </div>
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Category</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Items</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Inventory</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">GL Balance</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Variance</th>
                </tr>
              </thead>
              <tbody>
                {inventoryVal.categories?.map((cat) => (
                  <tr key={cat.gl_account_code} className="border-t border-gray-800">
                    <td className="py-3 px-4">
                      <span className="text-white">{cat.category}</span>
                      <span className="text-gray-500 text-sm ml-2">({cat.gl_account_code})</span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-400">{cat.item_count}</td>
                    <td className="py-3 px-4 text-right text-white">{formatCurrency(cat.inventory_value)}</td>
                    <td className="py-3 px-4 text-right text-white">{formatCurrency(cat.gl_balance)}</td>
                    <td className={`py-3 px-4 text-right font-medium ${
                      Math.abs(cat.variance) < 0.01 ? "text-green-400" : "text-red-400"
                    }`}>
                      {formatCurrency(cat.variance)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Transaction Ledger */}
      {activeReport === "ledger" && (
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">Transaction Ledger</h3>
            <HelpIcon label="Detailed transaction history for a specific GL account. Shows all journal entries affecting the account with running balance." />
          </div>
          {/* Account Selector */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-xs text-gray-400 mb-1">Account Code</label>
                <input
                  type="text"
                  value={selectedAccount}
                  onChange={(e) => setSelectedAccount(e.target.value)}
                  placeholder="e.g., 1200"
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded px-3 py-2 text-sm"
                />
              </div>
              <button
                onClick={() => fetchLedger(selectedAccount)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
              >
                Load Ledger
              </button>
            </div>
          </div>

          {/* Ledger Table */}
          {ledger && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-gray-800">
                <h3 className="text-lg font-semibold text-white">
                  {ledger.account_code} - {ledger.account_name}
                </h3>
                <p className="text-sm text-gray-400">
                  {ledger.transaction_count} transactions |
                  Opening: {formatCurrency(ledger.opening_balance)} |
                  Closing: {formatCurrency(ledger.closing_balance)}
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-800/50">
                    <tr>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Date</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Entry</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Description</th>
                      <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Debit</th>
                      <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Credit</th>
                      <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ledger.transactions?.map((txn, idx) => (
                      <tr key={idx} className="border-t border-gray-800 hover:bg-gray-800/50">
                        <td className="py-3 px-4 text-gray-400 text-sm">{txn.entry_date}</td>
                        <td className="py-3 px-4 text-white font-mono text-sm">{txn.entry_number}</td>
                        <td className="py-3 px-4 text-gray-300 text-sm">{txn.description}</td>
                        <td className="py-3 px-4 text-right text-white">
                          {txn.debit > 0 ? formatCurrency(txn.debit) : "-"}
                        </td>
                        <td className="py-3 px-4 text-right text-white">
                          {txn.credit > 0 ? formatCurrency(txn.credit) : "-"}
                        </td>
                        <td className="py-3 px-4 text-right text-blue-400 font-medium">
                          {formatCurrency(txn.running_balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PeriodsTab({ token }) {
  const [periods, setPeriods] = useState([]);
  const [currentPeriod, setCurrentPeriod] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const toast = useToast();

  useEffect(() => {
    fetchPeriods();
  }, []);

  const fetchPeriods = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/periods`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPeriods(data.periods || []);
        setCurrentPeriod(data.current_period);
        setLastUpdated(new Date());
      } else {
        setError(`Failed to load periods: ${res.status}`);
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatLastUpdated = (date) => {
    if (!date) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const closePeriod = async (periodId) => {
    if (!confirm("Are you sure you want to close this period? No further entries can be made.")) return;
    setActionLoading(periodId);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/periods/${periodId}/close`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ confirm: true }),
      });
      if (res.ok) {
        const result = await res.json();
        toast.success(result.message || "Period closed successfully");
        fetchPeriods();
      } else {
        const data = await res.json();
        toast.error(data.detail || "Failed to close period");
      }
    } catch (err) {
      toast.error(`Error closing period: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const reopenPeriod = async (periodId) => {
    if (!confirm("Are you sure? This will allow modifications to historical data.")) return;
    setActionLoading(periodId);
    try {
      const res = await fetch(`${API_URL}/api/v1/accounting/periods/${periodId}/reopen`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const result = await res.json();
        toast.warning(result.message || "Period reopened - historical data can now be modified");
        fetchPeriods();
      } else {
        const data = await res.json();
        toast.error(data.detail || "Failed to reopen period");
      }
    } catch (err) {
      toast.error(`Error reopening period: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {/* Skeleton for current period */}
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <Skeleton variant="circle" className="w-3 h-3" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
        {/* Skeleton for periods table */}
        <TableSkeleton rows={6} cols={7} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} onRetry={fetchPeriods} />}

      {/* Current Period Highlight */}
      {currentPeriod && (
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
            <span className="text-blue-400 font-medium">Current Period:</span>
            <span className="text-white">{currentPeriod.year}-{String(currentPeriod.period).padStart(2, '0')}</span>
            <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
              currentPeriod.status === "open"
                ? "bg-green-500/20 text-green-400"
                : "bg-gray-500/20 text-gray-400"
            }`}>
              {currentPeriod.status}
            </span>
          </div>
        </div>
      )}

      {/* Periods Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">Fiscal Periods</h3>
            <HelpIcon label="Manage accounting periods. Closing a period prevents entries from being backdated. Reopen with caution - allows modifications to historical data." />
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-xs text-gray-500">
                Updated {formatLastUpdated(lastUpdated)}
              </span>
            )}
            <button
              onClick={fetchPeriods}
              disabled={loading}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh data"
            >
              <svg
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </div>
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Period</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">Date Range</th>
              <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">Status</th>
              <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Entries</th>
              <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Total DR</th>
              <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">Total CR</th>
              <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {periods.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-gray-500">
                  No fiscal periods found
                </td>
              </tr>
            ) : (
              periods.map((period) => (
                <tr key={period.id} className="border-t border-gray-800">
                  <td className="py-3 px-4 text-white font-medium">
                    {period.year}-{String(period.period).padStart(2, '0')}
                  </td>
                  <td className="py-3 px-4 text-gray-400 text-sm">
                    {period.start_date} to {period.end_date}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      period.status === "open"
                        ? "bg-green-500/20 text-green-400"
                        : "bg-gray-500/20 text-gray-400"
                    }`}>
                      {period.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-400">{period.journal_entry_count}</td>
                  <td className="py-3 px-4 text-right text-white">{formatCurrency(period.total_debits)}</td>
                  <td className="py-3 px-4 text-right text-white">{formatCurrency(period.total_credits)}</td>
                  <td className="py-3 px-4 text-center">
                    {period.status === "open" ? (
                      <button
                        onClick={() => closePeriod(period.id)}
                        disabled={actionLoading === period.id}
                        className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white rounded text-sm disabled:opacity-50"
                      >
                        {actionLoading === period.id ? "..." : "Close"}
                      </button>
                    ) : (
                      <button
                        onClick={() => reopenPeriod(period.id)}
                        disabled={actionLoading === period.id}
                        className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm disabled:opacity-50"
                      >
                        {actionLoading === period.id ? "..." : "Reopen"}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Main component
export default function AdminAccounting() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const token = localStorage.getItem("adminToken");
  const { isPro, isEnterprise, loading: tierLoading } = useFeatureFlags();

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "chart-bar", tier: "community" },
    { id: "sales", label: "Sales Journal", icon: "receipt", tier: "community" },
    { id: "payments", label: "Payments", icon: "credit-card", tier: "community" },
    { id: "cogs", label: "COGS & Materials", icon: "cube", tier: "community" },
    { id: "tax", label: "Tax Center", icon: "calculator", tier: "community" },
    { id: "glreports", label: "GL Reports", icon: "document-report", tier: "pro" },
    { id: "periods", label: "Periods", icon: "calendar", tier: "pro" },
  ];

  // Check if user can access a tab based on their tier
  const canAccessTab = (tier) => {
    if (tier === "community") return true;
    if (tier === "pro") return isPro || isEnterprise;
    if (tier === "enterprise") return isEnterprise;
    return false;
  };

  const getTabIcon = (icon) => {
    switch (icon) {
      case "chart-bar":
        return (
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
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
        );
      case "receipt":
        return (
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
        );
      case "credit-card":
        return (
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
              d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
            />
          </svg>
        );
      case "cube":
        return (
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
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
        );
      case "calculator":
        return (
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
              d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        );
      case "document-report":
        return (
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
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        );
      case "calendar":
        return (
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
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Accounting</h1>
        <p className="text-gray-400 mt-1">
          Financial overview, sales journal, and tax reports
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-1 flex flex-wrap gap-1">
        {tabs.map((tab) => {
          const accessible = canAccessTab(tab.tier);
          return (
            <button
              key={tab.id}
              onClick={() => accessible && setActiveTab(tab.id)}
              disabled={!accessible}
              title={!accessible ? `Requires ${tab.tier === "pro" ? "Pro" : "Enterprise"} tier` : ""}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : accessible
                    ? "text-gray-400 hover:text-white hover:bg-gray-800"
                    : "text-gray-600 cursor-not-allowed"
              }`}
            >
              {getTabIcon(tab.icon)}
              {tab.label}
              {!accessible && (
                <svg className="w-3 h-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "dashboard" && <DashboardTab token={token} />}
      {activeTab === "sales" && <SalesJournalTab token={token} />}
      {activeTab === "payments" && <PaymentsTab token={token} />}
      {activeTab === "cogs" && <COGSTab token={token} />}
      {activeTab === "tax" && <TaxCenterTab token={token} />}
      {activeTab === "glreports" && <GLReportsTab token={token} />}
      {activeTab === "periods" && <PeriodsTab token={token} />}
    </div>
  );
}
