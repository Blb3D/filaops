import React, { useState, useEffect, useRef } from "react";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";

const AdminSettings = () => {
  const toast = useToast();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const fileInputRef = useRef(null);

  // Form state
  const [form, setForm] = useState({
    company_name: "",
    company_address_line1: "",
    company_address_line2: "",
    company_city: "",
    company_state: "",
    company_zip: "",
    company_country: "USA",
    company_phone: "",
    company_email: "",
    company_website: "",
    tax_enabled: false,
    tax_rate_percent: "",
    tax_name: "Sales Tax",
    tax_registration_number: "",
    default_quote_validity_days: 30,
    quote_terms: "",
    quote_footer: "",
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem("adminToken");
      if (!token) {
        toast.error("Not logged in. Please log in again.");
        setLoading(false);
        return;
      }
      const response = await fetch(`${API_URL}/api/v1/settings/company`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setForm({
          company_name: data.company_name || "",
          company_address_line1: data.company_address_line1 || "",
          company_address_line2: data.company_address_line2 || "",
          company_city: data.company_city || "",
          company_state: data.company_state || "",
          company_zip: data.company_zip || "",
          company_country: data.company_country || "USA",
          company_phone: data.company_phone || "",
          company_email: data.company_email || "",
          company_website: data.company_website || "",
          tax_enabled: data.tax_enabled || false,
          tax_rate_percent: data.tax_rate_percent || "",
          tax_name: data.tax_name || "Sales Tax",
          tax_registration_number: data.tax_registration_number || "",
          default_quote_validity_days: data.default_quote_validity_days || 30,
          quote_terms: data.quote_terms || "",
          quote_footer: data.quote_footer || "",
        });
        } else {
        const errData = await response.json().catch(() => ({}));
        toast.error(errData.detail || `Error ${response.status}: Failed to load settings`);
      }
    } catch (err) {
      toast.error("Failed to load settings: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/company`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...form,
          tax_rate_percent: form.tax_rate_percent
            ? parseFloat(form.tax_rate_percent)
            : null,
          default_quote_validity_days: parseInt(form.default_quote_validity_days),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        toast.success("Settings saved successfully!");
      } else {
        const err = await response.json();
        toast.error(err.detail || "Failed to save settings");
      }
    } catch (err) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadingLogo(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/company/logo`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (response.ok) {
        toast.success("Logo uploaded successfully!");
        fetchSettings();
      } else {
        const err = await response.json();
        toast.error(err.detail || "Failed to upload logo");
      }
    } catch (err) {
      toast.error("Failed to upload logo");
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleLogoDelete = async () => {
    if (!confirm("Are you sure you want to delete the company logo?")) return;

    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/company/logo`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success("Logo deleted successfully!");
        fetchSettings();
      }
    } catch (err) {
      toast.error("Failed to delete logo");
    }
  };

  if (loading) {
    return <div className="p-6 text-white">Loading...</div>;
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Company Settings</h1>
        <p className="text-gray-400">
          Configure your company information, logo, and tax settings
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Company Logo */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Company Logo</h2>
          <div className="flex items-center gap-6">
            {settings?.has_logo ? (
              <div className="relative">
                <img
                  src={`${API_URL}/api/v1/settings/company/logo?t=${Date.now()}`}
                  alt="Company Logo"
                  className="w-32 h-32 object-contain bg-gray-700 rounded-lg"
                />
                <button
                  type="button"
                  onClick={handleLogoDelete}
                  className="absolute -top-2 -right-2 bg-red-600 hover:bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm"
                >
                  ×
                </button>
              </div>
            ) : (
              <div className="w-32 h-32 bg-gray-700 rounded-lg flex items-center justify-center text-gray-500">
                No Logo
              </div>
            )}
            <div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleLogoUpload}
                accept="image/png,image/jpeg,image/gif,image/webp"
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingLogo}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
              >
                {uploadingLogo ? "Uploading..." : settings?.has_logo ? "Change Logo" : "Upload Logo"}
              </button>
              <p className="text-sm text-gray-400 mt-2">
                PNG, JPEG, GIF, or WebP. Max 2MB.
              </p>
            </div>
          </div>
        </div>

        {/* Company Information */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">
            Company Information
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Company Name
              </label>
              <input
                type="text"
                name="company_name"
                value={form.company_name}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="Your Company Name"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Address Line 1
              </label>
              <input
                type="text"
                name="company_address_line1"
                value={form.company_address_line1}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="123 Main Street"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Address Line 2
              </label>
              <input
                type="text"
                name="company_address_line2"
                value={form.company_address_line2}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="Suite 100"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                City
              </label>
              <input
                type="text"
                name="company_city"
                value={form.company_city}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                State
              </label>
              <input
                type="text"
                name="company_state"
                value={form.company_state}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="TX"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                ZIP Code
              </label>
              <input
                type="text"
                name="company_zip"
                value={form.company_zip}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Country
              </label>
              <input
                type="text"
                name="company_country"
                value={form.company_country}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Phone
              </label>
              <input
                type="tel"
                name="company_phone"
                value={form.company_phone}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="(555) 123-4567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Email
              </label>
              <input
                type="email"
                name="company_email"
                value={form.company_email}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="info@yourcompany.com"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Website
              </label>
              <input
                type="url"
                name="company_website"
                value={form.company_website}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="https://yourcompany.com"
              />
            </div>
          </div>
        </div>

        {/* Tax Settings */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Tax Settings</h2>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="tax_enabled"
                name="tax_enabled"
                checked={form.tax_enabled}
                onChange={handleChange}
                className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="tax_enabled" className="text-white">
                Enable sales tax on quotes
              </label>
            </div>

            {form.tax_enabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-8">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Tax Rate (%)
                  </label>
                  <input
                    type="number"
                    name="tax_rate_percent"
                    value={form.tax_rate_percent}
                    onChange={handleChange}
                    step="0.01"
                    min="0"
                    max="100"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    placeholder="8.25"
                  />
                  <p className="text-sm text-gray-400 mt-1">
                    e.g., 8.25 for 8.25% tax
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Tax Name
                  </label>
                  <input
                    type="text"
                    name="tax_name"
                    value={form.tax_name}
                    onChange={handleChange}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    placeholder="Sales Tax"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Tax Registration Number (optional)
                  </label>
                  <input
                    type="text"
                    name="tax_registration_number"
                    value={form.tax_registration_number}
                    onChange={handleChange}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    placeholder="Your tax ID or VAT number"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quote Settings */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Quote Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Default Quote Validity (days)
              </label>
              <input
                type="number"
                name="default_quote_validity_days"
                value={form.default_quote_validity_days}
                onChange={handleChange}
                min="1"
                max="365"
                className="w-full md:w-48 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Quote Terms & Conditions
              </label>
              <textarea
                name="quote_terms"
                value={form.quote_terms}
                onChange={handleChange}
                rows={4}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="Enter your standard terms and conditions..."
              />
              <p className="text-sm text-gray-400 mt-1">
                Displayed on quote PDFs
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Quote Footer Message
              </label>
              <textarea
                name="quote_footer"
                value={form.quote_footer}
                onChange={handleChange}
                rows={2}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="Thank you for your business! Contact us at..."
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdminSettings;
