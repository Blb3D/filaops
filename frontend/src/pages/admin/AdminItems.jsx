import { useState, useEffect } from "react";
import ItemForm from "../../components/ItemForm";
import MaterialForm from "../../components/MaterialForm";
import BOMEditor from "../../components/BOMEditor";
import RoutingEditor from "../../components/RoutingEditor";
import StatCard from "../../components/StatCard";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

// Item type options
const ITEM_TYPES = [
  { value: "finished_good", label: "Finished Good", color: "blue" },
  { value: "component", label: "Component", color: "purple" },
  { value: "filament", label: "Filament", color: "orange" },
  { value: "supply", label: "Supply", color: "yellow" },
  { value: "service", label: "Service", color: "green" },
];

export default function AdminItems() {
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [categoryTree, setCategoryTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState(new Set());
  const [filters, setFilters] = useState({
    search: "",
    itemType: "all",
    activeOnly: true,
  });

  // Pagination state
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 50,
    total: 0,
  });

  // Modal states
  const [showItemModal, setShowItemModal] = useState(false);
  const [showMaterialModal, setShowMaterialModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showBOMEditor, setShowBOMEditor] = useState(false);
  const [showRoutingEditor, setShowRoutingEditor] = useState(false);
  const [selectedItemForBOM, setSelectedItemForBOM] = useState(null);
  const [selectedItemForRouting, setSelectedItemForRouting] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);

  // Recost states
  const [recosting, setRecosting] = useState(false);
  const [recostResult, setRecostResult] = useState(null);

  // Bulk selection states
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [showBulkUpdateModal, setShowBulkUpdateModal] = useState(false);

  const token = localStorage.getItem("adminToken");

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchItems();
  }, [selectedCategory, filters.itemType, filters.activeOnly, pagination.page, pagination.pageSize]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, page: 1 }));
  }, [selectedCategory, filters.itemType, filters.activeOnly]);

  const fetchCategories = async () => {
    if (!token) return;
    try {
      // Fetch flat list
      const res = await fetch(
        `${API_URL}/api/v1/items/categories?include_inactive=true`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) throw new Error("Failed to fetch categories");
      const data = await res.json();
      setCategories(data);

      // Fetch tree structure
      const treeRes = await fetch(`${API_URL}/api/v1/items/categories/tree`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (treeRes.ok) {
        const treeData = await treeRes.json();
        setCategoryTree(treeData);
      }
    } catch (err) {
      // Category fetch failure is non-critical - category tree will just be empty
    }
  };

  const fetchItems = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", pagination.pageSize.toString());
      params.set("offset", ((pagination.page - 1) * pagination.pageSize).toString());
      params.set("active_only", filters.activeOnly.toString());
      if (selectedCategory)
        params.set("category_id", selectedCategory.toString());
      if (filters.itemType !== "all") params.set("item_type", filters.itemType);
      if (filters.search) params.set("search", filters.search);

      const res = await fetch(`${API_URL}/api/v1/items?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch items");
      const data = await res.json();
      setItems(data.items || []);
      setPagination((prev) => ({ ...prev, total: data.total || 0 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Server-side search is now used, so filteredItems is just items
  const filteredItems = items;

  // Debounced search - trigger fetch when search changes
  useEffect(() => {
    const timer = setTimeout(() => {
      if (pagination.page === 1) {
        fetchItems();
      } else {
        setPagination((prev) => ({ ...prev, page: 1 }));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  // Pagination helpers
  const totalPages = Math.ceil(pagination.total / pagination.pageSize);
  const canGoPrev = pagination.page > 1;
  const canGoNext = pagination.page < totalPages;

  // Toggle category expand/collapse
  const toggleExpand = (categoryId) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) {
        next.delete(categoryId);
      } else {
        next.add(categoryId);
      }
      return next;
    });
  };

  // Delete category handler
  const handleDeleteCategory = async (category) => {
    if (!confirm(`Delete category "${category.name}"? Items in this category will become uncategorized.`)) {
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/v1/items/categories/${category.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete category");
      }
      toast.success("Category deleted");
      fetchCategories();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Category tree component
  const CategoryNode = ({ node, depth = 0 }) => {
    const hasChildren = node.children?.length > 0;
    const isExpanded = expandedCategories.has(node.id);
    const isSelected = selectedCategory === node.id;

    return (
      <div>
        <div
          className={`group flex items-center rounded-lg text-sm transition-colors ${
            isSelected
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-gray-400 hover:bg-gray-800 hover:text-white"
          }`}
          style={{ paddingLeft: `${8 + depth * 12}px` }}
        >
          {/* Expand/Collapse toggle */}
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.id);
              }}
              className="p-1 hover:text-white"
            >
              <span className="text-xs">{isExpanded ? "▼" : "▶"}</span>
            </button>
          ) : (
            <span className="w-5" /> // Spacer for alignment
          )}

          {/* Category name - click to filter */}
          <button
            onClick={() => setSelectedCategory(isSelected ? null : node.id)}
            className="flex-1 text-left py-2 pr-2"
          >
            {node.name}
          </button>

          {/* Edit/Delete buttons - show on hover */}
          <div className="hidden group-hover:flex items-center gap-1 pr-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditingCategory(node);
                setShowCategoryModal(true);
              }}
              className="p-1 text-gray-500 hover:text-blue-400"
              title="Edit category"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteCategory(node);
              }}
              className="p-1 text-gray-500 hover:text-red-400"
              title="Delete category"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Children - only show if expanded */}
        {hasChildren && isExpanded && (
          <div>
            {node.children.map((child) => (
              <CategoryNode key={child.id} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  // Stats calculations
  const stats = {
    total: items.length,
    finishedGoods: items.filter((i) => i.item_type === "finished_good").length,
    components: items.filter((i) => i.item_type === "component").length,
    supplies: items.filter(
      (i) => i.item_type === "supply" && !i.material_type_id
    ).length,
    filaments: items.filter((i) => i.material_type_id).length,
    needsReorder: items.filter((i) => i.needs_reorder).length,
  };

  const getItemTypeStyle = (type, hasFilament = false) => {
    // If item has material_type_id, treat as filament regardless of item_type
    if (hasFilament) {
      return "bg-orange-500/20 text-orange-400";
    }
    const found = ITEM_TYPES.find((t) => t.value === type);
    if (!found) return "bg-gray-500/20 text-gray-400";
    return {
      blue: "bg-blue-500/20 text-blue-400",
      purple: "bg-purple-500/20 text-purple-400",
      orange: "bg-orange-500/20 text-orange-400",
      yellow: "bg-yellow-500/20 text-yellow-400",
      green: "bg-green-500/20 text-green-400",
    }[found.color];
  };

  // Save category
  const handleSaveCategory = async (catData) => {
    try {
      const url = editingCategory
        ? `${API_URL}/api/v1/items/categories/${editingCategory.id}`
        : `${API_URL}/api/v1/items/categories`;
      const method = editingCategory ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(catData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save category");
      }

      toast.success(editingCategory ? "Category updated" : "Category created");
      setShowCategoryModal(false);
      setEditingCategory(null);
      fetchCategories();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Bulk selection handlers
  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedItems(new Set(filteredItems.map((item) => item.id)));
    } else {
      setSelectedItems(new Set());
    }
  };

  const handleSelectItem = (itemId) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const isAllSelected =
    filteredItems.length > 0 && selectedItems.size === filteredItems.length;
  const isIndeterminate =
    selectedItems.size > 0 && selectedItems.size < filteredItems.length;

  // Bulk update handler
  const handleBulkUpdate = async (updateData) => {
    if (selectedItems.size === 0) {
      toast.warning("Please select at least one item");
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/v1/items/bulk-update`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          item_ids: Array.from(selectedItems),
          ...updateData,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update items");
      }

      const data = await res.json();
      toast.success(`Successfully updated ${data.message}`);
      setSelectedItems(new Set());
      setShowBulkUpdateModal(false);
      fetchItems(); // Refresh list
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Recost all items
  const handleRecostAll = async () => {
    if (
      !confirm(
        "Recost all items? This will update standard costs from BOM/Routing (manufactured) or average cost (purchased)."
      )
    ) {
      return;
    }
    setRecosting(true);
    setRecostResult(null);
    try {
      const params = new URLSearchParams();
      if (selectedCategory)
        params.set("category_id", selectedCategory.toString());
      if (filters.itemType !== "all") params.set("item_type", filters.itemType);

      const res = await fetch(`${API_URL}/api/v1/items/recost-all?${params}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to recost items");
      }

      const data = await res.json();
      setRecostResult(data);
      toast.success(`Recosted ${data.updated || 0} items`);
      fetchItems(); // Refresh list to show new costs
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRecosting(false);
    }
  };

  return (
    <div className="flex gap-6 h-full">
      {/* Left Sidebar - Categories */}
      <div className="w-64 flex-shrink-0">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-white">Categories</h2>
            <button
              onClick={() => {
                setEditingCategory(null);
                setShowCategoryModal(true);
              }}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              + Add
            </button>
          </div>

          <button
            onClick={() => setSelectedCategory(null)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-2 transition-colors ${
              selectedCategory === null
                ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            All Items
          </button>

          <div className="space-y-1">
            {categoryTree.map((node) => (
              <CategoryNode key={node.id} node={node} />
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Items</h1>
            <p className="text-gray-400 mt-1">
              Manage products, components, supplies, and services
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchItems}
              disabled={loading}
              className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
              title="Refresh items"
            >
              {loading ? "Loading..." : "↻ Refresh"}
            </button>
            <button
              onClick={handleRecostAll}
              disabled={recosting}
              className="px-4 py-2 bg-gray-800 border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-700 hover:text-white disabled:opacity-50"
            >
              {recosting ? "Recosting..." : "Recost All"}
            </button>
            <button
              onClick={() => {
                setShowMaterialModal(true);
              }}
              className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg font-medium transition-colors"
            >
              + New Material
            </button>
            <button
              onClick={() => {
                setEditingItem(null);
                setShowItemModal(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              + New Item
            </button>
          </div>
        </div>

        {/* Recost Result */}
        {recostResult && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-green-400 font-medium">
                  Recost complete: {recostResult.updated} items updated,{" "}
                  {recostResult.skipped} skipped
                </p>
                {recostResult.items?.length > 0 && (
                  <div className="mt-2 text-sm text-gray-400 max-h-32 overflow-auto">
                    {recostResult.items.slice(0, 10).map((item, i) => (
                      <div key={i}>
                        {item.sku}: ${item.old_cost.toFixed(2)} → $
                        {item.new_cost.toFixed(2)} ({item.cost_source})
                      </div>
                    ))}
                    {recostResult.items.length > 10 && (
                      <div className="text-gray-500">
                        ...and {recostResult.items.length - 10} more
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={() => setRecostResult(null)}
                className="text-gray-500 hover:text-white"
              >
                x
              </button>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search by SKU, name, or UPC..."
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500"
            />
          </div>
          <select
            value={filters.itemType}
            onChange={(e) =>
              setFilters({ ...filters, itemType: e.target.value })
            }
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
          >
            <option value="all">All Types</option>
            {ITEM_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-gray-400">
            <input
              type="checkbox"
              checked={filters.activeOnly}
              onChange={(e) =>
                setFilters({ ...filters, activeOnly: e.target.checked })
              }
              className="rounded"
            />
            Active only
          </label>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-6 gap-4">
          <StatCard variant="simple" title="Total Items" value={stats.total} color="neutral" />
          <StatCard variant="simple" title="Finished Goods" value={stats.finishedGoods} color="primary" />
          <StatCard variant="simple" title="Components" value={stats.components} color="secondary" />
          <StatCard variant="simple" title="Filaments" value={stats.filaments} color="primary" />
          <StatCard variant="simple" title="Supplies" value={stats.supplies} color="warning" />
          <StatCard variant="simple" title="Needs Reorder" value={stats.needsReorder} color="danger" />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        )}

        {/* Bulk Actions Toolbar */}
        {selectedItems.size > 0 && (
          <div className="bg-blue-600/20 border border-blue-500/30 rounded-xl p-4 mb-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-white font-medium">
                {selectedItems.size} item{selectedItems.size !== 1 ? "s" : ""}{" "}
                selected
              </span>
              <button
                onClick={() => setShowBulkUpdateModal(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium"
              >
                Bulk Update
              </button>
              <button
                onClick={() => setSelectedItems(new Set())}
                className="px-4 py-2 text-gray-400 hover:text-white text-sm"
              >
                Clear Selection
              </button>
            </div>
          </div>
        )}

        {/* Items Table */}
        {!loading && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase w-12">
                    <input
                      type="checkbox"
                      checked={isAllSelected}
                      ref={(input) => {
                        if (input) input.indeterminate = isIndeterminate;
                      }}
                      onChange={handleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    SKU
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Name
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Category
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Std Cost
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Price
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    On Hand
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Reserved
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Available
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-400 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-gray-800 hover:bg-gray-800/50"
                  >
                    <td className="py-3 px-4">
                      <input
                        type="checkbox"
                        checked={selectedItems.has(item.id)}
                        onChange={() => handleSelectItem(item.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="py-3 px-4 text-white font-mono text-sm">
                      {item.sku}
                    </td>
                    <td className="py-3 px-4 text-gray-300">{item.name}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${getItemTypeStyle(
                          item.item_type,
                          !!item.material_type_id
                        )}`}
                      >
                        {item.material_type_id
                          ? "Filament"
                          : ITEM_TYPES.find((t) => t.value === item.item_type)
                              ?.label || item.item_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400">
                      {item.category_name || "-"}
                    </td>
                    <td className="py-3 px-4 text-right text-gray-400">
                      {item.standard_cost
                        ? `$${parseFloat(item.standard_cost).toFixed(2)}`
                        : "-"}
                    </td>
                    <td className="py-3 px-4 text-right text-green-400">
                      {/* Hide price for materials/supplies - not for sale */}
                      {item.material_type_id || item.item_type === "supply"
                        ? "-"
                        : item.selling_price
                        ? `$${parseFloat(item.selling_price).toFixed(2)}`
                        : "-"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={
                          item.needs_reorder ? "text-red-400" : "text-gray-300"
                        }
                      >
                        {item.on_hand_qty != null
                          ? parseFloat(item.on_hand_qty).toFixed(0)
                          : "-"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-yellow-400">
                      {item.allocated_qty != null && parseFloat(item.allocated_qty) > 0
                        ? parseFloat(item.allocated_qty).toFixed(0)
                        : "-"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={
                          item.available_qty != null && parseFloat(item.available_qty) <= 0
                            ? "text-red-400"
                            : item.needs_reorder
                            ? "text-yellow-400"
                            : "text-green-400"
                        }
                      >
                        {item.available_qty != null
                          ? parseFloat(item.available_qty).toFixed(0)
                          : "-"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          item.active
                            ? "bg-green-500/20 text-green-400"
                            : "bg-gray-500/20 text-gray-400"
                        }`}
                      >
                        {item.active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => {
                            setEditingItem(item);
                            setShowItemModal(true);
                          }}
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          Edit
                        </button>
                        {(item.procurement_type === "make" ||
                          item.procurement_type === "make_or_buy") && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedItemForBOM(item);
                                setShowBOMEditor(true);
                              }}
                              className="text-purple-400 hover:text-purple-300 text-sm"
                              title="Edit BOM"
                            >
                              BOM
                            </button>
                            <button
                              onClick={() => {
                                setSelectedItemForRouting(item);
                                setShowRoutingEditor(true);
                              }}
                              className="text-green-400 hover:text-green-300 text-sm"
                              title="Edit Routing"
                            >
                              Route
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredItems.length === 0 && (
                  <tr>
                    <td
                      colSpan={12}
                      className="py-12 text-center text-gray-500"
                    >
                      No items found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700">
            <div className="text-sm text-gray-400">
              Showing {((pagination.page - 1) * pagination.pageSize) + 1} - {Math.min(pagination.page * pagination.pageSize, pagination.total)} of {pagination.total} items
            </div>
            <div className="flex items-center gap-2">
              <select
                value={pagination.pageSize}
                onChange={(e) => setPagination((prev) => ({ ...prev, pageSize: parseInt(e.target.value), page: 1 }))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm"
              >
                <option value={25}>25 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
                <option value={200}>200 per page</option>
              </select>
              <button
                onClick={() => setPagination((prev) => ({ ...prev, page: prev.page - 1 }))}
                disabled={!canGoPrev}
                className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
              >
                Previous
              </button>
              <span className="text-sm text-gray-400">
                Page {pagination.page} of {totalPages || 1}
              </span>
              <button
                onClick={() => setPagination((prev) => ({ ...prev, page: prev.page + 1 }))}
                disabled={!canGoNext}
                className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
              >
                Next
              </button>
            </div>
          </div>
          </div>
        )}
      </div>

      {/* Item Form */}
      <ItemForm
        isOpen={showItemModal}
        onClose={() => {
          setShowItemModal(false);
          setEditingItem(null);
        }}
        onSuccess={() => {
          setShowItemModal(false);
          setEditingItem(null);
          fetchItems();
        }}
        editingItem={editingItem}
      />

      {/* Material Form */}
      <MaterialForm
        isOpen={showMaterialModal}
        onClose={() => {
          setShowMaterialModal(false);
        }}
        onSuccess={(newItem) => {
          setShowMaterialModal(false);
          toast.success(`Material created: ${newItem?.sku || 'Success'}`);
          // Search for the new item so user can see it
          if (newItem?.sku) {
            setFilters((prev) => ({ ...prev, search: newItem.sku, itemType: "all" }));
            setSelectedCategory(null);
          } else {
            fetchItems();
          }
        }}
      />

      {/* BOM Editor */}
      <BOMEditor
        isOpen={showBOMEditor}
        onClose={() => {
          setShowBOMEditor(false);
          setSelectedItemForBOM(null);
        }}
        productId={selectedItemForBOM?.id}
        onSuccess={() => {
          setShowBOMEditor(false);
          setSelectedItemForBOM(null);
          fetchItems(); // Refresh to show updated BOM status
        }}
      />

      {/* Routing Editor */}
      <RoutingEditor
        isOpen={showRoutingEditor}
        onClose={() => {
          setShowRoutingEditor(false);
          setSelectedItemForRouting(null);
        }}
        productId={selectedItemForRouting?.id}
        onSuccess={() => {
          setShowRoutingEditor(false);
          setSelectedItemForRouting(null);
          fetchItems(); // Refresh to show updated routing status
        }}
      />

      {/* Category Modal */}
      {showCategoryModal && (
        <CategoryModal
          category={editingCategory}
          categories={categories}
          onSave={handleSaveCategory}
          onClose={() => {
            setShowCategoryModal(false);
            setEditingCategory(null);
          }}
        />
      )}

      {/* Bulk Update Modal */}
      {showBulkUpdateModal && (
        <BulkUpdateModal
          categories={categories}
          selectedCount={selectedItems.size}
          onSave={handleBulkUpdate}
          onClose={() => {
            setShowBulkUpdateModal(false);
            // Clear selection after update to prevent accidental updates
            setSelectedItems(new Set());
          }}
        />
      )}
    </div>
  );
}

// Bulk Update Modal
function BulkUpdateModal({ categories, selectedCount, onSave, onClose }) {
  const toast = useToast();
  const [form, setForm] = useState({
    category_id: "",
    item_type: "",
    procurement_type: "",
    is_active: "",
  });

  // Reset form when modal closes
  useEffect(() => {
    return () => {
      setForm({
        category_id: "",
        item_type: "",
        procurement_type: "",
        is_active: "",
      });
    };
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Build update data with only non-empty fields
    const updateData = {};
    // Handle category_id - must explicitly check for empty string
    // "0" means clear category, empty string means don't update
    if (form.category_id !== "") {
      const categoryId = parseInt(form.category_id);
      if (!isNaN(categoryId)) {
        updateData.category_id = categoryId;
      }
    }
    if (form.item_type) updateData.item_type = form.item_type;
    if (form.procurement_type)
      updateData.procurement_type = form.procurement_type;
    if (form.is_active !== "") updateData.is_active = form.is_active === "true";

    // Check if at least one field is being updated
    if (Object.keys(updateData).length === 0) {
      toast.warning("Please select at least one field to update");
      return;
    }

    onSave(updateData);
    // Reset form after submit
    setForm({
      category_id: "",
      item_type: "",
      procurement_type: "",
      is_active: "",
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold text-white mb-4">
          Bulk Update {selectedCount} Item{selectedCount !== 1 ? "s" : ""}
        </h2>
        <p className="text-gray-400 text-sm mb-6">
          Update the selected items. Leave fields empty to keep current values.
        </p>

        <form onSubmit={handleSubmit}>
          {/* Category */}
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">Category</label>
            <select
              value={form.category_id}
              onChange={(e) =>
                setForm({ ...form, category_id: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="">-- Keep Current --</option>
              <option value="0">-- No Category --</option>
              {categories
                .filter((cat) => cat.is_active)
                .map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
            </select>
          </div>

          {/* Item Type */}
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">
              Item Type
            </label>
            <select
              value={form.item_type}
              onChange={(e) => setForm({ ...form, item_type: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="">-- Keep Current --</option>
              {/* Filter out "filament" - it's a virtual type for display only.
                  In the DB, filaments are supplies with material_type_id set.
                  Use Material Import to create filaments. */}
              {ITEM_TYPES.filter((type) => type.value !== "filament").map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Procurement Type */}
          <div className="mb-4">
            <label className="block text-gray-400 text-sm mb-2">
              Procurement Type
            </label>
            <select
              value={form.procurement_type}
              onChange={(e) =>
                setForm({ ...form, procurement_type: e.target.value })
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="">-- Keep Current --</option>
              <option value="make">Make</option>
              <option value="buy">Buy</option>
              <option value="make_or_buy">Make or Buy</option>
            </select>
          </div>

          {/* Active Status */}
          <div className="mb-6">
            <label className="block text-gray-400 text-sm mb-2">Status</label>
            <select
              value={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="">-- Keep Current --</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500"
            >
              Update {selectedCount} Item{selectedCount !== 1 ? "s" : ""}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Category Create/Edit Modal
function CategoryModal({ category, categories, onSave, onClose }) {
  const [form, setForm] = useState({
    code: category?.code || "",
    name: category?.name || "",
    parent_id: category?.parent_id || "",
    description: category?.description || "",
    sort_order: category?.sort_order || 0,
    is_active: category?.is_active ?? true,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = { ...form };
    if (data.parent_id === "") data.parent_id = null;
    else if (data.parent_id) data.parent_id = parseInt(data.parent_id);
    data.sort_order = parseInt(data.sort_order) || 0;
    onSave(data);
  };

  // Filter out current category and its children for parent selection
  const availableParents = categories.filter((c) => c.id !== category?.id);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md">
        <div className="p-6 border-b border-gray-800">
          <h2 className="text-xl font-bold text-white">
            {category ? "Edit Category" : "Add New Category"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Code *</label>
            <input
              type="text"
              value={form.code}
              onChange={(e) =>
                setForm({ ...form, code: e.target.value.toUpperCase() })
              }
              required
              placeholder="e.g. FILAMENT"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Parent Category
            </label>
            <select
              value={form.parent_id}
              onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            >
              <option value="">-- Root Level --</option>
              {availableParents.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_path || c.name}
                </option>
              ))}
            </select>
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
              rows={2}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                Sort Order
              </label>
              <input
                type="number"
                value={form.sort_order}
                onChange={(e) =>
                  setForm({ ...form, sort_order: e.target.value })
                }
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
              />
            </div>
            <div className="flex items-center pt-6">
              <input
                type="checkbox"
                id="cat_active"
                checked={form.is_active}
                onChange={(e) =>
                  setForm({ ...form, is_active: e.target.checked })
                }
                className="rounded"
              />
              <label htmlFor="cat_active" className="text-gray-400 ml-2">
                Active
              </label>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4 pt-4 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-500 hover:to-purple-500"
            >
              {category ? "Save Changes" : "Create Category"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
