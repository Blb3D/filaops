/**
 * ItemForm - Simple single-screen form for creating/editing items
 *
 * Replaces the complex ItemWizard with a clean, focused form.
 * BOM and Routing are managed separately via dedicated editors.
 */
import { useState, useEffect, useCallback } from "react";
import { API_URL } from "../config/api";
import {
  validateRequired,
  validateNumber,
  validatePrice,
  validateSKU,
  validateForm,
  hasErrors,
} from "../utils/validation";
import { FormErrorSummary, RequiredIndicator } from "./ErrorMessage";

const ITEM_TYPES = [
  { value: "finished_good", label: "Finished Good" },
  { value: "component", label: "Component" },
  { value: "supply", label: "Supply" },
  { value: "service", label: "Service" },
];

const PROCUREMENT_TYPES = [
  { value: "make", label: "Make (Manufactured)" },
  { value: "buy", label: "Buy (Purchased)" },
  { value: "make_or_buy", label: "Make or Buy" },
];

export default function ItemForm({
  isOpen,
  onClose,
  onSuccess,
  editingItem = null,
}) {
  const token = localStorage.getItem("adminToken");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [errors, setErrors] = useState({});
  const [categories, setCategories] = useState([]);
  const [uomClasses, setUomClasses] = useState([]);

  const [formData, setFormData] = useState({
    sku: editingItem?.sku || "",
    name: editingItem?.name || "",
    description: editingItem?.description || "",
    item_type: editingItem?.item_type || "finished_good",
    procurement_type: editingItem?.procurement_type || "make",
    category_id: editingItem?.category_id || null,
    unit: editingItem?.unit || "EA",
    standard_cost: editingItem?.standard_cost || "",
    selling_price: editingItem?.selling_price || "",
  });

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/items/categories`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("ItemForm: fetchCategories failed", {
          endpoint: `${API_URL}/api/v1/items/categories`,
          message: err?.message,
          stack: err?.stack,
        });
      }
    }
  }, [token]);

  const fetchUomClasses = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/uom/classes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUomClasses(data);
      }
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("ItemForm: fetchUomClasses failed", {
          endpoint: `${API_URL}/api/v1/admin/uom/classes`,
          message: err?.message,
          stack: err?.stack,
        });
      }
      setUomClasses([]);
    }
  }, [token]);

  useEffect(() => {
    if (isOpen) {
      fetchCategories();
      fetchUomClasses();
      if (editingItem) {
        setFormData({
          sku: editingItem.sku || "",
          name: editingItem.name || "",
          description: editingItem.description || "",
          item_type: editingItem.item_type || "finished_good",
          procurement_type: editingItem.procurement_type || "make",
          category_id: editingItem.category_id || null,
          unit: editingItem.unit || "EA",
          standard_cost: editingItem.standard_cost || "",
          selling_price: editingItem.selling_price || "",
        });
      } else {
        // Reset form for new item
        setFormData({
          sku: "",
          name: "",
          description: "",
          item_type: "finished_good",
          procurement_type: "make",
          category_id: null,
          unit: "EA",
          standard_cost: "",
          selling_price: "",
        });
      }
      setError(null);
      setErrors({});
    }
  }, [isOpen, editingItem, fetchCategories, fetchUomClasses]);

  const validateFormData = () => {
    const validationRules = {
      name: [(v) => validateRequired(v, "Item name")],
      unit: [(v) => validateRequired(v, "Unit of measure")],
      item_type: [(v) => validateRequired(v, "Item type")],
      procurement_type: [(v) => validateRequired(v, "Procurement type")],
    };

    // Only validate SKU if it's provided (it's optional - can be auto-generated)
    if (formData.sku && formData.sku.trim()) {
      validationRules.sku = [(v) => validateSKU(v)];
    }

    // Validate numeric fields if they have values
    if (formData.standard_cost !== "" && formData.standard_cost !== null) {
      validationRules.standard_cost = [
        (v) => validatePrice(v, "Standard cost"),
      ];
    }

    if (formData.selling_price !== "" && formData.selling_price !== null) {
      validationRules.selling_price = [
        (v) => validatePrice(v, "Selling price"),
      ];
    }

    return validateForm(formData, validationRules);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setErrors({});

    // Validate form
    const validationErrors = validateFormData();
    if (hasErrors(validationErrors)) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);

    try {
      const payload = {
        sku: formData.sku,
        name: formData.name,
        description: formData.description || null,
        item_type: formData.item_type,
        procurement_type: formData.procurement_type,
        unit: formData.unit,
        standard_cost: formData.standard_cost
          ? parseFloat(formData.standard_cost)
          : null,
        selling_price: formData.selling_price
          ? parseFloat(formData.selling_price)
          : null,
        category_id: formData.category_id || null,
      };

      const url = editingItem
        ? `${API_URL}/api/v1/items/${editingItem.id}`
        : `${API_URL}/api/v1/items`;

      const method = editingItem ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save item");
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-white">
              {editingItem ? "Edit Item" : "Create New Item"}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl">
              {error}
            </div>
          )}

          <FormErrorSummary errors={errors} className="mb-4" />

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  SKU{" "}
                  <span className="text-gray-500 text-xs">
                    (auto-generated if empty)
                  </span>
                </label>
                <input
                  type="text"
                  value={formData.sku}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      sku: e.target.value.toUpperCase(),
                    })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none ${
                    errors.sku
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                  placeholder="Leave empty for auto-generation"
                />
                {errors.sku && (
                  <div className="text-red-400 text-sm mt-1">{errors.sku}</div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Unit <RequiredIndicator />
                </label>
                <select
                  value={formData.unit}
                  onChange={(e) =>
                    setFormData({ ...formData, unit: e.target.value })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none ${
                    errors.unit
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                >
                  {uomClasses.length > 0 ? (
                    uomClasses.map((cls) => (
                      <optgroup
                        key={cls.uom_class}
                        label={
                          cls.uom_class.charAt(0).toUpperCase() +
                          cls.uom_class.slice(1)
                        }
                      >
                        {cls.units.map((u) => (
                          <option key={u.code} value={u.code}>
                            {u.code} - {u.name}
                          </option>
                        ))}
                      </optgroup>
                    ))
                  ) : (
                    // Fallback if UOM API not available
                    <>
                      <option value="EA">EA - Each</option>
                      <option value="KG">KG - Kilogram</option>
                      <option value="G">G - Gram</option>
                      <option value="LB">LB - Pound</option>
                      <option value="M">M - Meter</option>
                      <option value="FT">FT - Foot</option>
                      <option value="HR">HR - Hour</option>
                    </>
                  )}
                </select>
                {errors.unit && (
                  <div className="text-red-400 text-sm mt-1">{errors.unit}</div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Name <RequiredIndicator />
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none ${
                  errors.name
                    ? "border-red-500 focus:border-red-500"
                    : "border-gray-700 focus:border-blue-500"
                }`}
                placeholder="Item name"
              />
              {errors.name && (
                <div className="text-red-400 text-sm mt-1">{errors.name}</div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                rows="3"
                placeholder="Item description"
              />
            </div>

            {/* Classification */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Item Type <RequiredIndicator />
                </label>
                <select
                  value={formData.item_type}
                  onChange={(e) =>
                    setFormData({ ...formData, item_type: e.target.value })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none ${
                    errors.item_type
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                >
                  {ITEM_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {errors.item_type && (
                  <div className="text-red-400 text-sm mt-1">
                    {errors.item_type}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Procurement Type <RequiredIndicator />
                </label>
                <select
                  value={formData.procurement_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      procurement_type: e.target.value,
                    })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none ${
                    errors.procurement_type
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                >
                  {PROCUREMENT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                {errors.procurement_type && (
                  <div className="text-red-400 text-sm mt-1">
                    {errors.procurement_type}
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Category
              </label>
              <select
                value={formData.category_id || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    category_id: e.target.value
                      ? parseInt(e.target.value)
                      : null,
                  })
                }
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="">No category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Pricing */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Standard Cost
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.standard_cost}
                  onChange={(e) =>
                    setFormData({ ...formData, standard_cost: e.target.value })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none ${
                    errors.standard_cost
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                  placeholder="0.00"
                />
                {errors.standard_cost && (
                  <div className="text-red-400 text-sm mt-1">
                    {errors.standard_cost}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Selling Price
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.selling_price}
                  onChange={(e) =>
                    setFormData({ ...formData, selling_price: e.target.value })
                  }
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white placeholder-gray-500 focus:outline-none ${
                    errors.selling_price
                      ? "border-red-500 focus:border-red-500"
                      : "border-gray-700 focus:border-blue-500"
                  }`}
                  placeholder="0.00"
                />
                {errors.selling_price && (
                  <div className="text-red-400 text-sm mt-1">
                    {errors.selling_price}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-700"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
                disabled={loading}
              >
                {loading
                  ? "Saving..."
                  : editingItem
                  ? "Update Item"
                  : "Create Item"}
              </button>
            </div>
          </form>

          {formData.procurement_type === "make" && (
            <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl text-sm text-blue-300">
              <strong>Note:</strong> This item requires a BOM and Routing.
              Create the item first, then add BOM and Routing from the item
              detail page.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
