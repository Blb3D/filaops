import { useState, useEffect } from "react";
import { API_URL } from "../../config/api";

// Tab components
function DashboardTab({ token }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/accounting/dashboard`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (err) {
      console.error("Error fetching dashboard:", err);
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

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount || 0);
  };

  return (
    <div className="space-y-6">
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

  const handleExport = async (format) => {
    setExportError(null); // Clear previous errors
    try {
      const params = new URLSearchParams({
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        format: format,
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
      a.download = `sales-journal-${startDate}-to-${endDate}.${
        format === "quickbooks" ? "iif" : "csv"
      }`;
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
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex-1"></div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport("generic")}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 text-sm"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport("quickbooks")}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
          >
            Export for QuickBooks
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
    fetchPayments();
  }, [startDate, endDate]);

  const fetchPayments = async () => {
    setLoading(true);
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
      }
    } catch (err) {
      console.error("Error fetching payments:", err);
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
            className="bg-gray-800 border border-gray-700 text-white rounded px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
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
                  <td colSpan={6} className="py-8 text-center text-gray-500">
                    No payments in this period
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

// Main component
export default function AdminAccounting() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const token = localStorage.getItem("adminToken");

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "chart-bar" },
    { id: "sales", label: "Sales Journal", icon: "receipt" },
    { id: "payments", label: "Payments", icon: "credit-card" },
    { id: "cogs", label: "COGS & Materials", icon: "cube" },
    { id: "tax", label: "Tax Center", icon: "calculator" },
  ];

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
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white hover:bg-gray-800"
            }`}
          >
            {getTabIcon(tab.icon)}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "dashboard" && <DashboardTab token={token} />}
      {activeTab === "sales" && <SalesJournalTab token={token} />}
      {activeTab === "payments" && <PaymentsTab token={token} />}
      {activeTab === "cogs" && <COGSTab token={token} />}
      {activeTab === "tax" && <TaxCenterTab token={token} />}
    </div>
  );
}
