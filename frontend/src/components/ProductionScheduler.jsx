import { useState, useEffect, useRef, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useFeatureFlags } from "../hooks/useFeatureFlags";
import { API_URL } from "../config/api";

/**
 * Production Scheduler - Gantt/Calendar View with Drag-and-Drop
 *
 * Visual scheduling interface showing:
 * - Machines/resources on Y-axis
 * - Time slots on X-axis
 * - Production orders as draggable blocks
 * - Capacity visualization
 */
export default function ProductionScheduler({ onScheduleUpdate }) {
  const { isPro, loading: flagsLoading } = useFeatureFlags();
  const [machines, setMachines] = useState([]);
  const [productionOrders, setProductionOrders] = useState([]);
  const [unscheduledOrders, setUnscheduledOrders] = useState([]);
  const [viewMode, setViewMode] = useState("day"); // day, week, month
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draggedOrder, setDraggedOrder] = useState(null);
  const [hoveredSlot, setHoveredSlot] = useState(null);

  const token = localStorage.getItem("adminToken");
  const schedulerRef = useRef(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  useEffect(() => {
    fetchMachines();
    fetchProductionOrders();
  }, [selectedDate, viewMode]);

  const fetchMachines = async () => {
    try {
      // Get machine work centers
      const wcRes = await fetch(
        `${API_URL}/api/v1/work-centers/?center_type=machine&active_only=true`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!wcRes.ok) throw new Error("Failed to fetch work centers");
      const workCenters = await wcRes.json();

      // Get all resources from machine work centers
      const allResources = [];
      for (const wc of workCenters) {
        try {
          const resRes = await fetch(
            `${API_URL}/api/v1/work-centers/${wc.id}/resources?active_only=true`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (resRes.ok) {
            const resources = await resRes.json();
            allResources.push(
              ...resources.map((r) => ({ ...r, work_center: wc }))
            );
          }
        } catch (err) {
          // Failed to fetch resources for work center - will skip this work center
        }
      }

      setMachines(allResources);
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchProductionOrders = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/production-orders/?status=released&limit=200`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error("Failed to fetch production orders");

      const data = await res.json();
      const orders = Array.isArray(data) ? data : data.items || [];

      // Separate scheduled and unscheduled orders
      const scheduled = orders.filter(
        (o) => o.scheduled_start && o.scheduled_end
      );
      const unscheduled = orders.filter(
        (o) => !o.scheduled_start || !o.scheduled_end
      );

      setProductionOrders(scheduled);
      setUnscheduledOrders(unscheduled);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getTimeSlots = () => {
    const slots = [];
    const start = new Date(selectedDate);
    start.setHours(0, 0, 0, 0);

    const hours = viewMode === "day" ? 24 : viewMode === "week" ? 168 : 720;

    for (let i = 0; i < hours; i++) {
      const time = new Date(start);
      time.setHours(time.getHours() + i);
      slots.push(time);
    }

    return slots;
  };

  const getOrderPosition = (order) => {
    if (!order.scheduled_start || !order.scheduled_end) return null;

    const start = new Date(order.scheduled_start);
    const end = new Date(order.scheduled_end);
    const viewStart = new Date(selectedDate);
    viewStart.setHours(0, 0, 0, 0);

    const startOffset = (start - viewStart) / (1000 * 60 * 60); // hours
    const duration = (end - start) / (1000 * 60 * 60); // hours

    // Find which machine this order is assigned to
    // Note: print_jobs may not be in the response, check assigned_to first
    const machineIndex = machines.findIndex((m) => {
      if (order.assigned_to === m.code) return true;
      // Check print_jobs if available
      if (order.print_jobs && Array.isArray(order.print_jobs)) {
        return order.print_jobs.some((pj) => pj.printer_id === m.id);
      }
      return false;
    });

    return {
      machineIndex: machineIndex >= 0 ? machineIndex : 0,
      startOffset,
      duration,
      order,
    };
  };

  const handleDragStart = (event) => {
    const { active } = event;
    const orderId = parseInt(active.id);
    const order = [...productionOrders, ...unscheduledOrders].find(
      (o) => o.id === orderId
    );
    setDraggedOrder(order);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setDraggedOrder(null);
    setHoveredSlot(null);

    if (!over) return;

    // Ensure over.id is a string with expected format
    const overId = String(over.id);
    if (!overId.includes("-slot-")) return;

    const orderId = parseInt(active.id);
    const order = [...productionOrders, ...unscheduledOrders].find(
      (o) => o.id === orderId
    );

    // Parse drop target (format: "machine-{index}-slot-{hour}")
    const [machinePart, slotPart] = overId.split("-slot-");
    const machineIndex = parseInt(machinePart.replace("machine-", ""));
    const slotHour = parseInt(slotPart);

    if (isNaN(machineIndex) || isNaN(slotHour)) return;

    const machine = machines[machineIndex];
    if (!machine) return;

    // Calculate scheduled times
    const viewStart = new Date(selectedDate);
    viewStart.setHours(0, 0, 0, 0);
    const scheduledStart = new Date(viewStart);
    scheduledStart.setHours(scheduledStart.getHours() + slotHour);

    // Estimate duration (default 2 hours, or use order's estimated time)
    const estimatedHours = order.estimated_time_minutes
      ? order.estimated_time_minutes / 60
      : 2;
    const scheduledEnd = new Date(scheduledStart);
    scheduledEnd.setHours(scheduledEnd.getHours() + estimatedHours);

    // Check for conflicts
    const conflicts = await checkConflicts(
      machine.id,
      scheduledStart,
      scheduledEnd,
      orderId
    );
    if (conflicts.length > 0) {
      const confirm = window.confirm(
        `Conflict detected with ${conflicts.length} order(s). Schedule anyway?`
      );
      if (!confirm) return;
    }

    // Schedule the order
    await scheduleOrder(orderId, machine.id, scheduledStart, scheduledEnd);
  };

  const handleDragOver = (event) => {
    const { over } = event;
    if (over) {
      setHoveredSlot(over.id);
    }
  };

  const checkConflicts = async (machineId, start, end, excludeOrderId) => {
    // Get all scheduled orders for this machine
    const machineOrders = productionOrders.filter((o) => {
      if (o.id === excludeOrderId) return false;
      const pj = o.print_jobs?.find((pj) => pj.printer_id === machineId);
      return (
        pj || o.assigned_to === machines.find((m) => m.id === machineId)?.code
      );
    });

    // Check for time overlaps
    const conflicts = machineOrders.filter((o) => {
      if (!o.scheduled_start || !o.scheduled_end) return false;
      const oStart = new Date(o.scheduled_start);
      const oEnd = new Date(o.scheduled_end);
      return start < oEnd && end > oStart;
    });

    return conflicts;
  };

  const scheduleOrder = async (
    orderId,
    machineId,
    scheduledStart,
    scheduledEnd
  ) => {
    try {
      // Update production order with schedule
      const updateRes = await fetch(
        `${API_URL}/api/v1/production-orders/${orderId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            scheduled_start: scheduledStart.toISOString(),
            scheduled_end: scheduledEnd.toISOString(),
          }),
        }
      );

      if (!updateRes.ok) {
        const err = await updateRes.json();
        throw new Error(err.detail || "Failed to schedule order");
      }

      // If machine is selected, also assign it
      const machine = machines.find((m) => m.id === machineId);
      if (machine) {
        const startRes = await fetch(
          `${API_URL}/api/v1/admin/fulfillment/queue/${orderId}/start`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              printer_id: machine.code,
              notes: `Scheduled via drag-and-drop`,
            }),
          }
        );
        // Don't fail if start fails - scheduling is the main goal
      }

      // Refresh orders
      await fetchProductionOrders();
      if (onScheduleUpdate) onScheduleUpdate();
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    }
  };

  const autoSchedule = async (orderId) => {
    // Check Pro tier first
    if (!isPro) {
      setError(
        "Auto-scheduling is a Pro feature. Upgrade to unlock intelligent scheduling with material compatibility!"
      );
      setTimeout(() => setError(null), 5000);
      return;
    }

    const order = [...productionOrders, ...unscheduledOrders].find(
      (o) => o.id === orderId
    );
    if (!order) return;

    try {
      // Call backend auto-schedule endpoint (Pro feature with material compatibility)
      const response = await fetch(
        `${API_URL}/api/v1/scheduling/auto-schedule?order_id=${orderId}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (response.status === 402) {
        // Pro tier required
        const errorData = await response.json();
        setError(
          errorData.detail?.message || "Auto-scheduling requires Pro tier"
        );
        setTimeout(() => setError(null), 5000);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to auto-schedule order");
      }

      const result = await response.json();

      // Refresh orders to show updated schedule
      await fetchProductionOrders();
      if (onScheduleUpdate) onScheduleUpdate();

      setError(null);
    } catch (err) {
      setError(err.message || "Failed to auto-schedule order");
      setTimeout(() => setError(null), 5000);
    }
  };

  const timeSlots = getTimeSlots();
  const hoursPerSlot = viewMode === "day" ? 1 : viewMode === "week" ? 1 : 24;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
    >
      <div className="space-y-4">
        {/* Header Controls */}
        <div className="flex justify-between items-center">
          <div className="flex gap-4 items-center">
            <h2 className="text-xl font-bold text-white">
              Production Scheduler
            </h2>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1 text-white text-sm"
            >
              <option value="day">Day View</option>
              <option value="week">Week View</option>
              <option value="month">Month View</option>
            </select>
            <input
              type="date"
              value={selectedDate.toISOString().split("T")[0]}
              onChange={(e) => setSelectedDate(new Date(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1 text-white text-sm"
            />
            <button
              onClick={() => {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                setSelectedDate(today);
              }}
              className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm"
            >
              Today
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-4">
          {/* Unscheduled Orders Panel */}
          <div className="w-64 bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3">
              Unscheduled Orders
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {unscheduledOrders.map((order) => (
                <SortableItem
                  key={order.id}
                  id={order.id}
                  order={order}
                  onAutoSchedule={() => autoSchedule(order.id)}
                  isPro={isPro}
                />
              ))}
              {unscheduledOrders.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">
                  All orders scheduled
                </p>
              )}
            </div>
          </div>

          {/* Gantt Chart */}
          <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto" ref={schedulerRef}>
              <table className="w-full border-collapse">
                <thead className="bg-gray-800 sticky top-0 z-10">
                  <tr>
                    <th className="sticky left-0 z-20 bg-gray-800 border-r border-gray-700 px-4 py-2 text-left text-white font-semibold min-w-[200px]">
                      Machine
                    </th>
                    {timeSlots
                      .filter(
                        (_, i) =>
                          i %
                            (viewMode === "day"
                              ? 1
                              : viewMode === "week"
                              ? 1
                              : 24) ===
                          0
                      )
                      .map((slot, i) => (
                        <th
                          key={i}
                          className="border-r border-gray-700 px-2 py-2 text-center text-gray-400 text-xs min-w-[60px]"
                        >
                          {slot.toLocaleTimeString("en-US", {
                            hour: "numeric",
                            hour12: true,
                          })}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  {machines.map((machine, machineIndex) => {
                    const machineOrders = productionOrders.filter((o) => {
                      if (o.assigned_to === machine.code) return true;
                      if (o.print_jobs && Array.isArray(o.print_jobs)) {
                        return o.print_jobs.some(
                          (pj) => pj.printer_id === machine.id
                        );
                      }
                      return false;
                    });

                    return (
                      <tr key={machine.id} className="border-b border-gray-800">
                        <td className="sticky left-0 z-10 bg-gray-900 border-r border-gray-700 px-4 py-3 text-white">
                          <div className="font-medium">{machine.code}</div>
                          <div className="text-xs text-gray-400">
                            {machine.name}
                          </div>
                          <div
                            className={`text-xs mt-1 ${
                              machine.status === "available"
                                ? "text-green-400"
                                : machine.status === "busy"
                                ? "text-yellow-400"
                                : "text-red-400"
                            }`}
                          >
                            {machine.status}
                          </div>
                        </td>
                        {timeSlots
                          .filter(
                            (_, i) =>
                              i %
                                (viewMode === "day"
                                  ? 1
                                  : viewMode === "week"
                                  ? 1
                                  : 24) ===
                              0
                          )
                          .map((slot, slotIndex) => {
                            const slotId = `machine-${machineIndex}-slot-${slot.getHours()}`;
                            const isHovered = hoveredSlot === slotId;
                            const hasOrder = machineOrders.some((o) => {
                              const pos = getOrderPosition(o);
                              if (!pos || pos.machineIndex !== machineIndex)
                                return false;
                              const slotHour = slot.getHours();
                              return (
                                pos.startOffset <= slotHour &&
                                pos.startOffset + pos.duration > slotHour
                              );
                            });

                            return (
                              <td
                                key={slotIndex}
                                id={slotId}
                                className={`border-r border-gray-800 px-1 py-2 min-h-[60px] ${
                                  isHovered ? "bg-blue-900/30" : "bg-gray-900"
                                } ${hasOrder ? "" : "hover:bg-gray-800/50"}`}
                              >
                                {/* Render scheduled orders */}
                                {machineOrders.map((order) => {
                                  const pos = getOrderPosition(order);
                                  if (!pos || pos.machineIndex !== machineIndex)
                                    return null;

                                  const slotHour = slot.getHours();
                                  if (
                                    pos.startOffset <= slotHour &&
                                    pos.startOffset + pos.duration > slotHour
                                  ) {
                                    const isStart =
                                      Math.floor(pos.startOffset) === slotHour;
                                    return (
                                      <div
                                        key={order.id}
                                        className={`bg-purple-600 text-white text-xs p-1 rounded ${
                                          isStart ? "font-semibold" : ""
                                        }`}
                                        style={{
                                          width: `${Math.min(
                                            100,
                                            (pos.duration * 100) /
                                              (viewMode === "day"
                                                ? 1
                                                : viewMode === "week"
                                                ? 1
                                                : 24)
                                          )}%`,
                                        }}
                                      >
                                        {isStart && (
                                          <>
                                            <div className="font-semibold">
                                              {order.code}
                                            </div>
                                            <div className="text-xs opacity-75">
                                              {order.product?.name || "N/A"}
                                            </div>
                                          </>
                                        )}
                                      </div>
                                    );
                                  }
                                  return null;
                                })}
                              </td>
                            );
                          })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <DragOverlay>
          {draggedOrder ? (
            <div className="bg-purple-600 text-white p-3 rounded-lg shadow-lg">
              <div className="font-semibold">{draggedOrder.code}</div>
              <div className="text-sm opacity-75">
                {draggedOrder.product?.name || "N/A"}
              </div>
            </div>
          ) : null}
        </DragOverlay>
      </div>
    </DndContext>
  );
}

// Sortable item component for unscheduled orders
function SortableItem({ id, order, onAutoSchedule, isPro }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-gray-800 border border-gray-700 rounded-lg p-3 cursor-move hover:bg-gray-750"
    >
      <div className="flex justify-between items-start mb-1">
        <div className="font-medium text-white text-sm">{order.code}</div>
        {isPro ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAutoSchedule();
            }}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            title="Auto-schedule (Pro)"
          >
            ⚡
          </button>
        ) : (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAutoSchedule(); // Will show Pro upgrade message
            }}
            className="text-xs text-gray-500 cursor-not-allowed opacity-50"
            title="Auto-schedule (Pro feature - Upgrade required)"
            disabled
          >
            ⚡
          </button>
        )}
      </div>
      <div className="text-xs text-gray-400">
        {order.product?.name || "N/A"}
      </div>
      {order.estimated_time_minutes && (
        <div className="text-xs text-gray-500 mt-1">
          ~{Math.round(order.estimated_time_minutes / 60)}h
        </div>
      )}
    </div>
  );
}
