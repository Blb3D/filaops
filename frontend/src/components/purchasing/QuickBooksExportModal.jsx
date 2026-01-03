/**
 * QuickBooksExportModal - Export purchase orders for QuickBooks
 *
 * Features:
 * - Date range selection
 * - Export type (Expense, Bill, Check)
 * - Format selection (CSV, IIF)
 * - Preview before download
 * - Include/exclude tax and shipping
 */
import React, { useState, useEffect } from "react";
import {
  X,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Calendar,
  DollarSign,
  Loader2,
  AlertCircle,
  CheckCircle,
  CreditCard,
  Receipt,
  Wallet,
} from "lucide-react";
import api from "../../api/axios";

// Export type options
const EXPORT_TYPES = [
  {
    value: "expense",
    label: "Expenses",
    description: "Direct expenses (credit card/cash purchases)",
    icon: CreditCard,
    recommended: true,
  },
  {
    value: "bill",
    label: "Bills (AP)",
    description: "Creates vendor bills in Accounts Payable",
    icon: Receipt,
  },
  {
    value: "check",
    label: "Check Register",
    description: "For check payments",
    icon: Wallet,
  },
];

// Format options
const FORMAT_OPTIONS = [
  {
    value: "csv",
    label: "CSV",
    description: "Works with QuickBooks Online",
    icon: FileSpreadsheet,
    recommended: true,
  },
  {
    value: "iif",
    label: "IIF",
    description: "QuickBooks Desktop only",
    icon: FileText,
  },
];

// Format currency
const formatCurrency = (amount) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount || 0);
};

export default function QuickBooksExportModal({ isOpen, onClose }) {
  // Date range - default to current month
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

  const [startDate, setStartDate] = useState(
    firstOfMonth.toISOString().split("T")[0]
  );
  const [endDate, setEndDate] = useState(today.toISOString().split("T")[0]);

  // Export options
  const [exportType, setExportType] = useState("expense");
  const [format, setFormat] = useState("csv");
  const [includeTax, setIncludeTax] = useState(true);
  const [includeShipping, setIncludeShipping] = useState(true);
  const [includeLineDetail, setIncludeLineDetail] = useState(false);

  // State
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  // Load preview when options change
  useEffect(() => {
    if (!isOpen) return;

    const loadPreview = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await api.post("/exports/quickbooks/preview", {
          start_date: startDate,
          end_date: endDate,
          export_type: exportType,
          format: format,
          include_tax: includeTax,
          include_shipping: includeShipping,
          include_line_detail: includeLineDetail,
          status_filter: ["received", "closed"],
        });
        setPreview(response.data);
      } catch (err) {
        console.error("Failed to load preview:", err);
        setError(err.response?.data?.detail || "Failed to load preview");
        setPreview(null);
      } finally {
        setIsLoading(false);
      }
    };

    // Debounce the preview load
    const timer = setTimeout(loadPreview, 300);
    return () => clearTimeout(timer);
  }, [
    isOpen,
    startDate,
    endDate,
    exportType,
    format,
    includeTax,
    includeShipping,
    includeLineDetail,
  ]);

  // Handle export/download
  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      const response = await api.post(
        "/exports/quickbooks/export",
        {
          start_date: startDate,
          end_date: endDate,
          export_type: exportType,
          format: format,
          include_tax: includeTax,
          include_shipping: includeShipping,
          include_line_detail: includeLineDetail,
          status_filter: ["received", "closed"],
        },
        {
          responseType: "blob",
        }
      );

      // Create download link
      const blob = new Blob([response.data], {
        type: format === "csv" ? "text/csv" : "text/plain",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `FilaOps_PO_Export_${startDate}_${endDate}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Close modal on success
      onClose();
    } catch (err) {
      console.error("Export failed:", err);
      setError(err.response?.data?.detail || "Export failed");
    } finally {
      setIsExporting(false);
    }
  };

  // Quick date presets
  const setDatePreset = (preset) => {
    const now = new Date();
    let start, end;

    switch (preset) {
      case "today":
        start = end = now;
        break;
      case "yesterday":
        start = end = new Date(now.setDate(now.getDate() - 1));
        break;
      case "thisWeek":
        start = new Date(now.setDate(now.getDate() - now.getDay()));
        end = new Date();
        break;
      case "lastWeek": {
        const lastWeekEnd = new Date(
          now.setDate(now.getDate() - now.getDay() - 1)
        );
        start = new Date(lastWeekEnd);
        start.setDate(start.getDate() - 6);
        end = lastWeekEnd;
        break;
      }
      case "thisMonth":
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        end = new Date();
        break;
      case "lastMonth":
        start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        end = new Date(now.getFullYear(), now.getMonth(), 0);
        break;
      case "thisQuarter": {
        const quarter = Math.floor(now.getMonth() / 3);
        start = new Date(now.getFullYear(), quarter * 3, 1);
        end = new Date();
        break;
      }
      case "thisYear":
        start = new Date(now.getFullYear(), 0, 1);
        end = new Date();
        break;
      default:
        return;
    }

    setStartDate(start.toISOString().split("T")[0]);
    setEndDate(end.toISOString().split("T")[0]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-6 h-6 text-green-400" />
            <h2 className="text-xl font-semibold text-white">
              Export for QuickBooks
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Calendar className="w-4 h-4 inline mr-1" />
              Date Range
            </label>
            <div className="flex items-center gap-3 mb-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              />
              <span className="text-gray-500">to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              />
            </div>
            {/* Quick presets */}
            <div className="flex flex-wrap gap-2">
              {[
                { key: "today", label: "Today" },
                { key: "thisWeek", label: "This Week" },
                { key: "lastWeek", label: "Last Week" },
                { key: "thisMonth", label: "This Month" },
                { key: "lastMonth", label: "Last Month" },
                { key: "thisQuarter", label: "This Quarter" },
                { key: "thisYear", label: "YTD" },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setDatePreset(key)}
                  className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300 transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Export Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Export Type
            </label>
            <div className="grid grid-cols-3 gap-3">
              {EXPORT_TYPES.map((type) => {
                const Icon = type.icon;
                const isSelected = exportType === type.value;
                return (
                  <button
                    key={type.value}
                    onClick={() => setExportType(type.value)}
                    className={`p-3 rounded-lg border text-left transition-colors ${
                      isSelected
                        ? "bg-blue-900/30 border-blue-500 text-white"
                        : "bg-gray-750 border-gray-600 hover:border-gray-500 text-gray-300"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{type.label}</span>
                      {type.recommended && (
                        <span className="text-xs bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded">
                          Recommended
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{type.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Format */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              {FORMAT_OPTIONS.map((fmt) => {
                const Icon = fmt.icon;
                const isSelected = format === fmt.value;
                return (
                  <button
                    key={fmt.value}
                    onClick={() => setFormat(fmt.value)}
                    className={`p-3 rounded-lg border text-left transition-colors ${
                      isSelected
                        ? "bg-blue-900/30 border-blue-500 text-white"
                        : "bg-gray-750 border-gray-600 hover:border-gray-500 text-gray-300"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{fmt.label}</span>
                      {fmt.recommended && (
                        <span className="text-xs bg-green-900/50 text-green-400 px-1.5 py-0.5 rounded">
                          Recommended
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{fmt.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Options */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Include
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeTax}
                  onChange={(e) => setIncludeTax(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-300">Tax amounts</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeShipping}
                  onChange={(e) => setIncludeShipping(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-300">Shipping costs</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeLineDetail}
                  onChange={(e) => setIncludeLineDetail(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-300">
                  Line item detail (separate row per item)
                </span>
              </label>
            </div>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Eye className="w-4 h-4 inline mr-1" />
              Preview
            </label>
            {isLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Loading preview...
              </div>
            ) : preview ? (
              <div className="bg-gray-750 rounded-lg border border-gray-600 p-4">
                {/* Summary */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">
                      {preview.total_pos}
                    </div>
                    <div className="text-xs text-gray-500">Purchase Orders</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">
                      {formatCurrency(preview.total_amount)}
                    </div>
                    <div className="text-xs text-gray-500">Total Amount</div>
                  </div>
                  <div className="text-center">
                    <div className="text-sm text-gray-300">
                      {preview.date_range}
                    </div>
                    <div className="text-xs text-gray-500">Date Range</div>
                  </div>
                </div>

                {/* Preview lines */}
                {preview.lines?.length > 0 ? (
                  <div className="max-h-40 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="text-gray-500 text-xs uppercase">
                        <tr>
                          <th className="text-left py-1">Date</th>
                          <th className="text-left py-1">Vendor</th>
                          <th className="text-left py-1">PO #</th>
                          <th className="text-right py-1">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="text-gray-300">
                        {preview.lines.slice(0, 10).map((line, idx) => (
                          <tr key={idx} className="border-t border-gray-700">
                            <td className="py-1">{line.date}</td>
                            <td className="py-1 truncate max-w-[150px]">
                              {line.vendor}
                            </td>
                            <td className="py-1">{line.po_number}</td>
                            <td className="py-1 text-right">
                              {formatCurrency(line.amount)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {preview.lines.length > 10 && (
                      <p className="text-xs text-gray-500 mt-2 text-center">
                        ... and {preview.lines.length - 10} more lines
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-4">
                    No purchase orders found for this date range
                  </p>
                )}
              </div>
            ) : (
              <div className="bg-gray-750 rounded-lg border border-gray-600 p-8 text-center text-gray-500">
                Select options to see preview
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-700 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            Only exporting POs with status: Received, Closed
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting || !preview?.total_pos}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
            >
              {isExporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Download {format.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
