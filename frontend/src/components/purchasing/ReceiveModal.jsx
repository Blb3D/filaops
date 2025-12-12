/**
 * ReceiveModal - Enhanced receive items workflow
 *
 * Features:
 * - Prominent product SKU and name display
 * - Large, touch-friendly quantity inputs
 * - "Receive All" quick button per line
 * - Running total of items being received
 * - Visual indicators for partial/full receipt
 * - Auto-generate lot number option
 */
import { useState, useMemo } from "react";
import { useToast } from "../Toast";

export default function ReceiveModal({ po, onClose, onReceive }) {
  const toast = useToast();
  const [lines, setLines] = useState(
    po.lines
      ?.filter(
        (l) => parseFloat(l.quantity_received) < parseFloat(l.quantity_ordered)
      )
      .map((l) => ({
        line_id: l.id,
        line_number: l.line_number,
        quantity_to_receive: parseFloat(l.quantity_ordered) - parseFloat(l.quantity_received),
        quantity_ordered: parseFloat(l.quantity_ordered),
        quantity_already_received: parseFloat(l.quantity_received),
        remaining: parseFloat(l.quantity_ordered) - parseFloat(l.quantity_received),
        product_sku: l.product_sku,
        product_name: l.product_name,
        lot_number: "",
        notes: "",
      })) || []
  );
  const [notes, setNotes] = useState("");
  const [autoGenerateLot, setAutoGenerateLot] = useState(false);

  // Calculate running totals
  const totals = useMemo(() => {
    const itemsToReceive = lines.filter(l => parseFloat(l.quantity_to_receive) > 0).length;
    const totalQty = lines.reduce((sum, l) => sum + (parseFloat(l.quantity_to_receive) || 0), 0);
    return { itemsToReceive, totalQty };
  }, [lines]);

  const updateLine = (index, field, value) => {
    const newLines = [...lines];
    newLines[index] = { ...newLines[index], [field]: value };
    setLines(newLines);
  };

  const receiveAll = (index) => {
    const newLines = [...lines];
    newLines[index].quantity_to_receive = newLines[index].remaining;
    setLines(newLines);
  };

  const receiveNone = (index) => {
    const newLines = [...lines];
    newLines[index].quantity_to_receive = 0;
    setLines(newLines);
  };

  const receiveAllLines = () => {
    setLines(lines.map(l => ({ ...l, quantity_to_receive: l.remaining })));
  };

  const generateLotNumber = (lineNumber) => {
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    return `${po.po_number}-L${lineNumber}-${today}`;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const receiveData = {
      lines: lines
        .filter((l) => parseFloat(l.quantity_to_receive) > 0)
        .map((l) => ({
          line_id: l.line_id,
          quantity_received: parseFloat(l.quantity_to_receive),
          lot_number: autoGenerateLot && !l.lot_number
            ? generateLotNumber(l.line_number)
            : (l.lot_number || null),
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

  const getProgressPercent = (line) => {
    const total = line.quantity_already_received + (parseFloat(line.quantity_to_receive) || 0);
    return Math.min(100, (total / line.quantity_ordered) * 100);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-4xl w-full mx-auto p-6 max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8 8-4-4M4 12l4-4 4 4" />
                </svg>
                Receive Items
              </h3>
              <p className="text-gray-400 mt-1">
                {po.po_number} • {po.vendor_name}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-1"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Quick Actions Bar */}
          {lines.length > 0 && (
            <div className="flex items-center justify-between mb-4 p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={receiveAllLines}
                  className="px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg text-sm font-medium transition-colors"
                >
                  Receive All Items
                </button>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="autoLot"
                    checked={autoGenerateLot}
                    onChange={(e) => setAutoGenerateLot(e.target.checked)}
                    className="rounded bg-gray-700 border-gray-600 text-blue-600"
                  />
                  <label htmlFor="autoLot" className="text-sm text-gray-400">
                    Auto-generate lot numbers
                  </label>
                </div>
              </div>
              <div className="text-sm text-gray-400">
                <span className="text-white font-medium">{totals.itemsToReceive}</span> items •
                <span className="text-white font-medium ml-1">{totals.totalQty.toFixed(2)}</span> qty
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {lines.length === 0 ? (
              <div className="text-center py-12">
                <svg className="w-16 h-16 mx-auto text-green-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-300 text-lg">All items have been received</p>
                <p className="text-gray-500 mt-1">This purchase order is fully received</p>
              </div>
            ) : (
              <div className="space-y-4">
                {lines.map((line, index) => {
                  const progress = getProgressPercent(line);
                  const isFullyReceiving = parseFloat(line.quantity_to_receive) >= line.remaining - 0.001;
                  const isPartiallyReceiving = parseFloat(line.quantity_to_receive) > 0 && !isFullyReceiving;
                  const isNotReceiving = parseFloat(line.quantity_to_receive) === 0;

                  return (
                    <div
                      key={line.line_id}
                      className={`bg-gray-800/50 rounded-xl overflow-hidden transition-all ${
                        isNotReceiving ? 'opacity-60' : ''
                      }`}
                    >
                      {/* Progress Bar */}
                      <div className="h-1 bg-gray-700">
                        <div
                          className={`h-full transition-all ${
                            progress >= 100 ? 'bg-green-500' :
                            progress > 0 ? 'bg-blue-500' : 'bg-gray-600'
                          }`}
                          style={{ width: `${progress}%` }}
                        />
                      </div>

                      <div className="p-4">
                        {/* Product Info Row */}
                        <div className="flex justify-between items-start mb-4">
                          <div className="flex-1">
                            <div className="text-lg font-semibold text-white">
                              {line.product_sku}
                            </div>
                            <div className="text-gray-400">
                              {line.product_name}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm text-gray-400">
                              {line.quantity_already_received.toFixed(2)} of {line.quantity_ordered.toFixed(2)} received
                            </div>
                            <div className={`text-sm font-medium ${
                              isFullyReceiving ? 'text-green-400' :
                              isPartiallyReceiving ? 'text-yellow-400' : 'text-gray-500'
                            }`}>
                              {line.remaining.toFixed(2)} remaining
                            </div>
                          </div>
                        </div>

                        {/* Input Row */}
                        <div className="grid grid-cols-12 gap-3 items-end">
                          {/* Quantity Input - Large and prominent */}
                          <div className="col-span-4">
                            <label className="block text-xs text-gray-400 mb-1">
                              Qty to Receive
                            </label>
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                value={line.quantity_to_receive}
                                onChange={(e) =>
                                  updateLine(index, "quantity_to_receive", e.target.value)
                                }
                                min="0"
                                max={line.remaining}
                                step="0.01"
                                className="w-full bg-gray-700 border-2 border-gray-600 focus:border-blue-500 rounded-lg px-4 py-3 text-white text-lg font-medium"
                              />
                            </div>
                          </div>

                          {/* Quick Actions */}
                          <div className="col-span-2 flex flex-col gap-1">
                            <button
                              type="button"
                              onClick={() => receiveAll(index)}
                              className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                                isFullyReceiving
                                  ? 'bg-green-600/30 text-green-400'
                                  : 'bg-gray-700 hover:bg-green-600/20 text-gray-300 hover:text-green-400'
                              }`}
                            >
                              All ({line.remaining.toFixed(0)})
                            </button>
                            <button
                              type="button"
                              onClick={() => receiveNone(index)}
                              className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                                isNotReceiving
                                  ? 'bg-gray-600/30 text-gray-400'
                                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                              }`}
                            >
                              None
                            </button>
                          </div>

                          {/* Lot Number */}
                          <div className="col-span-3">
                            <label className="block text-xs text-gray-400 mb-1">
                              Lot Number
                            </label>
                            <input
                              type="text"
                              value={line.lot_number}
                              onChange={(e) =>
                                updateLine(index, "lot_number", e.target.value)
                              }
                              placeholder={autoGenerateLot ? "(auto)" : "Optional"}
                              disabled={autoGenerateLot}
                              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                          </div>

                          {/* Notes */}
                          <div className="col-span-3">
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
                              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-white"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Receipt Notes */}
            {lines.length > 0 && (
              <div className="border-t border-gray-800 pt-4">
                <label className="block text-sm text-gray-400 mb-1">
                  Receipt Notes (applies to all items)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Optional notes for this receipt transaction"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            )}

            {/* Footer */}
            <div className="flex justify-between items-center pt-4 border-t border-gray-800">
              <div className="text-sm text-gray-400">
                {totals.itemsToReceive > 0 && (
                  <>
                    Receiving <span className="text-white font-medium">{totals.itemsToReceive}</span> line items,
                    total qty: <span className="text-white font-medium">{totals.totalQty.toFixed(2)}</span>
                  </>
                )}
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={totals.itemsToReceive === 0}
                  className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg text-white font-medium flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Receive Items
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
