/**
 * RoutingEditor - Standalone routing editor component
 *
 * Simple, focused editor for managing manufacturing routings.
 * Can be used from item detail pages or standalone.
 */
import { useState, useEffect } from "react";
import { API_URL } from "../config/api";

export default function RoutingEditor({
  isOpen,
  onClose,
  productId = null, // Optional - if not provided, show product selector
  routingId = null, // If editing existing routing
  onSuccess,
  products = [], // Optional - for product selection when productId not provided
}) {
  const token = localStorage.getItem("adminToken");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [routing, setRouting] = useState(null);
  const [operations, setOperations] = useState([]);
  const [workCenters, setWorkCenters] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [showAddOperation, setShowAddOperation] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [selectedProductId, setSelectedProductId] = useState(productId || "");
  const [productList, setProductList] = useState(products || []);

  const [newOperation, setNewOperation] = useState({
    work_center_id: "",
    sequence: 1,
    operation_code: "",
    operation_name: "",
    setup_time_minutes: 0,
    run_time_minutes: 0,
    wait_time_minutes: 0,
    move_time_minutes: 0,
    units_per_cycle: 1,
    scrap_rate_percent: 0,
    is_active: true,
  });

  useEffect(() => {
    if (isOpen) {
      if (routingId) {
        fetchRouting();
      } else if (productId) {
        fetchRoutingByProduct();
      }
      fetchWorkCenters();
      fetchTemplates();
      setError(null);
    }
  }, [isOpen, routingId, productId]);

  const fetchRouting = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/routings/${routingId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRouting(data);
        setOperations(data.operations || []);
      }
    } catch (err) {
      // Routing fetch failure - will show empty editor
    }
  };

  const fetchRoutingByProduct = async () => {
    const finalProductId = selectedProductId || productId;
    if (!finalProductId) return;
    try {
      const res = await fetch(
        `${API_URL}/api/v1/routings/product/${finalProductId}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setRouting(data);
        setOperations(data.operations || []);
      } else if (res.status === 404) {
        // No routing exists yet, that's okay
        setRouting(null);
        setOperations([]);
      }
    } catch (err) {
      // Routing fetch failure - will show empty editor
    }
  };

  const fetchWorkCenters = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/work-centers?active_only=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setWorkCenters(data || []);
      }
    } catch (err) {
      // Work centers fetch failure is non-critical - work center selector will be empty
    }
  };

  const fetchTemplates = async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/routings?templates_only=true&active_only=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setTemplates(data || []);
      }
    } catch (err) {
      // Templates fetch failure is non-critical - templates list will be empty
    }
  };

  const handleApplyTemplate = async () => {
    if (!selectedTemplate) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/routings/from-template`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          template_routing_id: parseInt(selectedTemplate),
          product_id: selectedProductId || productId,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to apply template");
      }

      const data = await res.json();
      setRouting(data);
      setOperations(data.operations || []);
      setSelectedTemplate("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRouting = async () => {
    const finalProductId = selectedProductId || productId;
    if (!finalProductId) {
      setError("Please select a product");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/routings/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          product_id: finalProductId,
          version: 1,
          revision: "1.0",
          is_active: true,
          operations: operations.map((op, idx) => ({
            work_center_id: op.work_center_id,
            sequence: idx + 1,
            operation_code: op.operation_code || `OP${idx + 1}`,
            operation_name: op.operation_name || "",
            setup_time_minutes: op.setup_time_minutes || 0,
            run_time_minutes: op.run_time_minutes || 0,
            wait_time_minutes: op.wait_time_minutes || 0,
            move_time_minutes: op.move_time_minutes || 0,
            units_per_cycle: op.units_per_cycle || 1,
            scrap_rate_percent: op.scrap_rate_percent || 0,
            is_active: op.is_active !== false,
          })),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create routing");
      }

      const data = await res.json();
      onSuccess?.(data);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateRouting = async () => {
    if (!routing) return;

    setLoading(true);
    setError(null);

    try {
      // Update routing operations
      for (let i = 0; i < operations.length; i++) {
        const op = operations[i];
        if (op.id) {
          // Update existing operation
          const res = await fetch(
            `${API_URL}/api/v1/routings/operations/${op.id}`,
            {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                work_center_id: op.work_center_id,
                sequence: i + 1,
                operation_code: op.operation_code || `OP${i + 1}`,
                operation_name: op.operation_name || "",
                setup_time_minutes: op.setup_time_minutes || 0,
                run_time_minutes: op.run_time_minutes || 0,
                wait_time_minutes: op.wait_time_minutes || 0,
                move_time_minutes: op.move_time_minutes || 0,
                units_per_cycle: op.units_per_cycle || 1,
                scrap_rate_percent: op.scrap_rate_percent || 0,
                is_active: op.is_active !== false,
              }),
            }
          );
          if (!res.ok) throw new Error("Failed to update operation");
        } else {
          // Add new operation
          const res = await fetch(
            `${API_URL}/api/v1/routings/${routing.id}/operations`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                work_center_id: op.work_center_id,
                sequence: i + 1,
                operation_code: op.operation_code || `OP${i + 1}`,
                operation_name: op.operation_name || "",
                setup_time_minutes: op.setup_time_minutes || 0,
                run_time_minutes: op.run_time_minutes || 0,
                wait_time_minutes: op.wait_time_minutes || 0,
                move_time_minutes: op.move_time_minutes || 0,
                units_per_cycle: op.units_per_cycle || 1,
                scrap_rate_percent: op.scrap_rate_percent || 0,
                is_active: op.is_active !== false,
              }),
            }
          );
          if (!res.ok) throw new Error("Failed to add operation");
        }
      }

      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    if (routing) {
      handleUpdateRouting();
    } else {
      handleCreateRouting();
    }
  };

  const addOperation = () => {
    const workCenter = workCenters.find(
      (wc) => wc.id === parseInt(newOperation.work_center_id)
    );
    if (!workCenter) {
      setError("Please select a work center");
      return;
    }

    setOperations([
      ...operations,
      {
        ...newOperation,
        work_center_id: parseInt(newOperation.work_center_id),
        work_center_name: workCenter.name,
        work_center_code: workCenter.code,
        labor_rate: workCenter.labor_rate || 0,
        machine_rate: workCenter.machine_rate || 0,
      },
    ]);

    setNewOperation({
      work_center_id: "",
      sequence: operations.length + 2,
      operation_code: "",
      operation_name: "",
      setup_time_minutes: 0,
      run_time_minutes: 0,
      wait_time_minutes: 0,
      move_time_minutes: 0,
      units_per_cycle: 1,
      scrap_rate_percent: 0,
      is_active: true,
    });
    setShowAddOperation(false);
  };

  const removeOperation = (index) => {
    setOperations(operations.filter((_, i) => i !== index));
  };

  const updateOperation = (index, field, value) => {
    const updated = [...operations];
    updated[index] = { ...updated[index], [field]: value };
    setOperations(updated);
  };

  if (!isOpen) return null;

  const totalSetup = operations.reduce(
    (sum, op) => sum + (parseFloat(op.setup_time_minutes) || 0),
    0
  );
  const totalRun = operations.reduce(
    (sum, op) => sum + (parseFloat(op.run_time_minutes) || 0),
    0
  );
  const totalCost = operations.reduce((sum, op) => {
    const setupCost =
      ((parseFloat(op.setup_time_minutes) || 0) / 60) * (parseFloat(op.labor_rate) || 0);
    const runCost = ((parseFloat(op.run_time_minutes) || 0) / 60) * (parseFloat(op.labor_rate) || 0);
    return sum + setupCost + runCost;
  }, 0);

  // If no product selected and no routing, show product selector
  const needsProductSelection =
    !selectedProductId && !productId && !routingId && !routing;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-white">
              {routing
                ? `Edit Routing: ${routing.code || routing.name}`
                : "Create Routing"}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              <svg
                className="w-6 h-6"
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

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded">
              {error}
            </div>
          )}

          {/* Product Selection (if needed) */}
          {needsProductSelection && (
            <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Select Product *
              </label>
              <select
                value={selectedProductId}
                onChange={(e) => {
                  setSelectedProductId(e.target.value);
                  // Auto-fetch routing if exists
                  if (e.target.value) {
                    setTimeout(() => fetchRoutingByProduct(), 100);
                  }
                }}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white"
                required
              >
                <option value="">Select a product...</option>
                {productList.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} - {p.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-2">
                Select a product to create or edit its routing
              </p>
            </div>
          )}

          {/* Show editor only if product is selected or routing exists */}
          {!needsProductSelection && (
            <>
              {/* Template Selection */}
              {!routing && templates.length > 0 && (
                <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <h4 className="font-semibold mb-3 text-blue-400">
                    Apply Template
                  </h4>
                  <div className="flex gap-2">
                    <select
                      value={selectedTemplate}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white"
                    >
                      <option value="">Select a template...</option>
                      {templates.map((tpl) => (
                        <option key={tpl.id} value={tpl.id}>
                          {tpl.code} - {tpl.name} ({tpl.operation_count}{" "}
                          operations)
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleApplyTemplate}
                      disabled={!selectedTemplate || loading}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      Apply Template
                    </button>
                  </div>
                </div>
              )}

              {/* Operations */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold">Operations</h3>
                  <button
                    onClick={() => setShowAddOperation(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    + Add Operation
                  </button>
                </div>

                {operations.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    No operations added yet. Click "Add Operation" to get
                    started.
                  </div>
                ) : (
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-800 border-b border-gray-700">
                        <th className="border border-gray-700 p-2 text-left text-gray-300">
                          Seq
                        </th>
                        <th className="border border-gray-700 p-2 text-left text-gray-300">
                          Operation
                        </th>
                        <th className="border border-gray-700 p-2 text-left text-gray-300">
                          Work Center
                        </th>
                        <th className="border border-gray-700 p-2 text-right text-gray-300">
                          Setup (min)
                        </th>
                        <th className="border border-gray-700 p-2 text-right text-gray-300">
                          Run (min)
                        </th>
                        <th className="border border-gray-700 p-2 text-right text-gray-300">
                          Cost
                        </th>
                        <th className="border border-gray-700 p-2 text-center text-gray-300">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {operations.map((op, index) => (
                        <tr
                          key={index}
                          className="border-b border-gray-800 hover:bg-gray-800/50"
                        >
                          <td className="border border-gray-700 p-2 text-white">
                            {index + 1}
                          </td>
                          <td className="border border-gray-700 p-2">
                            <div>
                              <div className="font-medium text-white">
                                {op.operation_name ||
                                  op.operation_code ||
                                  `OP${index + 1}`}
                              </div>
                              {op.operation_code && (
                                <div className="text-sm text-gray-400">
                                  {op.operation_code}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="border border-gray-700 p-2 text-white">
                            {op.work_center_name || op.work_center?.name}
                          </td>
                          <td className="border border-gray-700 p-2">
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={op.setup_time_minutes || 0}
                              onChange={(e) =>
                                updateOperation(
                                  index,
                                  "setup_time_minutes",
                                  parseFloat(e.target.value) || 0
                                )
                              }
                              className="w-20 text-right bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                            />
                          </td>
                          <td className="border border-gray-700 p-2">
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={op.run_time_minutes || 0}
                              onChange={(e) =>
                                updateOperation(
                                  index,
                                  "run_time_minutes",
                                  parseFloat(e.target.value) || 0
                                )
                              }
                              className="w-20 text-right bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                            />
                          </td>
                          <td className="border border-gray-700 p-2 text-right text-white">
                            $
                            {(
                              (((parseFloat(op.setup_time_minutes) || 0) +
                                (parseFloat(op.run_time_minutes) || 0)) /
                                60) *
                              (parseFloat(op.labor_rate) || 0)
                            ).toFixed(2)}
                          </td>
                          <td className="border border-gray-700 p-2 text-center">
                            <button
                              onClick={() => removeOperation(index)}
                              className="text-red-400 hover:text-red-300"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-gray-800 font-semibold border-t border-gray-700">
                        <td
                          colSpan="3"
                          className="border border-gray-700 p-2 text-right text-gray-300"
                        >
                          Total:
                        </td>
                        <td className="border border-gray-700 p-2 text-right text-white">
                          {totalSetup.toFixed(1)} min
                        </td>
                        <td className="border border-gray-700 p-2 text-right text-white">
                          {totalRun.toFixed(1)} min
                        </td>
                        <td className="border border-gray-700 p-2 text-right text-white">
                          ${totalCost.toFixed(2)}
                        </td>
                        <td className="border border-gray-700"></td>
                      </tr>
                    </tfoot>
                  </table>
                )}
              </div>

              {/* Add Operation Form */}
              {showAddOperation && (
                <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <h4 className="font-semibold mb-3 text-white">
                    Add Operation
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1 text-gray-300">
                        Work Center
                      </label>
                      <select
                        value={newOperation.work_center_id}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            work_center_id: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-white"
                      >
                        <option value="">Select work center...</option>
                        {workCenters.map((wc) => (
                          <option key={wc.id} value={wc.id}>
                            {wc.code} - {wc.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Operation Name
                      </label>
                      <input
                        type="text"
                        value={newOperation.operation_name}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            operation_name: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border rounded-md"
                        placeholder="e.g., 3D Print, Support Removal"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Operation Code
                      </label>
                      <input
                        type="text"
                        value={newOperation.operation_code}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            operation_code: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border rounded-md"
                        placeholder="e.g., OP10, OP20"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Setup Time (minutes)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={newOperation.setup_time_minutes}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            setup_time_minutes: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-full px-3 py-2 border rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Run Time (minutes)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={newOperation.run_time_minutes}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            run_time_minutes: parseFloat(e.target.value) || 0,
                          })
                        }
                        className="w-full px-3 py-2 border rounded-md"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Units per Cycle
                      </label>
                      <input
                        type="number"
                        step="1"
                        min="1"
                        value={newOperation.units_per_cycle}
                        onChange={(e) =>
                          setNewOperation({
                            ...newOperation,
                            units_per_cycle: parseInt(e.target.value) || 1,
                          })
                        }
                        className="w-full px-3 py-2 border rounded-md"
                      />
                    </div>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={addOperation}
                      className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                    >
                      Add
                    </button>
                    <button
                      onClick={() => setShowAddOperation(false)}
                      className="px-4 py-2 bg-gray-300 rounded-md hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border rounded-md hover:bg-gray-50"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  disabled={loading || operations.length === 0}
                >
                  {loading
                    ? "Saving..."
                    : routing
                    ? "Update Routing"
                    : "Create Routing"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
