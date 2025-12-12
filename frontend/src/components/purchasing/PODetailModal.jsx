/**
 * PODetailModal - View purchase order details with actions
 */
import { useState } from "react";

const statusColors = {
  draft: "bg-gray-600 text-gray-100",
  ordered: "bg-blue-600/20 text-blue-400",
  shipped: "bg-purple-600/20 text-purple-400",
  received: "bg-green-600/20 text-green-400",
  closed: "bg-gray-600/20 text-gray-400",
  cancelled: "bg-red-600/20 text-red-400",
};

export default function PODetailModal({
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
