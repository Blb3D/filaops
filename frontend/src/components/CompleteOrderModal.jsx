import { useState } from "react";
import { API_URL } from "../config/api";
import { useToast } from "./Toast";

export default function CompleteOrderModal({ productionOrder, onClose, onComplete }) {
  const toast = useToast();
  const [quantityCompleted, setQuantityCompleted] = useState(
    productionOrder.quantity_ordered || 1
  );
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const token = localStorage.getItem("adminToken");

  const quantityOrdered = productionOrder.quantity_ordered || 1;
  const isOverrun = quantityCompleted > quantityOrdered;

  const handleSubmit = async () => {
    if (quantityCompleted < 1) {
      toast.error("Quantity must be at least 1");
      return;
    }

    setSubmitting(true);
    try {
      const params = new URLSearchParams({
        quantity_completed: quantityCompleted.toString(),
      });

      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrder.id}/complete?${params}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (res.ok) {
        if (isOverrun) {
          toast.success(
            `Order completed with ${quantityCompleted - quantityOrdered} extra units (MTS overrun)`
          );
        } else {
          toast.success("Production order completed");
        }
        onComplete();
      } else {
        const err = await res.json();
        toast.error(err.detail || "Failed to complete order");
      }
    } catch (err) {
      toast.error(err.message || "Network error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">Complete Production Order</h2>
            <p className="text-gray-400 text-sm mt-1">
              {productionOrder.code} - {productionOrder.product_name || productionOrder.product_sku}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl"
          >
            &times;
          </button>
        </div>

        {/* Order Details */}
        <div className="bg-gray-800/50 rounded-lg p-4 mb-6">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">Quantity Ordered:</span>
            <span className="text-white font-medium">{quantityOrdered} units</span>
          </div>
          {productionOrder.scheduled_start && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Scheduled:</span>
              <span className="text-white">
                {new Date(productionOrder.scheduled_start).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>

        {/* Quantity Completed */}
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">
            Quantity Completed *
          </label>
          <input
            type="number"
            value={quantityCompleted}
            onChange={(e) => setQuantityCompleted(parseInt(e.target.value) || 0)}
            min="1"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-lg"
          />
          <p className="text-gray-500 text-sm mt-1">
            Enter actual quantity produced (can exceed ordered qty for MTS overruns)
          </p>
        </div>

        {/* Overrun Info Banner */}
        {isOverrun && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-blue-400 font-medium">MTS Overrun</p>
                <p className="text-blue-400/80 text-sm">
                  {quantityCompleted - quantityOrdered} extra unit{quantityCompleted - quantityOrdered > 1 ? "s" : ""} will be added to inventory as Make-to-Stock.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Under completion warning */}
        {quantityCompleted < quantityOrdered && quantityCompleted > 0 && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6">
            <div className="flex gap-3">
              <svg className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="text-yellow-400 font-medium">Partial Completion</p>
                <p className="text-yellow-400/80 text-sm">
                  Only {quantityCompleted} of {quantityOrdered} ordered will be completed.
                  Consider scrapping if the remainder failed.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={quantityCompleted < 1 || submitting}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Processing..." : "Complete Order"}
          </button>
        </div>
      </div>
    </div>
  );
}
