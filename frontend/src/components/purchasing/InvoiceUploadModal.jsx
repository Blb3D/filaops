/**
 * Invoice Upload Modal
 *
 * Allows user to upload PDF or CSV invoice files for parsing.
 * Sends to backend which uses Claude API to extract structured data.
 */
import { useState, useCallback } from "react";
import { API_URL } from "../../config/api";

export default function InvoiceUploadModal({
  onClose,
  onParsed,
  vendors = []
}) {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [preselectedVendorId, setPreselectedVendorId] = useState("");
  const [useVision, setUseVision] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFile = (selectedFile) => {
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    if (!['pdf', 'csv'].includes(ext)) {
      setError("Please upload a PDF or CSV file");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File too large. Maximum size is 10MB.");
      return;
    }
    setFile(selectedFile);
    setError(null);
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleParse = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      if (preselectedVendorId) {
        formData.append("vendor_id", preselectedVendorId);
      }
      formData.append("use_vision", useVision.toString());

      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/purchase-orders/invoices/parse`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to parse invoice");
      }

      if (!data.success) {
        throw new Error(data.error || "Failed to parse invoice");
      }

      // Pass parsed data and original file to review modal
      onParsed(data.parsed_invoice, file);
    } catch (err) {
      console.error("Invoice parse error:", err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const getFileIcon = () => {
    if (!file) return null;
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext === 'pdf') {
      return (
        <svg className="w-8 h-8 text-red-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
          <text x="8" y="17" fontSize="6" fill="currentColor" fontWeight="bold">PDF</text>
        </svg>
      );
    }
    return (
      <svg className="w-8 h-8 text-green-400" fill="currentColor" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
        <text x="7" y="17" fontSize="5" fill="currentColor" fontWeight="bold">CSV</text>
      </svg>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-xl w-full max-w-lg border border-gray-800 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Import Invoice</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? "border-blue-500 bg-blue-500/10"
                : file
                ? "border-green-500 bg-green-500/10"
                : "border-gray-700 hover:border-gray-600"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="space-y-2">
                <div className="flex items-center justify-center">
                  {getFileIcon()}
                </div>
                <p className="text-white font-medium">{file.name}</p>
                <p className="text-gray-400 text-sm">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
                <button
                  onClick={() => setFile(null)}
                  className="text-red-400 hover:text-red-300 text-sm"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <svg className="w-12 h-12 mx-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <div>
                  <p className="text-white">Drop your invoice here</p>
                  <p className="text-gray-400 text-sm">or click to browse</p>
                </div>
                <label className="inline-block px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-white text-sm cursor-pointer">
                  <input
                    type="file"
                    accept=".pdf,.csv"
                    onChange={handleFileInput}
                    className="hidden"
                  />
                  Select File
                </label>
                <p className="text-gray-500 text-xs">PDF or CSV, max 10MB</p>
              </div>
            )}
          </div>

          {/* Options */}
          <div className="space-y-4">
            {/* Vendor pre-selection */}
            <div>
              <label className="block text-gray-400 text-sm mb-1">
                Pre-select Vendor (Optional)
              </label>
              <select
                value={preselectedVendorId}
                onChange={(e) => setPreselectedVendorId(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              >
                <option value="">Auto-detect from invoice</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} {v.code ? `(${v.code})` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Vision mode toggle */}
            {file && file.name.toLowerCase().endsWith('.pdf') && (
              <label className="flex items-center gap-3 text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useVision}
                  onChange={(e) => setUseVision(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">
                  Use Vision Mode
                  <span className="text-gray-500 ml-1">(for scanned/image PDFs)</span>
                </span>
              </label>
            )}
          </div>

          {/* Error display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleParse}
            disabled={!file || uploading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-white flex items-center gap-2"
          >
            {uploading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Parsing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Parse Invoice
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
