/**
 * OperationActions - Action buttons for an operation
 *
 * Shows Start/Complete/Skip buttons based on operation status.
 * Handles API calls and validation.
 */
import { useState, useEffect } from 'react';
import { API_URL } from '../../config/api';

/**
 * Start button with blocking check
 */
function StartButton({ operation, productionOrderId, onSuccess, onError }) {
  const [loading, setLoading] = useState(false);
  const token = localStorage.getItem('adminToken');

  const handleStart = async () => {
    setLoading(true);
    try {
      // First check if operation can start (blocking issues)
      const checkRes = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/can-start`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (checkRes.ok) {
        const checkData = await checkRes.json();
        if (!checkData.can_start) {
          // Show blocking issues
          const issues = checkData.blocking_issues || [];
          const issueText = issues.map(i => `${i.product_sku}: need ${i.quantity_short} more`).join(', ');
          onError?.(`Cannot start: ${issueText || 'Materials not available'}`);
          setLoading(false);
          return;
        }
      }

      // Proceed with start
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/start`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            resource_id: operation.resource_id || null
          })
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to start operation');
      }

      onSuccess?.('Operation started');
    } catch (err) {
      onError?.(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        handleStart();
      }}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-600/30 disabled:opacity-50 transition-colors"
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-blue-400"></div>
          Checking...
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M6.3 2.841A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
          </svg>
          Start
        </>
      )}
    </button>
  );
}

/**
 * Complete button with quantity input and validation
 */
function CompleteButton({ operation, productionOrderId, onSuccess, onError }) {
  const maxQty = Number(operation.quantity_input) || 1;
  const [loading, setLoading] = useState(false);
  const [showQtyInput, setShowQtyInput] = useState(false);
  const [qtyGood, setQtyGood] = useState(maxQty);
  const [qtyBad, setQtyBad] = useState(0);
  const [validationError, setValidationError] = useState(null);
  const token = localStorage.getItem('adminToken');

  // Reset quantities when maxQty changes
  useEffect(() => {
    setQtyGood(maxQty);
    setQtyBad(0);
  }, [maxQty]);

  // Validate quantities
  const validateQuantities = () => {
    const good = Number(qtyGood) || 0;
    const bad = Number(qtyBad) || 0;
    const total = good + bad;

    if (good < 0 || bad < 0) {
      return 'Quantities cannot be negative';
    }
    if (total > maxQty) {
      return `Total (${total}) exceeds max allowed (${maxQty})`;
    }
    if (total === 0) {
      return 'Total quantity must be greater than 0';
    }
    return null;
  };

  // Check validation on qty change
  useEffect(() => {
    setValidationError(validateQuantities());
  }, [qtyGood, qtyBad]);

  const handleComplete = async () => {
    const error = validateQuantities();
    if (error) {
      setValidationError(error);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/${productionOrderId}/operations/${operation.id}/complete`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            quantity_completed: Number(qtyGood),
            quantity_scrapped: Number(qtyBad)
          })
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to complete operation');
      }

      setShowQtyInput(false);
      onSuccess?.('Operation completed');
    } catch (err) {
      onError?.(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle quantity changes with auto-adjustment
  const handleGoodChange = (value) => {
    const good = Math.max(0, Number(value) || 0);
    setQtyGood(good);
    // Auto-adjust bad if total exceeds max
    const currentBad = Number(qtyBad) || 0;
    if (good + currentBad > maxQty) {
      setQtyBad(Math.max(0, maxQty - good));
    }
  };

  const handleBadChange = (value) => {
    const bad = Math.max(0, Number(value) || 0);
    setQtyBad(bad);
    // Auto-adjust good if total exceeds max
    const currentGood = Number(qtyGood) || 0;
    if (currentGood + bad > maxQty) {
      setQtyGood(Math.max(0, maxQty - bad));
    }
  };

  // Show quantity input form
  if (showQtyInput) {
    const total = (Number(qtyGood) || 0) + (Number(qtyBad) || 0);
    const isValid = !validationError;

    return (
      <div className="mt-2 p-3 bg-gray-800/50 rounded-lg border border-gray-700" onClick={(e) => e.stopPropagation()}>
        {/* Header with max qty info */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">
            Input qty: <span className="text-white font-medium">{maxQty}</span>
          </span>
          <span className={`text-xs ${total === maxQty ? 'text-green-400' : total > maxQty ? 'text-red-400' : 'text-yellow-400'}`}>
            Total: {total}/{maxQty}
          </span>
        </div>

        {/* Quantity inputs */}
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-green-400">Good:</label>
            <input
              type="number"
              min="0"
              max={maxQty}
              value={qtyGood}
              onChange={(e) => handleGoodChange(e.target.value)}
              className="w-16 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:border-green-500 focus:ring-1 focus:ring-green-500"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-red-400">Bad:</label>
            <input
              type="number"
              min="0"
              max={maxQty}
              value={qtyBad}
              onChange={(e) => handleBadChange(e.target.value)}
              className="w-16 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white focus:border-red-500 focus:ring-1 focus:ring-red-500"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>

        {/* Validation error */}
        {validationError && (
          <div className="text-xs text-red-400 mb-2">
            ⚠ {validationError}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleComplete();
            }}
            disabled={loading || !isValid}
            className="flex-1 px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Saving...' : `Complete (${Number(qtyGood) || 0} good)`}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowQtyInput(false);
              setQtyGood(maxQty);
              setQtyBad(0);
            }}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        setShowQtyInput(true);
      }}
      disabled={loading}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-green-600/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-600/30 disabled:opacity-50 transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
      Complete ({maxQty})
    </button>
  );
}

/**
 * Skip button (opens modal)
 */
function SkipButton({ onClick }) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-yellow-600/20 text-yellow-400 border border-yellow-500/30 rounded-lg hover:bg-yellow-600/30 transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
      Skip
    </button>
  );
}

/**
 * Main component - shows appropriate buttons based on status
 */
export default function OperationActions({
  operation,
  productionOrderId,
  onSuccess,
  onError,
  onSkipClick
}) {
  if (!operation) return null;

  const { status } = operation;

  // No actions for completed or skipped
  if (['complete', 'skipped'].includes(status)) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 mt-2">
      {/* Pending/Queued: Start and Skip */}
      {['pending', 'queued'].includes(status) && (
        <>
          <StartButton
            operation={operation}
            productionOrderId={productionOrderId}
            onSuccess={onSuccess}
            onError={onError}
          />
          <SkipButton onClick={() => onSkipClick?.(operation)} />
        </>
      )}

      {/* Running: Complete only */}
      {status === 'running' && (
        <CompleteButton
          operation={operation}
          productionOrderId={productionOrderId}
          onSuccess={onSuccess}
          onError={onError}
        />
      )}
    </div>
  );
}
