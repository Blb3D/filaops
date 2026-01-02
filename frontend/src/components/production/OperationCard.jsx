import { useState } from 'react';
import ElapsedTimer from './ElapsedTimer';
import { formatDuration, formatTime } from '../../utils/formatting';

/**
 * Status configuration for visual styling
 */
const statusConfig = {
  pending: {
    icon: '○',
    label: 'Pending',
    bg: 'bg-gray-800/50',
    border: 'border-gray-700',
    iconColor: 'text-gray-400',
  },
  queued: {
    icon: '◐',
    label: 'Queued',
    bg: 'bg-blue-900/30',
    border: 'border-blue-500/30',
    iconColor: 'text-blue-400',
  },
  running: {
    icon: '●',
    label: 'Running',
    bg: 'bg-purple-900/30',
    border: 'border-purple-500/50',
    iconColor: 'text-purple-400 animate-pulse',
  },
  complete: {
    icon: '✓',
    label: 'Complete',
    bg: 'bg-green-900/20',
    border: 'border-green-500/30',
    iconColor: 'text-green-400',
  },
  skipped: {
    icon: '⊘',
    label: 'Skipped',
    bg: 'bg-yellow-900/20',
    border: 'border-yellow-500/30',
    iconColor: 'text-yellow-400',
  },
};

/**
 * OperationCard - Single operation with status-specific actions
 *
 * Shows operation details and provides actions based on current status:
 * - pending: Schedule, Skip
 * - queued: Start, Skip
 * - running: Complete (with qty inputs), Skip
 * - complete/skipped: Read-only view
 */
export default function OperationCard({
  operation,
  maxQty,
  onSchedule,
  onStart,
  onComplete,
  onSkip,
  loading,
  expanded: controlledExpanded,
  onToggleExpand,
}) {
  // Local state for qty inputs - parse to integers for display consistency
  const [qtyGood, setQtyGood] = useState(Math.floor(parseFloat(maxQty) || 0));
  const [qtyBad, setQtyBad] = useState(0);
  const [scrapReason, setScrapReason] = useState('');

  // Scrap reason options
  const scrapReasons = [
    { value: '', label: 'Select reason...' },
    { value: 'adhesion', label: 'Adhesion Failure' },
    { value: 'layer_shift', label: 'Layer Shift' },
    { value: 'stringing', label: 'Stringing' },
    { value: 'warping', label: 'Warping' },
    { value: 'nozzle_clog', label: 'Nozzle Clog' },
    { value: 'damage', label: 'Physical Damage' },
    { value: 'quality_fail', label: 'Quality Fail' },
    { value: 'other', label: 'Other' },
  ];

  const config = statusConfig[operation.status] || statusConfig.pending;
  const isExpanded = controlledExpanded ?? (operation.status === 'running');

  // Calculate times
  const plannedMinutes =
    (parseFloat(operation.planned_setup_minutes) || 0) +
    (parseFloat(operation.planned_run_minutes) || 0);

  const actualMinutes =
    (parseFloat(operation.actual_setup_minutes) || 0) +
    (parseFloat(operation.actual_run_minutes) || 0);

  // Parse maxQty to integer for calculations
  const maxQtyInt = Math.floor(parseFloat(maxQty) || 0);

  // Handle qty changes with validation
  const handleQtyGoodChange = (value) => {
    const v = Math.max(0, Math.min(maxQtyInt, parseInt(value) || 0));
    setQtyGood(v);
    // Auto-adjust bad qty if total exceeds max
    if (v + qtyBad > maxQtyInt) {
      setQtyBad(maxQtyInt - v);
    }
  };

  const handleQtyBadChange = (value) => {
    const v = Math.max(0, Math.min(maxQtyInt - qtyGood, parseInt(value) || 0));
    setQtyBad(v);
  };

  const handleComplete = () => {
    if (onComplete) {
      onComplete(operation.id, qtyGood, qtyBad, qtyBad > 0 ? scrapReason : null);
    }
  };

  // Check if scrap reason is required and provided
  const scrapReasonRequired = qtyBad > 0;
  const scrapReasonValid = !scrapReasonRequired || scrapReason !== '';

  return (
    <div
      className={`rounded-lg border ${config.border} ${config.bg} overflow-hidden transition-all duration-150`}
    >
      {/* Header - Always visible */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          <span className={`text-lg ${config.iconColor}`}>{config.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-medium">
                {operation.operation_code || `Op ${operation.sequence}`}
              </span>
              {operation.operation_name && (
                <span className="text-gray-400">— {operation.operation_name}</span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              {operation.work_center_name || 'No work center'}
              {operation.resource_name && (
                <span className="text-blue-400"> → {operation.resource_name}</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Timer for running ops */}
          {operation.status === 'running' && operation.actual_start && (
            <ElapsedTimer
              startTime={operation.actual_start}
              className="text-purple-400 text-sm"
            />
          )}

          {/* Time estimate/actual */}
          {operation.status === 'complete' ? (
            <span className="text-gray-400 text-sm font-mono">
              {formatDuration(actualMinutes)}
            </span>
          ) : (
            <span className="text-gray-500 text-sm font-mono">
              ~{formatDuration(plannedMinutes)}
            </span>
          )}

          {/* Expand indicator */}
          <span className="text-gray-500 text-xs">
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-gray-700/50 p-4 space-y-4">
          {/* Status-specific content */}

          {/* PENDING - Show schedule option */}
          {operation.status === 'pending' && (
            <div className="space-y-3">
              <div className="text-sm text-gray-400">
                Not yet scheduled. Assign to a resource to begin.
              </div>
              {operation.materials?.length > 0 && (
                <div className="text-xs text-gray-500">
                  Materials:{' '}
                  {operation.materials
                    .map((m) => `${m.item_name || m.item_code} (${m.quantity_required})`)
                    .join(', ')}
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => onSchedule?.(operation)}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  Schedule
                </button>
                <button
                  onClick={() => onSkip?.(operation)}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* QUEUED - Show start option */}
          {operation.status === 'queued' && (
            <div className="space-y-3">
              <div className="text-sm text-gray-400">
                Scheduled
                {operation.scheduled_start && (
                  <span>
                    {' '}for {formatTime(operation.scheduled_start)}
                  </span>
                )}
                {operation.resource_name && (
                  <span className="text-blue-400"> on {operation.resource_name}</span>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onStart?.(operation)}
                  disabled={loading}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  ▶ Start Operation
                </button>
                <button
                  onClick={() => onSkip?.(operation)}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* RUNNING - Show complete form */}
          {operation.status === 'running' && (
            <div className="space-y-4">
              <div className="text-sm text-gray-400">
                Started {operation.actual_start && formatTime(operation.actual_start)}
                {operation.resource_name && (
                  <span className="text-blue-400"> on {operation.resource_name}</span>
                )}
              </div>

              {/* Quantity inputs */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Qty Good
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={maxQtyInt}
                    value={qtyGood}
                    onChange={(e) => handleQtyGoodChange(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-lg font-mono focus:border-green-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Qty Bad
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={maxQtyInt - qtyGood}
                    value={qtyBad}
                    onChange={(e) => handleQtyBadChange(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-lg font-mono focus:border-red-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Scrap reason dropdown - only shown when qty bad > 0 */}
              {qtyBad > 0 && (
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    Scrap Reason <span className="text-red-400">*</span>
                  </label>
                  <select
                    value={scrapReason}
                    onChange={(e) => setScrapReason(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white focus:border-red-500 focus:outline-none"
                  >
                    {scrapReasons.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={handleComplete}
                  disabled={loading || (qtyGood + qtyBad === 0 && maxQtyInt > 0) || !scrapReasonValid}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Completing...' : maxQtyInt === 0 ? 'Complete (No Input)' : 'Complete Operation'}
                </button>
                <button
                  onClick={() => onSkip?.(operation)}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* COMPLETE - Show summary */}
          {operation.status === 'complete' && (
            <div className="text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-500">Qty Completed</span>
                <span className="text-green-400 font-mono">
                  {operation.quantity_completed || 0}
                </span>
              </div>
              {operation.quantity_scrapped > 0 && (
                <>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Qty Scrapped</span>
                    <span className="text-red-400 font-mono">
                      {operation.quantity_scrapped}
                    </span>
                  </div>
                  {operation.scrap_reason && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Scrap Reason</span>
                      <span className="text-red-400">
                        {scrapReasons.find(r => r.value === operation.scrap_reason)?.label || operation.scrap_reason}
                      </span>
                    </div>
                  )}
                </>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">Actual Time</span>
                <span className="text-gray-300 font-mono">
                  {formatDuration(actualMinutes)}
                </span>
              </div>
              {operation.actual_start && operation.actual_end && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Completed</span>
                  <span className="text-gray-300">
                    {formatTime(operation.actual_end)}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* SKIPPED - Show reason */}
          {operation.status === 'skipped' && (
            <div className="text-sm">
              <div className="text-yellow-400/80">
                {operation.notes?.replace(/^SKIPPED:\s*/i, '') || 'No reason provided'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
