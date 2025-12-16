import { useState, useEffect } from "react";
import RoutingEditor from "../../components/RoutingEditor";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

// Work center type options
const CENTER_TYPES = [
  { value: "machine", label: "Machine Pool", color: "blue" },
  { value: "station", label: "Work Station", color: "purple" },
  { value: "labor", label: "Labor Pool", color: "green" },
];

// Resource status options
const RESOURCE_STATUSES = [
  { value: "available", label: "Available", color: "green" },
  { value: "busy", label: "Busy", color: "yellow" },
  { value: "maintenance", label: "Maintenance", color: "orange" },
  { value: "offline", label: "Offline", color: "red" },
];

export default function AdminManufacturing() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("work-centers");
  const [workCenters, setWorkCenters] = useState([]);
  const [routings, setRoutings] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [showWorkCenterModal, setShowWorkCenterModal] = useState(false);
  const [showResourceModal, setShowResourceModal] = useState(false);
  const [showRoutingModal, setShowRoutingModal] = useState(false);
  const [showPrinterSetupModal, setShowPrinterSetupModal] = useState(false);
  const [editingWorkCenter, setEditingWorkCenter] = useState(null);
  const [editingResource, setEditingResource] = useState(null);
  const [editingRouting, setEditingRouting] = useState(null);
  const [routingProductId, setRoutingProductId] = useState(null);
  const [selectedWorkCenter, setSelectedWorkCenter] = useState(null);

  const token = localStorage.getItem("adminToken");

  useEffect(() => {
    if (activeTab === "work-centers") {
      fetchWorkCenters();
    } else {
      fetchRoutings();
      fetchProducts();
    }
  }, [activeTab]);

  const fetchWorkCenters = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/work-centers/?active_only=false`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) throw new Error("Failed to fetch work centers");
      const data = await res.json();
      setWorkCenters(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoutings = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/routings/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch routings");
      const data = await res.json();
      setRoutings(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/products?limit=500`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProducts(data.products || data || []);
      }
    } catch (err) {
      // Products fetch failure is non-critical - product selector will just be empty
    }
  };

  const handleSaveWorkCenter = async (data) => {
    try {
      const url = editingWorkCenter
        ? `${API_URL}/api/v1/work-centers/${editingWorkCenter.id}`
        : `${API_URL}/api/v1/work-centers/`;

      const res = await fetch(url, {
        method: editingWorkCenter ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save work center");
      }

      toast.success(editingWorkCenter ? "Work center updated" : "Work center created");
      setShowWorkCenterModal(false);
      setEditingWorkCenter(null);
      fetchWorkCenters();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDeleteWorkCenter = async (wc) => {
    if (!confirm(`Deactivate work center "${wc.name}"?`)) return;

    try {
      const res = await fetch(`${API_URL}/api/v1/work-centers/${wc.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to delete");
      toast.success("Work center deactivated");
      fetchWorkCenters();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDeleteResource = async (resource) => {
    if (!confirm(`Delete resource "${resource.name}"? This cannot be undone.`))
      return;

    try {
      const res = await fetch(
        `${API_URL}/api/v1/work-centers/resources/${resource.id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!res.ok) throw new Error("Failed to delete resource");
      toast.success("Resource deleted");
      fetchWorkCenters(); // Refresh to update resource counts
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleSaveResource = async (data) => {
    try {
      const url = editingResource
        ? `${API_URL}/api/v1/work-centers/resources/${editingResource.id}`
        : `${API_URL}/api/v1/work-centers/${selectedWorkCenter.id}/resources`;

      const res = await fetch(url, {
        method: editingResource ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save resource");
      }

      toast.success(editingResource ? "Resource updated" : "Resource created");
      setShowResourceModal(false);
      setEditingResource(null);
      fetchWorkCenters();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const getTypeColor = (type) => {
    const t = CENTER_TYPES.find((ct) => ct.value === type);
    return t?.color || "gray";
  };

  const getStatusColor = (status) => {
    const s = RESOURCE_STATUSES.find((rs) => rs.value === status);
    return s?.color || "gray";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Manufacturing</h1>
          <p className="text-gray-400 mt-1">
            Work centers, resources, and production routings
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab("work-centers")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === "work-centers"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-gray-400 hover:text-white hover:border-gray-600"
            }`}
          >
            Work Centers
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-700">
              {workCenters.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("routings")}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === "routings"
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-gray-400 hover:text-white hover:border-gray-600"
            }`}
          >
            Routings
            <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-700">
              {routings.length}
            </span>
          </button>
        </nav>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Work Centers Tab */}
      {activeTab === "work-centers" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <button
              onClick={() => setShowPrinterSetupModal(true)}
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
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
                  d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                />
              </svg>
              Printer Setup
            </button>
            <button
              onClick={() => {
                setEditingWorkCenter(null);
                setShowWorkCenterModal(true);
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <span>+</span> Add Work Center
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-400">Loading...</div>
          ) : (
            <div className="grid gap-4">
              {workCenters.map((wc) => (
                <WorkCenterCard
                  key={wc.id}
                  workCenter={wc}
                  onEdit={() => {
                    setEditingWorkCenter(wc);
                    setShowWorkCenterModal(true);
                  }}
                  onDelete={() => handleDeleteWorkCenter(wc)}
                  onAddResource={() => {
                    setSelectedWorkCenter(wc);
                    setEditingResource(null);
                    setShowResourceModal(true);
                  }}
                  onEditResource={(r) => {
                    setSelectedWorkCenter(wc);
                    setEditingResource(r);
                    setShowResourceModal(true);
                  }}
                  onDeleteResource={handleDeleteResource}
                  getTypeColor={getTypeColor}
                  getStatusColor={getStatusColor}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Routings Tab */}
      {activeTab === "routings" && (
        <div className="space-y-4">
          <div className="flex justify-end items-center">
            <button
              onClick={() => {
                setEditingRouting(null);
                setRoutingProductId(null);
                setShowRoutingModal(true);
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              <span>+</span> Create Routing
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-400">Loading...</div>
          ) : routings.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-2">No routings defined yet</div>
              <p className="text-sm text-gray-500">
                Routings define HOW to make a product - the sequence of
                operations at each work center.
              </p>
            </div>
          ) : (
            <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800 text-left text-sm text-gray-400">
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Product</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Operations</th>
                    <th className="px-4 py-3">Total Time</th>
                    <th className="px-4 py-3">Cost</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {routings.map((routing) => (
                    <tr
                      key={routing.id}
                      className={`border-b border-gray-800 hover:bg-gray-800/50 ${
                        routing.is_template ? "bg-green-900/10" : ""
                      }`}
                    >
                      <td className="px-4 py-3 font-mono text-blue-400">
                        {routing.code}
                        {routing.is_template && (
                          <span className="ml-2 px-2 py-0.5 rounded text-xs bg-green-900/30 text-green-400">
                            Template
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-white">
                        {routing.is_template ? (
                          <span className="text-green-300">{routing.name}</span>
                        ) : (
                          routing.product_name ||
                          routing.product_sku ||
                          `Product #${routing.product_id}`
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        v{routing.version} ({routing.revision})
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {routing.operation_count || 0} steps
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {routing.total_run_time_minutes
                          ? `${parseFloat(
                              routing.total_run_time_minutes
                            ).toFixed(0)} min`
                          : "-"}
                      </td>
                      <td className="px-4 py-3 text-green-400">
                        {routing.total_cost
                          ? `$${parseFloat(routing.total_cost).toFixed(2)}`
                          : "-"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            routing.is_active
                              ? "bg-green-900/30 text-green-400"
                              : "bg-gray-700 text-gray-400"
                          }`}
                        >
                          {routing.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => {
                            setEditingRouting(routing);
                            setRoutingProductId(routing.product_id);
                            setShowRoutingModal(true);
                          }}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Work Center Modal */}
      {showWorkCenterModal && (
        <WorkCenterModal
          workCenter={editingWorkCenter}
          onClose={() => {
            setShowWorkCenterModal(false);
            setEditingWorkCenter(null);
          }}
          onSave={handleSaveWorkCenter}
        />
      )}

      {/* Resource Modal */}
      {showResourceModal && (
        <ResourceModal
          resource={editingResource}
          workCenter={selectedWorkCenter}
          token={token}
          onClose={() => {
            setShowResourceModal(false);
            setEditingResource(null);
          }}
          onSave={handleSaveResource}
        />
      )}

      {/* Printer Setup Modal */}
      {showPrinterSetupModal && (
        <PrinterSetupModal
          workCenters={workCenters}
          onClose={() => setShowPrinterSetupModal(false)}
          onAddPrinter={(wc) => {
            setShowPrinterSetupModal(false);
            setSelectedWorkCenter(wc);
            setEditingResource(null);
            setShowResourceModal(true);
          }}
        />
      )}

      {/* Routing Editor Modal */}
      {showRoutingModal && (
        <RoutingEditor
          isOpen={showRoutingModal}
          onClose={() => {
            setShowRoutingModal(false);
            setEditingRouting(null);
            setRoutingProductId(null);
          }}
          productId={routingProductId || editingRouting?.product_id || null}
          routingId={editingRouting?.id || null}
          products={products}
          onSuccess={() => {
            setShowRoutingModal(false);
            setEditingRouting(null);
            setRoutingProductId(null);
            fetchRoutings();
          }}
        />
      )}
    </div>
  );
}

// Work Center Card Component
function WorkCenterCard({
  workCenter,
  onEdit,
  onDelete,
  onAddResource,
  onEditResource,
  onDeleteResource,
  getTypeColor,
  getStatusColor,
}) {
  const [expanded, setExpanded] = useState(false);
  const [resources, setResources] = useState([]);
  const [printers, setPrinters] = useState([]);
  const [loadingResources, setLoadingResources] = useState(false);

  const token = localStorage.getItem("adminToken");

  const fetchResources = async () => {
    if (resources.length > 0) return;
    setLoadingResources(true);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/work-centers/${workCenter.id}/resources?active_only=false`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setResources(data);
      }
    } catch (err) {
      // Resources fetch failure is non-critical - resource list will just be empty
    } finally {
      setLoadingResources(false);
    }
  };

  const fetchPrinters = async () => {
    if (printers.length > 0) return;
    try {
      const res = await fetch(
        `${API_URL}/api/v1/work-centers/${workCenter.id}/printers?active_only=false`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setPrinters(data);
      }
    } catch (err) {
      // Printers fetch failure is non-critical
    }
  };

  useEffect(() => {
    if (expanded) {
      fetchResources();
      if (workCenter.center_type === "machine") {
        fetchPrinters();
      }
    }
  }, [expanded]);

  const [addingAll, setAddingAll] = useState(false);

  const handleAddAllPrinters = async (printersToAdd) => {
    setAddingAll(true);
    let successCount = 0;

    for (const printer of printersToAdd) {
      try {
        const resourceData = {
          code: printer.code || "",
          name: printer.name || "",
          machine_type: printer.model || "",
          serial_number: printer.serial_number || "",
          bambu_device_id: printer.device_id || "",
          bambu_ip_address: printer.ip_address || "",
          status: printer.status === "idle" ? "available" : "available",
          is_active: printer.is_active ?? true,
          printer_id: printer.id,
        };

        const res = await fetch(
          `${API_URL}/api/v1/work-centers/${workCenter.id}/resources`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(resourceData),
          }
        );

        if (res.ok) {
          successCount++;
        }
      } catch (err) {
        // Continue with next printer
      }
    }

    // Refresh resources list
    setResources([]);
    await fetchResources();
    setAddingAll(false);
  };

  const typeColor = getTypeColor(workCenter.center_type);

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-white"
          >
            {expanded ? "▼" : "▶"}
          </button>

          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-blue-400 font-medium">
                {workCenter.code}
              </span>
              <span className="text-white font-medium">{workCenter.name}</span>
              <span
                className={`px-2 py-0.5 rounded text-xs bg-${typeColor}-900/30 text-${typeColor}-400`}
              >
                {workCenter.center_type}
              </span>
              {!workCenter.is_active && (
                <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-400">
                  Inactive
                </span>
              )}
              {workCenter.is_bottleneck && (
                <span className="px-2 py-0.5 rounded text-xs bg-red-900/30 text-red-400">
                  Bottleneck
                </span>
              )}
            </div>
            <div className="text-sm text-gray-400 mt-1 flex gap-4">
              <span>
                Capacity: {workCenter.capacity_hours_per_day || "-"} hrs/day
              </span>
              <span>
                Rate: $
                {parseFloat(workCenter.total_rate_per_hour || 0).toFixed(2)}/hr
              </span>
              <span>Resources: {workCenter.resource_count || 0}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onEdit}
            className="text-blue-400 hover:text-blue-300 text-sm px-3 py-1"
          >
            Edit
          </button>
          <button
            onClick={onDelete}
            className="text-red-400 hover:text-red-300 text-sm px-3 py-1"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Expanded: Resources */}
      {expanded && (
        <div className="border-t border-gray-800 p-4 bg-gray-950">
          <div className="flex justify-between items-center mb-3">
            <h4 className="text-sm font-medium text-gray-400">
              Resources / Machines
            </h4>
            <button
              onClick={onAddResource}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              + Add Resource
            </button>
          </div>

          {loadingResources ? (
            <div className="text-gray-500 text-sm">Loading...</div>
          ) : resources.length === 0 ? (
            <div className="text-gray-500 text-sm">
              No resources defined. Add individual machines or stations.
            </div>
          ) : (
            <div className="grid gap-2">
              {resources.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between p-3 bg-gray-900 rounded border border-gray-800"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-2 h-2 rounded-full bg-${getStatusColor(
                        r.status
                      )}-500`}
                    />
                    <span className="font-mono text-sm text-gray-300">
                      {r.code}
                    </span>
                    <span className="text-white">{r.name}</span>
                    {r.machine_type && (
                      <span className="text-xs text-gray-500">
                        ({r.machine_type})
                      </span>
                    )}
                    {r.bambu_device_id && (
                      <span className="text-xs text-purple-400">
                        Bambu Connected
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs bg-${getStatusColor(
                        r.status
                      )}-900/30 text-${getStatusColor(r.status)}-400`}
                    >
                      {r.status}
                    </span>
                    <button
                      onClick={() => onEditResource(r)}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => onDeleteResource(r)}
                      className="text-red-400 hover:text-red-300 text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Printers Section - only for machine type work centers */}
          {workCenter.center_type === "machine" && (() => {
            // Filter out printers that are already added as resources (by code)
            const resourceCodes = resources.map((r) => r.code);
            const unaddedPrinters = printers.filter((p) => !resourceCodes.includes(p.code));

            return (
              <div className="mt-4 pt-4 border-t border-gray-800">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-sm font-medium text-gray-400">
                    🖨️ Available Printers
                    {unaddedPrinters.length > 0 && (
                      <span className="ml-2 text-xs text-yellow-500">
                        ({unaddedPrinters.length} not added)
                      </span>
                    )}
                  </h4>
                  <div className="flex items-center gap-3">
                    {unaddedPrinters.length > 0 && (
                      <button
                        onClick={() => handleAddAllPrinters(unaddedPrinters)}
                        disabled={addingAll}
                        className="text-sm px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-green-800 disabled:cursor-wait text-white rounded"
                      >
                        {addingAll ? "Adding..." : `Add All (${unaddedPrinters.length})`}
                      </button>
                    )}
                    <a
                      href="/admin/printers"
                      className="text-sm text-blue-400 hover:text-blue-300"
                    >
                      Manage Printers →
                    </a>
                  </div>
                </div>

                {printers.length === 0 ? (
                  <div className="text-gray-500 text-sm">
                    No printers assigned to this pool. Assign printers from the Printers page.
                  </div>
                ) : unaddedPrinters.length === 0 ? (
                  <div className="text-green-500 text-sm">
                    ✓ All assigned printers have been added as resources.
                  </div>
                ) : (
                  <div className="grid gap-2">
                    {unaddedPrinters.map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between p-3 bg-gray-900 rounded border border-gray-800"
                      >
                        <div className="flex items-center gap-3">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              p.status === "idle" ? "bg-green-500" :
                              p.status === "printing" ? "bg-blue-500" :
                              p.status === "error" ? "bg-red-500" :
                              "bg-gray-500"
                            }`}
                          />
                          <span className="font-mono text-sm text-gray-300">
                            {p.code}
                          </span>
                          <span className="text-white">{p.name}</span>
                          <span className="text-xs text-gray-500">
                            ({p.model})
                          </span>
                          {p.ip_address && (
                            <span className="text-xs text-purple-400">
                              {p.ip_address}
                            </span>
                          )}
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-xs ${
                            p.status === "idle" ? "bg-green-900/30 text-green-400" :
                            p.status === "printing" ? "bg-blue-900/30 text-blue-400" :
                            p.status === "error" ? "bg-red-900/30 text-red-400" :
                            "bg-gray-700 text-gray-400"
                          }`}
                        >
                          {p.status || "offline"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

// Work Center Modal
function WorkCenterModal({ workCenter, onClose, onSave }) {
  const [form, setForm] = useState({
    code: workCenter?.code || "",
    name: workCenter?.name || "",
    description: workCenter?.description || "",
    center_type: workCenter?.center_type || "station",
    capacity_hours_per_day: workCenter?.capacity_hours_per_day || "",
    capacity_units_per_hour: workCenter?.capacity_units_per_hour || "",
    machine_rate_per_hour: workCenter?.machine_rate_per_hour || "",
    labor_rate_per_hour: workCenter?.labor_rate_per_hour || "",
    overhead_rate_per_hour: workCenter?.overhead_rate_per_hour || "",
    is_bottleneck: workCenter?.is_bottleneck || false,
    scheduling_priority: workCenter?.scheduling_priority || 50,
    is_active: workCenter?.is_active ?? true,
  });

  // Overhead calculator state
  const [showCalculator, setShowCalculator] = useState(false);
  const [calc, setCalc] = useState({
    printerCost: 1200,
    lifespanYears: 3,
    hoursPerDay: 20,
    daysPerYear: 350,
    electricityRate: 0.12,
    wattage: 150,
    annualMaintenance: 150,
  });

  // Calculate overhead rate from inputs
  const calculatedOverhead = (() => {
    const annualHours = calc.hoursPerDay * calc.daysPerYear;
    if (annualHours === 0) return 0;
    const depreciation = calc.printerCost / calc.lifespanYears / annualHours;
    const electricity = calc.electricityRate * (calc.wattage / 1000);
    const maintenance = calc.annualMaintenance / annualHours;
    return depreciation + electricity + maintenance;
  })();

  const applyCalculatedRate = () => {
    setForm({ ...form, overhead_rate_per_hour: calculatedOverhead.toFixed(3) });
    setShowCalculator(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Convert empty strings to null for numeric fields
    const data = {
      ...form,
      capacity_hours_per_day: form.capacity_hours_per_day || null,
      capacity_units_per_hour: form.capacity_units_per_hour || null,
      machine_rate_per_hour: form.machine_rate_per_hour || null,
      labor_rate_per_hour: form.labor_rate_per_hour || null,
      overhead_rate_per_hour: form.overhead_rate_per_hour || null,
    };

    onSave(data);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg border border-gray-700 w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white">
            {workCenter ? "Edit Work Center" : "New Work Center"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Code *</label>
              <input
                type="text"
                value={form.code}
                onChange={(e) =>
                  setForm({ ...form, code: e.target.value.toUpperCase() })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                placeholder="FDM-POOL"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Type</label>
              <select
                value={form.center_type}
                onChange={(e) =>
                  setForm({ ...form, center_type: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                {CENTER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              placeholder="FDM Printer Pool"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              rows={2}
            />
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Capacity</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Hours/Day
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={form.capacity_hours_per_day}
                  onChange={(e) =>
                    setForm({ ...form, capacity_hours_per_day: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="8"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Units/Hour
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={form.capacity_units_per_hour}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      capacity_units_per_hour: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="10"
                />
              </div>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Hourly Rates ($)
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Machine
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={form.machine_rate_per_hour}
                  onChange={(e) =>
                    setForm({ ...form, machine_rate_per_hour: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="2.00"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Labor
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={form.labor_rate_per_hour}
                  onChange={(e) =>
                    setForm({ ...form, labor_rate_per_hour: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="25.00"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Overhead
                  <button
                    type="button"
                    onClick={() => setShowCalculator(!showCalculator)}
                    className="ml-2 text-xs text-blue-400 hover:text-blue-300"
                  >
                    {showCalculator ? "Hide Calculator" : "Calculate"}
                  </button>
                </label>
                <input
                  type="number"
                  step="0.001"
                  value={form.overhead_rate_per_hour}
                  onChange={(e) =>
                    setForm({ ...form, overhead_rate_per_hour: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="0.09"
                />
              </div>
            </div>

            {/* Overhead Calculator */}
            {showCalculator && (
              <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-blue-500/30">
                <h4 className="text-sm font-medium text-blue-400 mb-3">
                  Overhead Rate Calculator
                </h4>
                <p className="text-xs text-gray-500 mb-3">
                  Calculate machine overhead from depreciation + electricity +
                  maintenance
                </p>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Printer Cost ($)
                    </label>
                    <input
                      type="number"
                      value={calc.printerCost}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          printerCost: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Lifespan (years)
                    </label>
                    <input
                      type="number"
                      value={calc.lifespanYears}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          lifespanYears: parseFloat(e.target.value) || 1,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Hours/Day
                    </label>
                    <input
                      type="number"
                      value={calc.hoursPerDay}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          hoursPerDay: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Days/Year
                    </label>
                    <input
                      type="number"
                      value={calc.daysPerYear}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          daysPerYear: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Electricity ($/kWh)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={calc.electricityRate}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          electricityRate: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Wattage (W)
                    </label>
                    <input
                      type="number"
                      value={calc.wattage}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          wattage: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-gray-400 mb-1">
                      Annual Maintenance ($)
                    </label>
                    <input
                      type="number"
                      value={calc.annualMaintenance}
                      onChange={(e) =>
                        setCalc({
                          ...calc,
                          annualMaintenance: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                    />
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <div className="text-sm">
                    <span className="text-gray-400">Calculated rate: </span>
                    <span className="text-green-400 font-mono font-bold">
                      ${calculatedOverhead.toFixed(3)}/hr
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={applyCalculatedRate}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
                  >
                    Apply Rate
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Scheduling
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Priority (0-100)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={form.scheduling_priority}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      scheduling_priority: parseInt(e.target.value),
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <div className="flex items-center gap-4 pt-6">
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.is_bottleneck}
                    onChange={(e) =>
                      setForm({ ...form, is_bottleneck: e.target.checked })
                    }
                    className="rounded bg-gray-800 border-gray-700"
                  />
                  Bottleneck
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) =>
                      setForm({ ...form, is_active: e.target.checked })
                    }
                    className="rounded bg-gray-800 border-gray-700"
                  />
                  Active
                </label>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              {workCenter ? "Save Changes" : "Create Work Center"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Resource Modal
function ResourceModal({ resource, workCenter, onClose, onSave, token }) {
  const [form, setForm] = useState({
    code: resource?.code || "",
    name: resource?.name || "",
    machine_type: resource?.machine_type || "",
    serial_number: resource?.serial_number || "",
    bambu_device_id: resource?.bambu_device_id || "",
    bambu_ip_address: resource?.bambu_ip_address || "",
    capacity_hours_per_day: resource?.capacity_hours_per_day || "",
    status: resource?.status || "available",
    is_active: resource?.is_active ?? true,
    printer_id: resource?.printer_id || null,
  });
  const [printers, setPrinters] = useState([]);
  const [existingResources, setExistingResources] = useState([]);
  const [loadingPrinters, setLoadingPrinters] = useState(false);

  // Fetch printers and existing resources for this work center
  useEffect(() => {
    if (!resource && workCenter?.center_type === "machine") {
      setLoadingPrinters(true);

      // Fetch both printers and existing resources
      Promise.all([
        fetch(`${API_URL}/api/v1/work-centers/${workCenter.id}/printers?active_only=true`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.ok ? res.json() : []),
        fetch(`${API_URL}/api/v1/work-centers/${workCenter.id}/resources?active_only=false`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((res) => res.ok ? res.json() : []),
      ])
        .then(([printersData, resourcesData]) => {
          setPrinters(printersData);
          setExistingResources(resourcesData);
        })
        .catch(() => {
          setPrinters([]);
          setExistingResources([]);
        })
        .finally(() => setLoadingPrinters(false));
    }
  }, [workCenter, resource, token]);

  // Filter out printers that are already added as resources
  const availablePrinters = printers.filter(
    (p) => !existingResources.some((r) => r.code === p.code)
  );

  const handlePrinterSelect = (printerId) => {
    if (!printerId) {
      // Clear form if "Manual Entry" selected
      setForm({
        code: "",
        name: "",
        machine_type: "",
        serial_number: "",
        bambu_device_id: "",
        bambu_ip_address: "",
        capacity_hours_per_day: "",
        status: "available",
        is_active: true,
        printer_id: null,
      });
      return;
    }
    const printer = printers.find((p) => p.id === parseInt(printerId));
    if (printer) {
      setForm({
        code: printer.code || "",
        name: printer.name || "",
        machine_type: printer.model || "",
        serial_number: printer.serial_number || "",
        bambu_device_id: printer.device_id || "",
        bambu_ip_address: printer.ip_address || "",
        capacity_hours_per_day: "",
        status: printer.status === "idle" ? "available" : printer.status === "printing" ? "busy" : "available",
        is_active: printer.is_active ?? true,
        printer_id: printer.id,
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      ...form,
      capacity_hours_per_day: form.capacity_hours_per_day || null,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg border border-gray-700 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white">
            {resource ? "Edit Resource" : "New Resource"}
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Adding to: {workCenter?.name}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Printer Selection Dropdown - only show for new resources on machine-type work centers */}
          {!resource && workCenter?.center_type === "machine" && availablePrinters.length > 0 && (
            <div className="pb-4 border-b border-gray-800">
              <label className="block text-sm text-gray-400 mb-1">
                Quick Add from Assigned Printer
              </label>
              <select
                onChange={(e) => handlePrinterSelect(e.target.value)}
                className="w-full bg-gray-800 border border-green-600 rounded px-3 py-2 text-white"
                defaultValue=""
              >
                <option value="">-- Select a printer or enter manually --</option>
                {availablePrinters.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} - {p.name} ({p.model || "Unknown model"})
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Select a printer to auto-fill the form, or leave blank for manual entry
              </p>
            </div>
          )}

          {!resource && workCenter?.center_type === "machine" && printers.length > 0 && availablePrinters.length === 0 && !loadingPrinters && (
            <div className="p-3 bg-green-900/30 border border-green-700 rounded text-green-400 text-sm">
              ✓ All assigned printers have been added as resources. Enter details manually below if needed.
            </div>
          )}

          {!resource && workCenter?.center_type === "machine" && printers.length === 0 && !loadingPrinters && (
            <div className="p-3 bg-yellow-900/30 border border-yellow-700 rounded text-yellow-400 text-sm">
              No printers assigned to this work center. Assign printers from the Printers page first, or enter details manually below.
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Code *</label>
              <input
                type="text"
                value={form.code}
                onChange={(e) =>
                  setForm({ ...form, code: e.target.value.toUpperCase() })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                placeholder="PRINTER-01"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              >
                {RESOURCE_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              placeholder="Donatello"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Machine Type
              </label>
              <input
                type="text"
                value={form.machine_type}
                onChange={(e) =>
                  setForm({ ...form, machine_type: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                placeholder="X1C, P1S, A1..."
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Serial Number
              </label>
              <input
                type="text"
                value={form.serial_number}
                onChange={(e) =>
                  setForm({ ...form, serial_number: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              />
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <h3 className="text-sm font-medium text-purple-400 mb-3">
              Bambu Integration
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Device ID
                </label>
                <input
                  type="text"
                  value={form.bambu_device_id}
                  onChange={(e) =>
                    setForm({ ...form, bambu_device_id: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="From Bambu Studio"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  IP Address
                </label>
                <input
                  type="text"
                  value={form.bambu_ip_address}
                  onChange={(e) =>
                    setForm({ ...form, bambu_ip_address: e.target.value })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  placeholder="192.168.1.100"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm text-gray-400 mb-1">
                Capacity Hours/Day
              </label>
              <input
                type="number"
                step="0.5"
                value={form.capacity_hours_per_day}
                onChange={(e) =>
                  setForm({ ...form, capacity_hours_per_day: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                placeholder="Inherit from work center"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-300 pt-6">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="rounded bg-gray-800 border-gray-700"
              />
              Active
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
            >
              {resource ? "Save Changes" : "Add Resource"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Simple Routing Modal (for now)
function RoutingModal({ products, workCenters, onClose, token, onSuccess }) {
  const toast = useToast();
  const [form, setForm] = useState({
    product_id: "",
    code: "",
    name: "",
    operations: [],
  });
  const [saving, setSaving] = useState(false);

  const addOperation = () => {
    setForm({
      ...form,
      operations: [
        ...form.operations,
        {
          work_center_id: workCenters[0]?.id || "",
          sequence: form.operations.length + 1,
          operation_name: "",
          run_time_minutes: 0,
          setup_time_minutes: 0,
        },
      ],
    });
  };

  const updateOperation = (index, field, value) => {
    const ops = [...form.operations];
    ops[index] = { ...ops[index], [field]: value };
    setForm({ ...form, operations: ops });
  };

  const removeOperation = (index) => {
    const ops = form.operations.filter((_, i) => i !== index);
    // Resequence
    ops.forEach((op, i) => (op.sequence = i + 1));
    setForm({ ...form, operations: ops });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.product_id) {
      toast.warning("Please select a product");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/routings/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          product_id: parseInt(form.product_id),
          code: form.code || `RTG-${Date.now()}`,
          name: form.name,
          operations: form.operations.map((op) => ({
            ...op,
            work_center_id: parseInt(op.work_center_id),
            run_time_minutes: parseFloat(op.run_time_minutes) || 0,
            setup_time_minutes: parseFloat(op.setup_time_minutes) || 0,
          })),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create routing");
      }

      toast.success("Routing created");
      onSuccess();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white">Create Routing</h2>
          <p className="text-sm text-gray-400 mt-1">
            Define the sequence of operations to make a product
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Product *
              </label>
              <select
                value={form.product_id}
                onChange={(e) =>
                  setForm({ ...form, product_id: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                required
              >
                <option value="">Select product...</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} - {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Routing Code
              </label>
              <input
                type="text"
                value={form.code}
                onChange={(e) =>
                  setForm({ ...form, code: e.target.value.toUpperCase() })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                placeholder="Auto-generated if empty"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              placeholder="Standard Production Process"
            />
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-medium text-gray-300">Operations</h3>
              <button
                type="button"
                onClick={addOperation}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                + Add Operation
              </button>
            </div>

            {form.operations.length === 0 ? (
              <div className="text-gray-500 text-sm py-4 text-center border border-dashed border-gray-700 rounded">
                No operations yet. Click "Add Operation" to define the process.
              </div>
            ) : (
              <div className="space-y-3">
                {form.operations.map((op, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-3 bg-gray-800 rounded border border-gray-700"
                  >
                    <span className="text-gray-500 font-mono text-sm w-6">
                      {op.sequence}
                    </span>
                    <select
                      value={op.work_center_id}
                      onChange={(e) =>
                        updateOperation(idx, "work_center_id", e.target.value)
                      }
                      className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white"
                    >
                      {workCenters.map((wc) => (
                        <option key={wc.id} value={wc.id}>
                          {wc.code} - {wc.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={op.operation_name}
                      onChange={(e) =>
                        updateOperation(idx, "operation_name", e.target.value)
                      }
                      className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white"
                      placeholder="Operation name"
                    />
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        value={op.run_time_minutes}
                        onChange={(e) =>
                          updateOperation(
                            idx,
                            "run_time_minutes",
                            e.target.value
                          )
                        }
                        className="w-20 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white"
                        placeholder="0"
                      />
                      <span className="text-gray-500 text-xs">min</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeOperation(idx)}
                      className="text-red-400 hover:text-red-300 px-2"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Routing"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Printer Setup Modal - for adding printers/machines to work centers
function PrinterSetupModal({ workCenters, onClose, onAddPrinter }) {
  const [selectedWorkCenter, setSelectedWorkCenter] = useState("");

  // Filter to only show Machine Pool type work centers
  const machineWorkCenters = workCenters.filter((wc) => wc.center_type === "machine");

  const handleAddPrinter = () => {
    const wc = workCenters.find((w) => w.id === parseInt(selectedWorkCenter));
    if (wc) {
      onAddPrinter(wc);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg border border-gray-700 w-full max-w-lg">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <svg
              className="w-6 h-6 text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
              />
            </svg>
            Printer Setup
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Add printers and machines to your work centers for scheduling
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Enterprise upsell banner */}
          <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border border-purple-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <svg
                  className="w-5 h-5 text-purple-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-medium text-purple-300">
                  Automatic Printer Sync
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  FilaOps Enterprise integrates directly with Bambu Cloud to
                  auto-sync your printers, monitor status, and track jobs in
                  real-time.
                </p>
                <a
                  href="https://filaops.com/enterprise"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-purple-400 hover:text-purple-300 mt-2 inline-block"
                >
                  Learn more →
                </a>
              </div>
            </div>
          </div>

          {/* Manual setup section */}
          <div>
            <h3 className="text-sm font-medium text-white mb-3">
              Manual Setup
            </h3>
            <p className="text-sm text-gray-400 mb-4">
              Select a work center to add a printer or machine:
            </p>

            {machineWorkCenters.length === 0 ? (
              <div className="text-center py-6 bg-gray-800/50 rounded-lg border border-gray-700">
                <p className="text-gray-400 text-sm">
                  No Machine Pool work centers found.
                </p>
                <p className="text-gray-500 text-xs mt-1">
                  Create a work center with type "Machine Pool" first.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <select
                  value={selectedWorkCenter}
                  onChange={(e) => setSelectedWorkCenter(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="">Select a work center...</option>
                  {machineWorkCenters.map((wc) => (
                    <option key={wc.id} value={wc.id}>
                      {wc.code} - {wc.name}
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleAddPrinter}
                  disabled={!selectedWorkCenter}
                  className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
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
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  Add Printer to Work Center
                </button>
              </div>
            )}
          </div>

          {/* Quick tip */}
          <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <p className="text-xs text-gray-400">
              <span className="text-blue-400 font-medium">Tip:</span> You can
              also add printers by clicking on a work center card and selecting
              "Add Resource".
            </p>
          </div>
        </div>

        <div className="p-6 border-t border-gray-800">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 text-gray-400 hover:text-white border border-gray-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
