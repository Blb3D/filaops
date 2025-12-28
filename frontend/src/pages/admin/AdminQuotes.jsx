import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

// Status options with colors
const STATUS_OPTIONS = [
  { value: "pending", label: "Pending", color: "yellow" },
  { value: "approved", label: "Approved", color: "blue" },
  { value: "accepted", label: "Accepted", color: "cyan" },
  { value: "rejected", label: "Rejected", color: "red" },
  { value: "converted", label: "Converted", color: "green" },
  { value: "cancelled", label: "Cancelled", color: "gray" },
];

export default function AdminQuotes() {
  const navigate = useNavigate();
  const toast = useToast();
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    search: "",
    status: "all",
  });

  // Modal states
  const [showQuoteModal, setShowQuoteModal] = useState(false);
  const [editingQuote, setEditingQuote] = useState(null);
  const [viewingQuote, setViewingQuote] = useState(null);

  const token = localStorage.getItem("adminToken");

  useEffect(() => {
    fetchQuotes();
    fetchStats();
  }, [filters.status]);

  const fetchQuotes = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "200");
      if (filters.status !== "all") params.set("status", filters.status);

      const res = await fetch(`${API_URL}/api/v1/quotes?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch quotes");
      const data = await res.json();
      setQuotes(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch {
      // Stats fetch failure is non-critical
    }
  };

  const filteredQuotes = quotes.filter((quote) => {
    if (!filters.search) return true;
    const search = filters.search.toLowerCase();
    return (
      quote.quote_number?.toLowerCase().includes(search) ||
      quote.product_name?.toLowerCase().includes(search) ||
      quote.customer_name?.toLowerCase().includes(search) ||
      quote.customer_email?.toLowerCase().includes(search)
    );
  });

  const getStatusStyle = (status) => {
    const found = STATUS_OPTIONS.find((s) => s.value === status);
    if (!found) return "bg-gray-500/20 text-gray-400";
    return {
      yellow: "bg-yellow-500/20 text-yellow-400",
      blue: "bg-blue-500/20 text-blue-400",
      cyan: "bg-cyan-500/20 text-cyan-400",
      red: "bg-red-500/20 text-red-400",
      green: "bg-green-500/20 text-green-400",
      gray: "bg-gray-500/20 text-gray-400",
    }[found.color];
  };

  const handleSaveQuote = async (quoteData) => {
    try {
      const url = editingQuote
        ? `${API_URL}/api/v1/quotes/${editingQuote.id}`
        : `${API_URL}/api/v1/quotes`;
      const method = editingQuote ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(quoteData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save quote");
      }

      toast.success(editingQuote ? "Quote updated" : "Quote created");
      setShowQuoteModal(false);
      setEditingQuote(null);
      fetchQuotes();
      fetchStats();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleUpdateStatus = async (quoteId, newStatus, rejectionReason = null) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quoteId}/status`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: newStatus,
          rejection_reason: rejectionReason,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update status");
      }

      const updated = await res.json();
      toast.success(`Quote ${newStatus}`);
      fetchQuotes();
      fetchStats();
      if (viewingQuote?.id === quoteId) {
        setViewingQuote(updated);
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleConvertToOrder = async (quoteId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quoteId}/convert`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to convert quote");
      }

      const data = await res.json();
      toast.success(`Converted to ${data.order_number}`);
      setViewingQuote(null);
      fetchQuotes();
      fetchStats();

      // Navigate to the new order
      navigate(`/admin/orders/${data.order_id}`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDownloadPDF = async (quote) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quote.id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to generate PDF");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${quote.quote_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      toast.success("Quote PDF downloaded");
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handlePrintPDF = async (quote) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quote.id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to generate PDF");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      // Open in new window for printing
      const printWindow = window.open(url, "_blank");
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      } else {
        // Fallback: just open in new tab if popup blocked
        window.open(url, "_blank");
        toast.info("PDF opened in new tab. Use browser print (Ctrl+P) to print.");
      }
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDuplicateQuote = async (quote) => {
    try {
      // Create a new quote based on the existing one
      const newQuoteData = {
        product_id: quote.product_id || null,
        product_name: quote.product_name,
        quantity: quote.quantity,
        unit_price: parseFloat(quote.unit_price || 0),
        customer_id: quote.customer_id || null,
        customer_name: quote.customer_name || null,
        customer_email: quote.customer_email || null,
        material_type: quote.material_type || null,
        color: quote.color || null,
        customer_notes: quote.customer_notes || null,
        admin_notes: `Duplicated from ${quote.quote_number}`,
        apply_tax: quote.tax_rate ? true : false,
        valid_days: 30,
      };

      const res = await fetch(`${API_URL}/api/v1/quotes`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newQuoteData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to duplicate quote");
      }

      const newQuote = await res.json();
      toast.success(`Quote duplicated as ${newQuote.quote_number}`);
      fetchQuotes();
      fetchStats();
      setViewingQuote(newQuote);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleCopyQuoteLink = (quote) => {
    // Create a shareable link - could be customer portal link or just quote reference
    const quoteLink = `${window.location.origin}/quote/${quote.quote_number}`;
    navigator.clipboard.writeText(quoteLink).then(() => {
      toast.success("Quote link copied to clipboard");
    }).catch(() => {
      // Fallback - copy quote number
      navigator.clipboard.writeText(quote.quote_number);
      toast.success("Quote number copied to clipboard");
    });
  };

  const handleDeleteQuote = async (quoteId) => {
    if (!confirm("Are you sure you want to delete this quote?")) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quoteId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete quote");
      }

      toast.success("Quote deleted");
      setViewingQuote(null);
      fetchQuotes();
      fetchStats();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const isExpired = (quote) => {
    return new Date(quote.expires_at) < new Date();
  };

  const isExpiringSoon = (quote) => {
    const expiresAt = new Date(quote.expires_at);
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    return expiresAt > now && expiresAt <= sevenDaysFromNow;
  };

  const getDaysUntilExpiry = (quote) => {
    const expiresAt = new Date(quote.expires_at);
    const now = new Date();
    const diffTime = expiresAt.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Quote Management</h1>
          <p className="text-gray-400 mt-1">Create and manage customer quotes</p>
        </div>
        <button
          onClick={() => {
            setEditingQuote(null);
            setShowQuoteModal(true);
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Quote
        </button>
      </div>

      {/* Stats Cards - Clickable to filter */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <button
            onClick={() => setFilters((f) => ({ ...f, status: "pending" }))}
            className={`text-left bg-gradient-to-br from-yellow-600/20 to-yellow-600/5 border rounded-xl p-4 transition-all hover:scale-[1.02] ${
              filters.status === "pending" ? "border-yellow-400 ring-1 ring-yellow-400" : "border-yellow-500/30"
            }`}
          >
            <p className="text-gray-400 text-sm">Pending</p>
            <p className="text-2xl font-bold text-white">{stats.pending}</p>
            <p className="text-yellow-400 text-xs mt-1">
              ${parseFloat(stats.pending_value || 0).toLocaleString()}
            </p>
          </button>
          <button
            onClick={() => setFilters((f) => ({ ...f, status: "approved" }))}
            className={`text-left bg-gradient-to-br from-blue-600/20 to-blue-600/5 border rounded-xl p-4 transition-all hover:scale-[1.02] ${
              filters.status === "approved" ? "border-blue-400 ring-1 ring-blue-400" : "border-blue-500/30"
            }`}
          >
            <p className="text-gray-400 text-sm">Approved</p>
            <p className="text-2xl font-bold text-white">{stats.approved}</p>
            <p className="text-blue-400 text-xs mt-1">Ready to accept</p>
          </button>
          <button
            onClick={() => setFilters((f) => ({ ...f, status: "accepted" }))}
            className={`text-left bg-gradient-to-br from-cyan-600/20 to-cyan-600/5 border rounded-xl p-4 transition-all hover:scale-[1.02] ${
              filters.status === "accepted" ? "border-cyan-400 ring-1 ring-cyan-400" : "border-cyan-500/30"
            }`}
          >
            <p className="text-gray-400 text-sm">Accepted</p>
            <p className="text-2xl font-bold text-white">{stats.accepted}</p>
            <p className="text-cyan-400 text-xs mt-1">Ready to convert</p>
          </button>
          <button
            onClick={() => setFilters((f) => ({ ...f, status: "converted" }))}
            className={`text-left bg-gradient-to-br from-green-600/20 to-green-600/5 border rounded-xl p-4 transition-all hover:scale-[1.02] ${
              filters.status === "converted" ? "border-green-400 ring-1 ring-green-400" : "border-green-500/30"
            }`}
          >
            <p className="text-gray-400 text-sm">Converted</p>
            <p className="text-2xl font-bold text-white">{stats.converted}</p>
            <p className="text-green-400 text-xs mt-1">Became orders</p>
          </button>
          <div className="bg-gradient-to-br from-emerald-600/20 to-emerald-600/5 border border-emerald-500/30 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Conversion Rate</p>
            <p className="text-2xl font-bold text-white">
              {stats.total > 0 ? ((stats.converted / stats.total) * 100).toFixed(1) : 0}%
            </p>
            <p className="text-emerald-400 text-xs mt-1">
              {stats.converted} of {stats.total} quotes
            </p>
          </div>
          <button
            onClick={() => setFilters((f) => ({ ...f, status: "all" }))}
            className={`text-left bg-gradient-to-br from-purple-600/20 to-purple-600/5 border rounded-xl p-4 transition-all hover:scale-[1.02] ${
              filters.status === "all" ? "border-purple-400 ring-1 ring-purple-400" : "border-purple-500/30"
            }`}
          >
            <p className="text-gray-400 text-sm">Total Value</p>
            <p className="text-2xl font-bold text-white">
              ${parseFloat(stats.total_value || 0).toLocaleString()}
            </p>
            <p className="text-purple-400 text-xs mt-1">{stats.total} quotes</p>
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search quotes..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white pl-10"
          />
          <svg
            className="w-5 h-5 absolute left-3 top-2.5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
        >
          <option value="all">All Status</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Quotes Table */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-800/50">
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Quote #</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Product</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Customer</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Qty</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Total</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Status</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium text-sm">Expires</th>
                <th className="text-right px-4 py-3 text-gray-400 font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filteredQuotes.map((quote) => {
                const expired = isExpired(quote) && quote.status !== "converted";
                const expiringSoon = !expired && isExpiringSoon(quote) && quote.status !== "converted";
                const daysLeft = getDaysUntilExpiry(quote);

                return (
                  <tr
                    key={quote.id}
                    className={`hover:bg-gray-800/50 cursor-pointer ${expired ? "opacity-60" : ""}`}
                    onClick={() => setViewingQuote(quote)}
                  >
                    <td className="px-4 py-3">
                      <span className="text-white font-mono">{quote.quote_number}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-white">{quote.product_name || "—"}</span>
                      {quote.material_type && (
                        <span className="text-gray-500 text-sm ml-2">
                          ({quote.material_type}
                          {quote.color ? ` / ${quote.color}` : ""})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-white">{quote.customer_name || "—"}</span>
                      {quote.customer_email && (
                        <span className="text-gray-500 text-sm block">{quote.customer_email}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-white">{quote.quantity}</td>
                    <td className="px-4 py-3 text-green-400 font-medium">
                      ${parseFloat(quote.total_price || 0).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs ${getStatusStyle(quote.status)}`}>
                        {quote.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {quote.status === "converted" ? (
                        <span className="text-gray-500 text-sm">—</span>
                      ) : expired ? (
                        <span className="text-red-400 text-sm font-medium">Expired</span>
                      ) : expiringSoon ? (
                        <span className="text-yellow-400 text-sm font-medium">
                          {daysLeft} day{daysLeft !== 1 ? "s" : ""} left
                        </span>
                      ) : (
                        <span className="text-gray-400 text-sm">
                          {new Date(quote.expires_at).toLocaleDateString()}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => handleDownloadPDF(quote)}
                          className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
                          title="Download PDF"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                        </button>
                        <button
                          onClick={() => handlePrintPDF(quote)}
                          className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
                          title="Print Quote"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                            />
                          </svg>
                        </button>
                        {quote.status === "pending" && (
                          <button
                            onClick={() => handleUpdateStatus(quote.id, "approved")}
                            className="p-1.5 text-blue-400 hover:text-blue-300 hover:bg-blue-900/30 rounded"
                            title="Approve"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                        )}
                        {(quote.status === "approved" || quote.status === "accepted") && !expired && (
                          <button
                            onClick={() => handleConvertToOrder(quote.id)}
                            className="p-1.5 text-green-400 hover:text-green-300 hover:bg-green-900/30 rounded"
                            title="Convert to Order"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                              />
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredQuotes.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                    No quotes found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Quote Modal */}
      {showQuoteModal && (
        <QuoteFormModal
          quote={editingQuote}
          onSave={handleSaveQuote}
          onClose={() => {
            setShowQuoteModal(false);
            setEditingQuote(null);
          }}
          token={token}
        />
      )}

      {/* View Quote Modal */}
      {viewingQuote && (
        <QuoteDetailModal
          quote={viewingQuote}
          onClose={() => setViewingQuote(null)}
          onEdit={() => {
            setEditingQuote(viewingQuote);
            setShowQuoteModal(true);
            setViewingQuote(null);
          }}
          onUpdateStatus={handleUpdateStatus}
          onConvert={handleConvertToOrder}
          onDownloadPDF={handleDownloadPDF}
          onPrintPDF={handlePrintPDF}
          onDuplicate={handleDuplicateQuote}
          onCopyLink={handleCopyQuoteLink}
          onDelete={handleDeleteQuote}
          getStatusStyle={getStatusStyle}
          onRefresh={async () => {
            // Refresh the viewing quote to get updated has_image flag
            const res = await fetch(`${API_URL}/api/v1/quotes/${viewingQuote.id}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
              const updated = await res.json();
              setViewingQuote(updated);
            }
            fetchQuotes();
          }}
        />
      )}
    </div>
  );
}

// Quote Form Modal Component - Now with Product Selection, Customer, and Tax
function QuoteFormModal({ quote, onSave, onClose, token }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [step, setStep] = useState(1); // 1=product, 2=customer+details
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [companySettings, setCompanySettings] = useState(null);
  const [productSearch, setProductSearch] = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({
    product_id: quote?.product_id || null,
    product_name: quote?.product_name || "",
    quantity: quote?.quantity || 1,
    unit_price: quote?.unit_price || "",
    customer_id: quote?.customer_id || null,
    customer_name: quote?.customer_name || "",
    customer_email: quote?.customer_email || "",
    material_type: quote?.material_type || "",
    color: quote?.color || "",
    customer_notes: quote?.customer_notes || "",
    admin_notes: quote?.admin_notes || "",
    apply_tax: quote?.tax_rate ? true : null, // null = use company default
    shipping_cost: quote?.shipping_cost || "",
    valid_days: 30,
  });
  const [saveAsCustomer, setSaveAsCustomer] = useState(false);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchProducts();
    fetchCustomers();
    fetchCompanySettings();
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/products?limit=500&active_only=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProducts(data.items || data || []);
      }
    } catch {
      // Products fetch failure will show empty list
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/customers?limit=200`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCustomers(data.items || data || []);
      }
    } catch {
      // Customers fetch failure is non-critical
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
        // Default apply_tax based on company settings
        if (form.apply_tax === null && !quote) {
          setForm((f) => ({ ...f, apply_tax: data.tax_enabled }));
        }
      }
    } catch {
      // Company settings fetch failure is non-critical
    }
  };

  // Filter products that have a BOM
  const filteredProducts = products.filter((p) => {
    if (!p.has_bom) return false;
    if (!productSearch.trim()) return true;
    const search = productSearch.toLowerCase();
    return (
      (p.name || "").toLowerCase().includes(search) ||
      (p.sku || "").toLowerCase().includes(search)
    );
  });

  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setForm((f) => ({
      ...f,
      product_id: product.id,
      product_name: product.name,
      unit_price: product.selling_price || "",
      material_type: product.category || "",
    }));
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.product_name || !form.unit_price) {
      toast.error("Product and unit price are required");
      return;
    }

    // Validate save as customer requires email
    if (saveAsCustomer && !form.customer_email) {
      toast.error("Customer email is required to save as new customer");
      return;
    }

    setSaving(true);

    // If saving as new customer, create customer first
    let customerId = form.customer_id;
    if (saveAsCustomer && !customerId && form.customer_email) {
      try {
        // Parse name into first/last
        const nameParts = (form.customer_name || "").trim().split(" ");
        const firstName = nameParts[0] || "";
        const lastName = nameParts.slice(1).join(" ") || "";

        const customerRes = await fetch(`${API_URL}/api/v1/admin/customers`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: form.customer_email,
            first_name: firstName || null,
            last_name: lastName || null,
          }),
        });

        if (customerRes.ok) {
          const newCustomer = await customerRes.json();
          customerId = newCustomer.id;
          toast.success(`Customer ${newCustomer.customer_number} created`);
        } else {
          const err = await customerRes.json();
          // If customer exists, try to find them
          if (err.detail?.includes("already exists")) {
            toast.info("Customer already exists, linking to quote");
          } else {
            throw new Error(err.detail || "Failed to create customer");
          }
        }
      } catch (err) {
        console.error("Failed to create customer:", err);
        // Continue with quote creation even if customer creation fails
      }
    }

    // Build the payload - only send fields the backend accepts
    const payload = {
      product_id: form.product_id || null,
      product_name: form.product_name,
      quantity: form.quantity,
      unit_price: parseFloat(form.unit_price),
      customer_id: customerId || null,
      customer_name: form.customer_name || null,
      customer_email: form.customer_email || null,
      material_type: form.material_type || null,
      color: form.color || null,
      customer_notes: form.customer_notes || null,
      admin_notes: form.admin_notes || null,
      apply_tax: form.apply_tax,
      shipping_cost: form.shipping_cost ? parseFloat(form.shipping_cost) : null,
    };

    // Only include valid_days for new quotes (not updates)
    if (!quote) {
      payload.valid_days = form.valid_days;
    }

    await onSave(payload);
    setSaving(false);
  };

  // Handle customer selection from dropdown
  const handleCustomerSelect = (e) => {
    const customerId = e.target.value ? parseInt(e.target.value) : null;
    if (customerId) {
      const customer = customers.find((c) => c.id === customerId);
      if (customer) {
        setForm((f) => ({
          ...f,
          customer_id: customerId,
          customer_name: `${customer.first_name || ""} ${customer.last_name || ""}`.trim() || customer.email,
          customer_email: customer.email || "",
        }));
      }
    } else {
      setForm((f) => ({ ...f, customer_id: null }));
    }
  };

  // Calculate totals preview
  const subtotal = (parseFloat(form.unit_price) || 0) * (form.quantity || 1);
  const taxRate = form.apply_tax && companySettings?.tax_rate_percent ? companySettings.tax_rate_percent / 100 : 0;
  const taxAmount = subtotal * taxRate;
  const shippingCost = parseFloat(form.shipping_cost) || 0;
  const grandTotal = subtotal + taxAmount + shippingCost;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-3xl w-full mx-auto p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-white">
              {quote ? "Edit Quote" : "New Quote"} - Step {step} of 2
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Step indicator */}
          <div className="flex gap-2 mb-6">
            <div className={`flex-1 h-1 rounded ${step >= 1 ? "bg-blue-500" : "bg-gray-700"}`} />
            <div className={`flex-1 h-1 rounded ${step >= 2 ? "bg-blue-500" : "bg-gray-700"}`} />
          </div>

          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h4 className="text-white font-medium mb-2">Select Product</h4>
                <p className="text-gray-400 text-sm mb-4">
                  Choose an existing product with BOM, or{" "}
                  <button
                    onClick={() => navigate("/admin/items?action=new")}
                    className="text-blue-400 hover:underline"
                  >
                    create a new product first
                  </button>
                </p>
              </div>

              {/* Product Search */}
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search products by SKU or name..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white pl-10"
                />
                <svg
                  className="w-5 h-5 absolute left-3 top-3.5 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>

              {/* Product Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-[400px] overflow-auto">
                {loading ? (
                  <div className="col-span-full flex justify-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : filteredProducts.length === 0 ? (
                  <div className="col-span-full text-center py-8 text-gray-500">
                    {productSearch.trim()
                      ? `No products with BOM found matching "${productSearch}"`
                      : "No products with BOM available. Create a product with BOM first."}
                  </div>
                ) : (
                  filteredProducts.map((product) => (
                    <button
                      key={product.id}
                      onClick={() => handleSelectProduct(product)}
                      className={`text-left p-4 bg-gray-800 border rounded-lg hover:border-blue-500 transition-colors ${
                        selectedProduct?.id === product.id
                          ? "border-blue-500 bg-blue-900/20"
                          : "border-gray-700"
                      }`}
                    >
                      <div className="text-white font-medium truncate">{product.name}</div>
                      <div className="text-gray-500 text-xs font-mono mt-1">{product.sku}</div>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-green-400 font-medium">
                          ${parseFloat(product.selling_price || 0).toFixed(2)}
                        </span>
                        <span className="text-xs text-blue-400">Has BOM</span>
                      </div>
                    </button>
                  ))
                )}
              </div>

              <div className="flex justify-end pt-4 border-t border-gray-700">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Selected Product */}
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-white font-medium">{form.product_name}</h4>
                    <p className="text-gray-400 text-sm">{selectedProduct?.sku}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="text-blue-400 text-sm hover:underline"
                  >
                    Change
                  </button>
                </div>
              </div>

              {/* Quantity & Price */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    value={form.quantity}
                    onChange={(e) => setForm((f) => ({ ...f, quantity: parseInt(e.target.value) || 1 }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Unit Price *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.unit_price}
                    onChange={(e) => setForm((f) => ({ ...f, unit_price: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    required
                  />
                </div>
              </div>

              {/* Customer Info */}
              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-sm font-medium text-gray-300 mb-3">Customer Information</h4>

                {/* Customer Selection Dropdown */}
                {customers.length > 0 && (
                  <div className="mb-4">
                    <label className="block text-sm text-gray-400 mb-1">Select Existing Customer</label>
                    <select
                      value={form.customer_id || ""}
                      onChange={handleCustomerSelect}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    >
                      <option value="">-- Enter customer manually --</option>
                      {customers.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.first_name} {c.last_name} ({c.email})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Customer Name</label>
                    <input
                      type="text"
                      value={form.customer_name}
                      onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Customer Email</label>
                    <input
                      type="email"
                      value={form.customer_email}
                      onChange={(e) => setForm((f) => ({ ...f, customer_email: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    />
                  </div>
                </div>

                {/* Save as new customer option - only show if not already a customer */}
                {!form.customer_id && form.customer_email && (
                  <div className="mt-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={saveAsCustomer}
                        onChange={(e) => setSaveAsCustomer(e.target.checked)}
                        className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-600"
                      />
                      <span className="text-sm text-gray-300">
                        Save as new customer record
                      </span>
                    </label>
                  </div>
                )}
              </div>

              {/* Tax & Shipping */}
              <div className="border-t border-gray-700 pt-4 space-y-4">
                {companySettings?.tax_enabled && (
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="apply_tax"
                      checked={form.apply_tax || false}
                      onChange={(e) => setForm((f) => ({ ...f, apply_tax: e.target.checked }))}
                      className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-blue-600"
                    />
                    <label htmlFor="apply_tax" className="text-white">
                      Apply {companySettings.tax_name || "Sales Tax"} ({companySettings.tax_rate_percent?.toFixed(2)}%)
                    </label>
                  </div>
                )}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Shipping Cost</label>
                  <div className="relative w-40">
                    <span className="absolute left-3 top-2 text-gray-400">$</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.shipping_cost}
                      onChange={(e) => setForm((f) => ({ ...f, shipping_cost: e.target.value }))}
                      placeholder="0.00"
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 pl-7 text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div className="border-t border-gray-700 pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Customer Notes</label>
                    <textarea
                      value={form.customer_notes}
                      onChange={(e) => setForm((f) => ({ ...f, customer_notes: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                      rows={2}
                      placeholder="Special requests..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Internal Notes</label>
                    <textarea
                      value={form.admin_notes}
                      onChange={(e) => setForm((f) => ({ ...f, admin_notes: e.target.value }))}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                      rows={2}
                      placeholder="Internal notes..."
                    />
                  </div>
                </div>
              </div>

              {/* Valid Days */}
              {!quote && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Quote Valid For (days)</label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={form.valid_days}
                    onChange={(e) => setForm((f) => ({ ...f, valid_days: parseInt(e.target.value) || 30 }))}
                    className="w-32 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>
              )}

              {/* Total Preview with Tax & Shipping Breakdown */}
              <div className="bg-gray-800 rounded-lg p-4 space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-400">Subtotal:</span>
                  <span className="text-white">${subtotal.toFixed(2)}</span>
                </div>
                {form.apply_tax && taxAmount > 0 && (
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">
                      {companySettings?.tax_name || "Tax"} ({companySettings?.tax_rate_percent?.toFixed(2)}%):
                    </span>
                    <span className="text-white">${taxAmount.toFixed(2)}</span>
                  </div>
                )}
                {shippingCost > 0 && (
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">Shipping:</span>
                    <span className="text-white">${shippingCost.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between items-center pt-2 border-t border-gray-700">
                  <span className="text-gray-400 font-medium">Total:</span>
                  <span className="text-2xl font-bold text-green-400">${grandTotal.toFixed(2)}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-between gap-3 pt-4 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                >
                  Back
                </button>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? "Saving..." : quote ? "Update Quote" : "Create Quote"}
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// Quote Detail Modal Component
function QuoteDetailModal({
  quote,
  onClose,
  onEdit,
  onUpdateStatus,
  onConvert,
  onDownloadPDF,
  onPrintPDF,
  onDuplicate,
  onCopyLink,
  onDelete,
  getStatusStyle,
  onRefresh,
}) {
  const toast = useToast();
  const token = localStorage.getItem("adminToken");
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageUrl, setImageUrl] = useState(null);
  const imageUrlRef = useRef(null);

  const isExpired = new Date(quote.expires_at) < new Date();
  const canConvert =
    (quote.status === "approved" || quote.status === "accepted") && !isExpired && !quote.sales_order_id;

  // Load image if quote has one (fetch with auth and create blob URL)
  useEffect(() => {
    if (quote.has_image) {
      fetch(`${API_URL}/api/v1/quotes/${quote.id}/image`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (res.ok) return res.blob();
          throw new Error("Failed to load image");
        })
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          imageUrlRef.current = url;
          setImageUrl(url);
        })
        .catch(() => setImageUrl(null));
    } else {
      setImageUrl(null);
    }

    // Cleanup blob URL on unmount (use ref to avoid stale closure)
    return () => {
      if (imageUrlRef.current) {
        URL.revokeObjectURL(imageUrlRef.current);
        imageUrlRef.current = null;
      }
    };
  }, [quote.id, quote.has_image, token]);

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be less than 5MB");
      return;
    }

    setUploadingImage(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quote.id}/image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to upload image");
      }

      toast.success("Image uploaded successfully");
      // Refresh image by fetching with auth
      const imgRes = await fetch(`${API_URL}/api/v1/quotes/${quote.id}/image`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (imgRes.ok) {
        const blob = await imgRes.blob();
        setImageUrl(URL.createObjectURL(blob));
      }
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleImageDelete = async () => {
    if (!confirm("Delete this product image?")) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/quotes/${quote.id}/image`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete image");
      }

      toast.success("Image deleted");
      setImageUrl(null);
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-2xl w-full mx-auto p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">{quote.quote_number}</h3>
              <p className="text-gray-400 text-sm">
                Created {new Date(quote.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-sm ${getStatusStyle(quote.status)}`}>
                {quote.status}
              </span>
              {isExpired && quote.status !== "converted" && (
                <span className="px-3 py-1 rounded-full text-sm bg-red-500/20 text-red-400">Expired</span>
              )}
              <button onClick={onClose} className="text-gray-400 hover:text-white ml-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Quote Details */}
          <div className="space-y-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Product Details</h4>
              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div>
                  <span className="text-gray-400">Product:</span>
                  <span className="text-white ml-2">{quote.product_name || "—"}</span>
                </div>
                <div>
                  <span className="text-gray-400">Quantity:</span>
                  <span className="text-white ml-2">{quote.quantity}</span>
                </div>
                {quote.material_type && (
                  <div>
                    <span className="text-gray-400">Material:</span>
                    <span className="text-white ml-2">
                      {quote.material_type}
                      {quote.color ? ` / ${quote.color}` : ""}
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-gray-400">Unit Price:</span>
                  <span className="text-white ml-2">${parseFloat(quote.unit_price || 0).toFixed(2)}</span>
                </div>
              </div>
              {/* Price Breakdown */}
              <div className="border-t border-gray-700 pt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Subtotal:</span>
                  <span className="text-white">
                    ${parseFloat(quote.subtotal || (quote.unit_price * quote.quantity) || 0).toFixed(2)}
                  </span>
                </div>
                {quote.tax_rate && quote.tax_amount && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">
                      Tax ({(parseFloat(quote.tax_rate) * 100).toFixed(2)}%):
                    </span>
                    <span className="text-white">${parseFloat(quote.tax_amount).toFixed(2)}</span>
                  </div>
                )}
                {quote.shipping_cost && parseFloat(quote.shipping_cost) > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Shipping:</span>
                    <span className="text-white">${parseFloat(quote.shipping_cost).toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm font-medium pt-2 border-t border-gray-700">
                  <span className="text-white">Total:</span>
                  <span className="text-green-400 text-lg font-bold">
                    ${parseFloat(quote.total_price || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Customer */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Customer</h4>
              <div className="text-sm">
                <p className="text-white">{quote.customer_name || "No name"}</p>
                <p className="text-gray-400">{quote.customer_email || "No email"}</p>
                {quote.customer_id && (
                  <p className="text-blue-400 text-xs mt-1">Linked to Customer #{quote.customer_id}</p>
                )}
              </div>
            </div>

            {/* Product Image */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Product Image</h4>
              {imageUrl ? (
                <div className="space-y-3">
                  <img
                    src={imageUrl}
                    alt="Product"
                    className="max-h-48 rounded-lg object-contain bg-gray-900"
                    onError={() => setImageUrl(null)}
                  />
                  <div className="flex gap-2">
                    <label className="px-3 py-1.5 text-sm bg-gray-700 text-white rounded cursor-pointer hover:bg-gray-600">
                      Replace
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageUpload}
                        className="hidden"
                        disabled={uploadingImage}
                      />
                    </label>
                    <button
                      onClick={handleImageDelete}
                      className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ) : (
                <div className="border-2 border-dashed border-gray-700 rounded-lg p-4 text-center">
                  <label className="cursor-pointer">
                    <div className="text-gray-400 mb-2">
                      {uploadingImage ? (
                        "Uploading..."
                      ) : (
                        <>
                          <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          Click to upload product image
                        </>
                      )}
                    </div>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                      className="hidden"
                      disabled={uploadingImage}
                    />
                    <span className="text-xs text-gray-500">PNG, JPG, WebP up to 5MB</span>
                  </label>
                </div>
              )}
            </div>

            {/* Validity */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Validity</h4>
              <p className={`text-sm ${isExpired ? "text-red-400" : "text-white"}`}>
                {isExpired ? "Expired on " : "Valid until "}
                {new Date(quote.expires_at).toLocaleDateString()}
              </p>
            </div>

            {/* Notes */}
            {(quote.customer_notes || quote.admin_notes) && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Notes</h4>
                {quote.customer_notes && (
                  <p className="text-sm text-white mb-2">
                    <span className="text-gray-400">Customer: </span>
                    {quote.customer_notes}
                  </p>
                )}
                {quote.admin_notes && (
                  <p className="text-sm text-white">
                    <span className="text-gray-400">Internal: </span>
                    {quote.admin_notes}
                  </p>
                )}
              </div>
            )}

            {/* Linked Order */}
            {quote.sales_order_id && (
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                <p className="text-green-400 text-sm">
                  Converted to Order #{quote.sales_order_id}
                  {quote.converted_at && ` on ${new Date(quote.converted_at).toLocaleDateString()}`}
                </p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 pt-4 border-t border-gray-700 space-y-3">
            {/* Primary Actions */}
            <div className="flex flex-wrap gap-2">
              {quote.status === "pending" && (
                <>
                  <button
                    onClick={() => onUpdateStatus(quote.id, "approved")}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => {
                      const reason = prompt("Rejection reason:");
                      if (reason !== null) {
                        onUpdateStatus(quote.id, "rejected", reason);
                      }
                    }}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                  >
                    Reject
                  </button>
                </>
              )}

              {quote.status === "approved" && (
                <button
                  onClick={() => onUpdateStatus(quote.id, "accepted")}
                  className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700"
                >
                  Mark as Accepted
                </button>
              )}

              {canConvert && (
                <button
                  onClick={() => onConvert(quote.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  Convert to Order
                </button>
              )}
            </div>

            {/* Secondary Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => onPrintPDF(quote)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print
              </button>
              <button
                onClick={() => onDownloadPDF(quote)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download PDF
              </button>
              <button
                onClick={() => onCopyLink(quote)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy Link
              </button>
              <button
                onClick={() => onDuplicate(quote)}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
                Duplicate
              </button>

              {quote.status !== "converted" && (
                <>
                  <button
                    onClick={onEdit}
                    className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Edit
                  </button>
                  <button
                    onClick={() => onDelete(quote.id)}
                    className="px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
