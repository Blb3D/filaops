/**
 * MaterialForm - Simple form for creating material items (filament)
 *
 * Uses the new POST /api/v1/items/material endpoint.
 * Pre-filled for material creation with material type and color selection.
 * Allows creating new colors on-the-fly if none exist for the material type.
 */
import { useState, useEffect } from "react";
import { API_URL } from "../config/api";

/**
 * Render a modal form for creating a material item (filament), including the ability to create a new color inline for the selected material type.
 *
 * Performs necessary network requests to fetch material types and colors, create a new color for the selected type, and submit the new material. Manages local loading and error states and invokes callbacks on close and on successful creation.
 *
 * @param {Object} props - Component props.
 * @param {boolean} props.isOpen - Whether the modal is visible.
 * @param {() => void} props.onClose - Callback invoked to close the modal.
 * @param {(createdMaterial: Object) => void} [props.onSuccess] - Optional callback invoked with the created material data after successful submission.
 * @returns {JSX.Element|null} A React element for the modal form when open, or `null` when closed.
 */
export default function MaterialForm({
  isOpen,
  onClose,
  onSuccess
}) {
  const token = localStorage.getItem("adminToken");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [materialTypes, setMaterialTypes] = useState([]);
  const [colors, setColors] = useState([]);
  const [selectedMaterialType, setSelectedMaterialType] = useState("");

  // Color creation state
  const [showColorForm, setShowColorForm] = useState(false);
  const [newColorName, setNewColorName] = useState("");
  const [newColorHex, setNewColorHex] = useState("#000000");
  const [creatingColor, setCreatingColor] = useState(false);

  const [formData, setFormData] = useState({
    material_type_code: "",
    color_code: "",
    initial_qty_kg: 0,
    cost_per_kg: "",
    selling_price: "",
  });

  useEffect(() => {
    if (isOpen) {
      fetchMaterialTypes();
      setFormData({
        material_type_code: "",
        color_code: "",
        initial_qty_kg: 0,
        cost_per_kg: "",
        selling_price: "",
      });
      setSelectedMaterialType("");
      setError(null);
      setShowColorForm(false);
      setNewColorName("");
      setNewColorHex("#000000");
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedMaterialType) {
      fetchColors(selectedMaterialType);
    } else {
      setColors([]);
    }
  }, [selectedMaterialType]);

  const fetchMaterialTypes = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/materials/types?customer_visible_only=false`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMaterialTypes(data.materials || []);
      }
    } catch (err) {
      // Material types fetch failure is non-critical - type selector will be empty
    }
  };

  const fetchColors = async (materialTypeCode) => {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/materials/types/${materialTypeCode}/colors?in_stock_only=false&customer_visible_only=false`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setColors(data.colors || []);
      }
    } catch (err) {
      // Colors fetch failure - color selector will be empty
      setColors([]);
    }
  };

  const handleCreateColor = async () => {
    if (!newColorName.trim()) {
      setError("Color name is required");
      return;
    }

    setCreatingColor(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_URL}/api/v1/materials/types/${selectedMaterialType}/colors`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: newColorName.trim(),
            hex_code: newColorHex || null,
          }),
        }
      );

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create color");
      }

      const data = await res.json();

      // Refresh colors list and select the new color
      await fetchColors(selectedMaterialType);
      setFormData({ ...formData, color_code: data.code });
      setShowColorForm(false);
      setNewColorName("");
      setNewColorHex("#000000");
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingColor(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        material_type_code: formData.material_type_code,
        color_code: formData.color_code,
        initial_qty_kg: parseFloat(formData.initial_qty_kg) || 0,
        cost_per_kg: formData.cost_per_kg ? parseFloat(formData.cost_per_kg) : null,
        selling_price: formData.selling_price ? parseFloat(formData.selling_price) : null,
      };

      const res = await fetch(`${API_URL}/api/v1/items/material`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to create material");
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

  const selectedMaterial = materialTypes.find(m => m.code === formData.material_type_code);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Create New Material</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Material Type */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Material Type <span className="text-red-500">*</span>
              </label>
              <select
                required
                value={formData.material_type_code}
                onChange={(e) => {
                  setFormData({ ...formData, material_type_code: e.target.value, color_code: "" });
                  setSelectedMaterialType(e.target.value);
                }}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="">Select material type...</option>
                {materialTypes.map((mt) => (
                  <option key={mt.code} value={mt.code}>
                    {mt.name} ({mt.base_material})
                  </option>
                ))}
              </select>
              {selectedMaterial && (
                <p className="mt-1 text-sm text-gray-600">{selectedMaterial.description}</p>
              )}
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Color <span className="text-red-500">*</span>
              </label>

              {!showColorForm ? (
                <>
                  <select
                    required={!showColorForm}
                    value={formData.color_code}
                    onChange={(e) => setFormData({ ...formData, color_code: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                    disabled={!formData.material_type_code}
                  >
                    <option value="">
                      {formData.material_type_code
                        ? colors.length === 0
                          ? "No colors available - create one below"
                          : "Select color..."
                        : "Select material type first"}
                    </option>
                    {colors.map((color) => (
                      <option key={color.code} value={color.code}>
                        {color.name} {color.hex && `(${color.hex})`}
                      </option>
                    ))}
                  </select>

                  {formData.material_type_code && (
                    <button
                      type="button"
                      onClick={() => setShowColorForm(true)}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                    >
                      <span>+</span> Create new color for this material
                    </button>
                  )}
                </>
              ) : (
                <div className="border rounded-md p-3 bg-gray-50 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700">New Color</span>
                    <button
                      type="button"
                      onClick={() => {
                        setShowColorForm(false);
                        setNewColorName("");
                        setNewColorHex("#000000");
                      }}
                      className="text-gray-500 hover:text-gray-700 text-sm"
                    >
                      Cancel
                    </button>
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Color Name *</label>
                    <input
                      type="text"
                      value={newColorName}
                      onChange={(e) => setNewColorName(e.target.value)}
                      placeholder="e.g., Mystic Blue"
                      className="w-full px-3 py-2 border rounded-md text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Hex Color (optional)</label>
                    <div className="flex gap-2 items-center">
                      <input
                        type="color"
                        value={newColorHex}
                        onChange={(e) => setNewColorHex(e.target.value)}
                        className="w-10 h-10 border rounded cursor-pointer"
                      />
                      <input
                        type="text"
                        value={newColorHex}
                        onChange={(e) => setNewColorHex(e.target.value)}
                        placeholder="#000000"
                        className="flex-1 px-3 py-2 border rounded-md text-sm"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleCreateColor}
                    disabled={creatingColor || !newColorName.trim()}
                    className="w-full px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 text-sm"
                  >
                    {creatingColor ? "Creating..." : "Create Color"}
                  </button>
                </div>
              )}
            </div>

            {/* Initial Quantity */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Initial Quantity (kg)
              </label>
              <input
                type="number"
                step="0.001"
                min="0"
                value={formData.initial_qty_kg}
                onChange={(e) => setFormData({ ...formData, initial_qty_kg: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="0.000"
              />
            </div>

            {/* Pricing */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Cost per kg
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.cost_per_kg}
                  onChange={(e) => setFormData({ ...formData, cost_per_kg: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Selling Price per kg
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={formData.selling_price}
                  onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="0.00"
                />
              </div>
            </div>

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
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                disabled={loading || !formData.material_type_code || !formData.color_code}
              >
                {loading ? "Creating..." : "Create Material"}
              </button>
            </div>
          </form>

          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
            <strong>Note:</strong> This will create a Product with SKU format: 
            MAT-{formData.material_type_code || "TYPE"}-{formData.color_code || "COLOR"}
          </div>
        </div>
      </div>
    </div>
  );
}
