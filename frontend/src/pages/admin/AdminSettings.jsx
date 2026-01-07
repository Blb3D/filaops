import React, { useState, useEffect, useRef } from "react";
import { API_URL } from "../../config/api";
import { useToast } from "../../components/Toast";
import { useVersionCheck } from "../../hooks/useVersionCheck";
import { getCurrentVersion, getCurrentVersionSync, formatVersion } from "../../utils/version";

// Format phone number as (XXX) XXX-XXXX
const formatPhoneNumber = (value) => {
  const digits = value.replace(/\D/g, "").slice(0, 10);
  if (digits.length === 0) return "";
  if (digits.length <= 3) return `(${digits}`;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
};

const AdminSettings = () => {
  const toast = useToast();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const fileInputRef = useRef(null);
  const {
    latestVersion,
    updateAvailable,
    loading: checkingUpdate,
    checkForUpdates,
  } = useVersionCheck();
  const [checkingManually, setCheckingManually] = useState(false);
  const [currentVersion, setCurrentVersion] = useState(getCurrentVersionSync());

  // AI Settings state
  const [aiSettings, setAiSettings] = useState(null);
  const [aiForm, setAiForm] = useState({
    ai_provider: "",
    ai_api_key: "",
    ai_ollama_url: "http://localhost:11434",
    ai_ollama_model: "llama3.2",
    external_ai_blocked: false,
  });
  const [savingAi, setSavingAi] = useState(false);
  const [testingAi, setTestingAi] = useState(false);
  const [startingOllama, setStartingOllama] = useState(false);
  const [anthropicStatus, setAnthropicStatus] = useState({ installed: false, version: null, loading: true });
  const [installingAnthropic, setInstallingAnthropic] = useState(false);

  // Common timezones (grouped by region)
  const timezoneOptions = [
    // Americas
    { value: "America/New_York", label: "US - Eastern Time (ET)" },
    { value: "America/Chicago", label: "US - Central Time (CT)" },
    { value: "America/Denver", label: "US - Mountain Time (MT)" },
    { value: "America/Phoenix", label: "US - Arizona (no DST)" },
    { value: "America/Los_Angeles", label: "US - Pacific Time (PT)" },
    { value: "America/Anchorage", label: "US - Alaska Time (AKT)" },
    { value: "Pacific/Honolulu", label: "US - Hawaii Time (HT)" },
    { value: "America/Toronto", label: "Canada - Eastern" },
    { value: "America/Vancouver", label: "Canada - Pacific" },
    { value: "America/Mexico_City", label: "Mexico - Central" },
    { value: "America/Sao_Paulo", label: "Brazil - Sao Paulo" },
    // Europe
    { value: "Europe/London", label: "UK - London (GMT/BST)" },
    { value: "Europe/Paris", label: "Europe - Central (CET)" },
    { value: "Europe/Berlin", label: "Germany - Berlin" },
    { value: "Europe/Amsterdam", label: "Netherlands - Amsterdam" },
    // Asia
    { value: "Asia/Dubai", label: "UAE - Dubai (GST)" },
    { value: "Asia/Kolkata", label: "India - IST" },
    { value: "Asia/Singapore", label: "Singapore (SGT)" },
    { value: "Asia/Hong_Kong", label: "Hong Kong (HKT)" },
    { value: "Asia/Tokyo", label: "Japan - Tokyo (JST)" },
    { value: "Asia/Shanghai", label: "China - Shanghai (CST)" },
    { value: "Asia/Seoul", label: "South Korea - Seoul (KST)" },
    // Australia & Pacific
    { value: "Australia/Perth", label: "Australia - Perth (AWST)" },
    { value: "Australia/Adelaide", label: "Australia - Adelaide (ACST)" },
    { value: "Australia/Sydney", label: "Australia - Sydney (AEST)" },
    { value: "Australia/Brisbane", label: "Australia - Brisbane (no DST)" },
    { value: "Australia/Melbourne", label: "Australia - Melbourne (AEST)" },
    { value: "Pacific/Auckland", label: "New Zealand (NZST)" },
    // UTC
    { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  ];

  // Form state
  const [form, setForm] = useState({
    company_name: "",
    company_address_line1: "",
    company_address_line2: "",
    company_city: "",
    company_state: "",
    company_zip: "",
    company_country: "USA",
    timezone: "America/New_York",
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
    business_hours_start: 8,
    business_hours_end: 16,
    business_days_per_week: 5,
    business_work_days: "0,1,2,3,4", // Mon-Fri
  });

  useEffect(() => {
    fetchSettings();
    fetchCurrentVersion();
    fetchAiSettings();
    // checkAnthropicStatus is called inside fetchAiSettings when relevant
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchCurrentVersion = async () => {
    try {
      const version = await getCurrentVersion();
      setCurrentVersion(version);
    } catch (error) {
      console.error('Failed to fetch current version:', error);
      // Keep the sync fallback version
    }
  };

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
          timezone: data.timezone || "America/New_York",
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
          business_hours_start: data.business_hours_start ?? 8,
          business_hours_end: data.business_hours_end ?? 16,
          business_days_per_week: data.business_days_per_week ?? 5,
          business_work_days: data.business_work_days || "0,1,2,3,4",
        });
      } else {
        const errData = await response.json().catch(() => ({}));
        toast.error(
          errData.detail || `Error ${response.status}: Failed to load settings`
        );
      }
    } catch (error) {
      toast.error("Failed to load settings: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
          default_quote_validity_days: parseInt(
            form.default_quote_validity_days
          ),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        toast.success("Settings saved successfully!");
      } else {
        const errData = await response.json();
        toast.error(errData.detail || "Failed to save settings");
      }
    } catch (error) {
      toast.error("Failed to save settings: " + error.message);
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
        const errData = await response.json();
        toast.error(errData.detail || "Failed to upload logo");
      }
    } catch (error) {
      toast.error("Failed to upload logo: " + error.message);
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
    } catch (error) {
      toast.error("Failed to delete logo: " + error.message);
    }
  };

  // AI Settings functions
  const fetchAiSettings = async () => {
    try {
      const token = localStorage.getItem("adminToken");
      if (!token) return;

      const response = await fetch(`${API_URL}/api/v1/settings/ai`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setAiSettings(data);
        setAiForm({
          ai_provider: data.ai_provider || "",
          ai_api_key: "", // Don't populate - it's masked
          ai_ollama_url: data.ai_ollama_url || "http://localhost:11434",
          ai_ollama_model: data.ai_ollama_model || "llama3.2",
          external_ai_blocked: data.external_ai_blocked || false,
        });
        // Only check Anthropic package status if relevant (anthropic selected or no provider)
        if (data.ai_provider === "anthropic" || !data.ai_provider) {
          checkAnthropicStatus();
        } else {
          // Not using Anthropic, so mark loading as done
          setAnthropicStatus((prev) => ({ ...prev, loading: false }));
        }
      }
    } catch (error) {
      console.error("Failed to fetch AI settings:", error);
      setAnthropicStatus((prev) => ({ ...prev, loading: false }));
    }
  };

  const checkAnthropicStatus = async () => {
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/ai/anthropic-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setAnthropicStatus({ ...data, loading: false });
      } else {
        setAnthropicStatus((prev) => ({ ...prev, loading: false }));
      }
    } catch (error) {
      console.error("Failed to check anthropic status:", error);
      setAnthropicStatus((prev) => ({ ...prev, loading: false }));
    }
  };

  const handleInstallAnthropic = async () => {
    setInstallingAnthropic(true);
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/ai/install-anthropic`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await response.json();
      if (response.ok && data.success) {
        toast.success(data.message);
        // Recheck status
        await checkAnthropicStatus();
      } else {
        toast.error(data.message || "Failed to install package");
      }
    } catch (error) {
      toast.error("Failed to install package: " + error.message);
    } finally {
      setInstallingAnthropic(false);
    }
  };

  const handleAiFormChange = (e) => {
    const { name, value } = e.target;
    setAiForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveAiSettings = async () => {
    setSavingAi(true);
    try {
      const token = localStorage.getItem("adminToken");

      // Build payload - only include non-empty values
      const payload = {};
      if (aiForm.ai_provider !== undefined) {
        payload.ai_provider = aiForm.ai_provider || null;
      }
      if (aiForm.ai_api_key) {
        payload.ai_api_key = aiForm.ai_api_key;
      }
      if (aiForm.ai_ollama_url) {
        payload.ai_ollama_url = aiForm.ai_ollama_url;
      }
      if (aiForm.ai_ollama_model) {
        payload.ai_ollama_model = aiForm.ai_ollama_model;
      }
      if (aiForm.ai_anthropic_model) {
        payload.ai_anthropic_model = aiForm.ai_anthropic_model;
      }

      const response = await fetch(`${API_URL}/api/v1/settings/ai`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        setAiSettings(data);
        setAiForm((prev) => ({ ...prev, ai_api_key: "" })); // Clear API key field
        toast.success("AI settings saved successfully!");
      } else {
        const errData = await response.json();
        toast.error(errData.detail || "Failed to save AI settings");
      }
    } catch (error) {
      toast.error("Failed to save AI settings: " + error.message);
    } finally {
      setSavingAi(false);
    }
  };

  const handleTestAiConnection = async () => {
    setTestingAi(true);
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/ai/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await response.json();
      if (response.ok && data.success) {
        toast.success(data.message || "AI connection successful!");
      } else {
        toast.error(data.message || "AI connection failed");
      }
    } catch (error) {
      toast.error("Failed to test AI connection: " + error.message);
    } finally {
      setTestingAi(false);
    }
  };

  const handleClearAiSettings = async () => {
    if (!confirm("Are you sure you want to disable AI and clear all settings?")) return;

    setSavingAi(true);
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/ai`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ai_provider: null,
          ai_api_key: "",
        }),
      });

      if (response.ok) {
        await fetchAiSettings();
        toast.success("AI settings cleared");
      } else {
        const errData = await response.json();
        toast.error(errData.detail || "Failed to clear AI settings");
      }
    } catch (error) {
      toast.error("Failed to clear AI settings: " + error.message);
    } finally {
      setSavingAi(false);
    }
  };

  const handleStartOllama = async () => {
    setStartingOllama(true);
    try {
      const token = localStorage.getItem("adminToken");
      const response = await fetch(`${API_URL}/api/v1/settings/ai/start-ollama`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await response.json();
      if (response.ok && data.success) {
        toast.success(data.message || "Ollama started!");
      } else {
        toast.error(data.message || "Failed to start Ollama");
      }
    } catch (error) {
      toast.error("Failed to start Ollama: " + error.message);
    } finally {
      setStartingOllama(false);
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
          <h2 className="text-xl font-semibold text-white mb-4">
            Company Logo
          </h2>
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
                {uploadingLogo
                  ? "Uploading..."
                  : settings?.has_logo
                  ? "Change Logo"
                  : "Upload Logo"}
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
                Timezone
              </label>
              <select
                name="timezone"
                value={form.timezone}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              >
                {timezoneOptions.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
              <p className="text-sm text-gray-400 mt-1">
                Used for date/time displays in reports and charts
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Phone
              </label>
              <input
                type="tel"
                name="company_phone"
                value={form.company_phone}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    company_phone: formatPhoneNumber(e.target.value),
                  }))
                }
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
          <h2 className="text-xl font-semibold text-white mb-4">
            Tax Settings
          </h2>
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
          <h2 className="text-xl font-semibold text-white mb-4">
            Quote Settings
          </h2>
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

        {/* Business Hours Settings */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">
            Business Hours (Production Operations)
          </h2>
          <p className="text-sm text-gray-400 mb-4">
            Configure default business hours for non-printer operations. These hours apply to all work centers except printer pools.
            Printer pools run 20 hours/day (4am-12am, daily) and are not affected by these settings.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Start Time (Hour)
              </label>
              <input
                type="number"
                name="business_hours_start"
                value={form.business_hours_start}
                onChange={handleChange}
                min="0"
                max="23"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="8"
              />
              <p className="text-sm text-gray-400 mt-1">
                0-23 (e.g., 8 for 8am)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                End Time (Hour)
              </label>
              <input
                type="number"
                name="business_hours_end"
                value={form.business_hours_end}
                onChange={handleChange}
                min="0"
                max="23"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="16"
              />
              <p className="text-sm text-gray-400 mt-1">
                0-23 (e.g., 16 for 4pm)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Days Per Week
              </label>
              <input
                type="number"
                name="business_days_per_week"
                value={form.business_days_per_week}
                onChange={handleChange}
                min="1"
                max="7"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                placeholder="5"
              />
              <p className="text-sm text-gray-400 mt-1">
                1-7 (default: 5 for Mon-Fri)
              </p>
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Work Days (comma-separated)
            </label>
            <input
              type="text"
              name="business_work_days"
              value={form.business_work_days}
              onChange={handleChange}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              placeholder="0,1,2,3,4"
            />
            <p className="text-sm text-gray-400 mt-1">
              0=Monday, 1=Tuesday, ..., 6=Sunday. Example: "0,1,2,3,4" for Mon-Fri
            </p>
          </div>
        </div>

        {/* AI Configuration */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">
            AI Configuration
          </h2>
          <p className="text-sm text-gray-400 mb-4">
            Configure AI for enhanced invoice parsing. When enabled, invoices can be automatically
            parsed to extract line items, vendor information, and amounts.
          </p>

          {/* Block External AI Toggle */}
          <div className={`mb-6 p-4 rounded-lg border-2 ${aiForm.external_ai_blocked ? 'border-green-600 bg-green-900/20' : 'border-gray-600 bg-gray-700/50'}`}>
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <svg className={`w-5 h-5 ${aiForm.external_ai_blocked ? 'text-green-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <h3 className="text-white font-bold">Block External AI Services</h3>
                </div>
                <p className="text-gray-400 text-sm mt-1">
                  {aiForm.external_ai_blocked
                    ? "External AI is blocked. Only local AI (Ollama) can be used. No data leaves this machine."
                    : "Enable to force local-only AI processing. Blocks cloud AI providers for data privacy."}
                </p>
              </div>
              <button
                type="button"
                onClick={async () => {
                  const newValue = !aiForm.external_ai_blocked;
                  setSavingAi(true);
                  try {
                    const token = localStorage.getItem("adminToken");
                    const response = await fetch(`${API_URL}/api/v1/settings/ai`, {
                      method: "PATCH",
                      headers: {
                        Authorization: `Bearer ${token}`,
                        "Content-Type": "application/json",
                      },
                      body: JSON.stringify({ external_ai_blocked: newValue }),
                    });
                    if (response.ok) {
                      const data = await response.json();
                      setAiSettings(data);
                      setAiForm((prev) => ({
                        ...prev,
                        external_ai_blocked: data.external_ai_blocked,
                        ai_provider: data.ai_provider || "",
                      }));
                      toast.success(newValue ? "External AI blocked - data stays local" : "External AI unblocked");
                    } else {
                      const errData = await response.json();
                      toast.error(errData.detail || "Failed to update setting");
                    }
                  } catch (error) {
                    toast.error("Failed to update setting: " + error.message);
                  } finally {
                    setSavingAi(false);
                  }
                }}
                disabled={savingAi}
                className={`ml-4 relative inline-flex h-8 w-14 items-center rounded-full transition-colors ${
                  aiForm.external_ai_blocked ? 'bg-green-600' : 'bg-gray-600'
                } ${savingAi ? 'opacity-50' : ''}`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                    aiForm.external_ai_blocked ? 'translate-x-7' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Status indicator */}
          {aiSettings && (
            <div className="mb-4 p-3 rounded-lg bg-gray-700">
              <div className="flex items-center gap-2">
                <span
                  className={`w-3 h-3 rounded-full ${
                    aiSettings.ai_status === "configured"
                      ? "bg-green-500"
                      : aiSettings.ai_status === "error"
                      ? "bg-red-500"
                      : "bg-yellow-500"
                  }`}
                />
                <span className="text-white font-medium">
                  {aiSettings.ai_status === "configured"
                    ? "AI Configured"
                    : aiSettings.ai_status === "error"
                    ? "Configuration Error"
                    : "Not Configured"}
                </span>
              </div>
              {aiSettings.ai_status_message && (
                <p className="text-sm text-gray-400 mt-1 ml-5">
                  {aiSettings.ai_status_message}
                </p>
              )}
              {aiSettings.ai_api_key_masked && (
                <p className="text-sm text-gray-400 mt-1 ml-5">
                  API Key: {aiSettings.ai_api_key_masked}
                </p>
              )}
            </div>
          )}

          <div className="space-y-4">
            {/* Provider Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                AI Provider
              </label>
              <select
                name="ai_provider"
                value={aiForm.ai_provider}
                onChange={handleAiFormChange}
                className="w-full md:w-64 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              >
                <option value="">Disabled</option>
                <option value="anthropic" disabled={aiForm.external_ai_blocked}>
                  Anthropic Claude {aiForm.external_ai_blocked && "(blocked)"}
                </option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>

            {/* Anthropic Settings */}
            {aiForm.ai_provider === "anthropic" && (
              <div className="pl-4 border-l-2 border-blue-600 space-y-4">
                <div className="p-3 bg-gray-700 rounded-lg border-l-4 border-yellow-500">
                  <p className="text-sm text-yellow-300 font-medium mb-1">
                    Data Privacy Notice
                  </p>
                  <p className="text-sm text-gray-300">
                    <strong>Anthropic Claude</strong> is a cloud-based AI service. Invoice and purchase order
                    data (vendor names, amounts, line items) will be sent to Anthropic's servers for processing.
                  </p>
                  <p className="text-sm text-gray-400 mt-2">
                    <strong>Not recommended</strong> for businesses with data compliance requirements
                    (HIPAA, ITAR, SOX, GDPR, etc.). Consider <strong>Ollama</strong> for fully local processing.
                  </p>
                  <p className="text-sm text-gray-400 mt-2">
                    Usage is billed per request (typically a few cents per invoice).{" "}
                    <a
                      href="https://www.anthropic.com/pricing"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:underline"
                    >
                      See pricing
                    </a>
                  </p>
                </div>

                {/* Package Installation Check */}
                {!anthropicStatus.installed && (
                  <div className="p-3 bg-red-900/30 border border-red-600 rounded-lg">
                    <p className="text-sm text-red-300 font-medium mb-2">
                      Required Package Not Installed
                    </p>
                    <p className="text-sm text-gray-300 mb-3">
                      The Anthropic Python package needs to be installed before you can use Claude AI.
                    </p>
                    <button
                      type="button"
                      onClick={handleInstallAnthropic}
                      disabled={installingAnthropic}
                      className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                    >
                      {installingAnthropic ? (
                        <>
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Installing...
                        </>
                      ) : (
                        "Install Anthropic Package"
                      )}
                    </button>
                  </div>
                )}

                {anthropicStatus.installed && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        API Key
                      </label>
                      <input
                        type="password"
                        name="ai_api_key"
                        value={aiForm.ai_api_key}
                        onChange={handleAiFormChange}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                        placeholder={
                          aiSettings?.ai_api_key_set
                            ? "••••••••••••••• (key is set)"
                            : "sk-ant-..."
                        }
                      />
                      <p className="text-sm text-gray-400 mt-1">
                        Get your API key from{" "}
                        <a
                          href="https://console.anthropic.com/account/keys"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:underline"
                        >
                          console.anthropic.com
                        </a>
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">
                        Model
                      </label>
                      <select
                        name="ai_anthropic_model"
                        value={aiForm.ai_anthropic_model}
                        onChange={handleAiFormChange}
                        className="w-full md:w-96 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                      >
                        <option value="claude-haiku-3-5-20241022">
                          Haiku 3.5 - Fastest (~$0.001/doc)
                        </option>
                        <option value="claude-sonnet-4-20250514">
                          Sonnet 4 - Balanced (~$0.004/doc)
                        </option>
                        <option value="claude-opus-4-5-20251101">
                          Opus 4.5 - Best Quality (~$0.02/doc)
                        </option>
                      </select>
                      <p className="text-sm text-gray-400 mt-1">
                        Cost estimates based on ~2,000 token invoices. Opus provides best extraction accuracy.
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Ollama Settings */}
            {aiForm.ai_provider === "ollama" && (
              <div className="pl-4 border-l-2 border-green-600 space-y-4">
                <div className="p-3 bg-gray-700 rounded-lg border-l-4 border-green-500">
                  <p className="text-sm text-green-300 font-medium mb-1">
                    Privacy-First Option
                  </p>
                  <p className="text-sm text-gray-300">
                    <strong>Ollama</strong> runs AI models entirely on your computer. No invoice or purchase
                    order data ever leaves your machine - ideal for regulated industries and sensitive data.
                  </p>
                  <p className="text-sm text-gray-400 mt-2">
                    First-time setup requires downloading a model (2-8 GB). Processing speed depends on
                    your computer's hardware (GPU recommended but not required).
                  </p>
                  <p className="text-sm text-gray-400 mt-2">
                    <a
                      href="https://ollama.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-400 hover:underline"
                    >
                      Download Ollama
                    </a>
                    {" "}if not already installed.
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Ollama Server URL
                  </label>
                  <input
                    type="text"
                    name="ai_ollama_url"
                    value={aiForm.ai_ollama_url}
                    onChange={handleAiFormChange}
                    className="w-full md:w-96 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    placeholder="http://localhost:11434"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Model Name
                  </label>
                  <input
                    type="text"
                    name="ai_ollama_model"
                    value={aiForm.ai_ollama_model}
                    onChange={handleAiFormChange}
                    className="w-full md:w-64 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    placeholder="llama3.2"
                  />
                  <p className="text-sm text-gray-400 mt-1">
                    Common models: llama3.2, mistral, codellama
                  </p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={handleSaveAiSettings}
                disabled={savingAi}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
              >
                {savingAi ? "Saving..." : "Save AI Settings"}
              </button>
              {aiForm.ai_provider && (
                <button
                  type="button"
                  onClick={handleTestAiConnection}
                  disabled={testingAi || savingAi}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  {testingAi ? "Testing..." : "Test Connection"}
                </button>
              )}
              {aiForm.ai_provider === "ollama" && (
                <button
                  type="button"
                  onClick={handleStartOllama}
                  disabled={startingOllama || savingAi}
                  className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  {startingOllama ? "Starting..." : "Start Ollama"}
                </button>
              )}
              {aiSettings?.ai_provider && (
                <button
                  type="button"
                  onClick={handleClearAiSettings}
                  disabled={savingAi}
                  className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Disable AI
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Version & Updates */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">
            Version & Updates
          </h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-400 mb-2">Current Version</p>
              <p className="text-lg font-semibold text-white">
                v{formatVersion(currentVersion)}
              </p>
            </div>

            {latestVersion && (
              <div>
                <p className="text-sm text-gray-400 mb-2">Latest Version</p>
                <div className="flex items-center gap-3">
                  <p className="text-lg font-semibold text-white">
                    v{formatVersion(latestVersion)}
                  </p>
                  {updateAvailable ? (
                    <span className="px-2 py-1 bg-blue-600 text-blue-100 text-xs rounded-md">
                      Update Available
                    </span>
                  ) : (
                    <span className="px-2 py-1 bg-green-600 text-green-100 text-xs rounded-md">
                      Up to Date
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={async () => {
                  setCheckingManually(true);
                  await checkForUpdates(true);
                  setCheckingManually(false);
                  if (updateAvailable) {
                    toast.success(
                      `Update available: v${formatVersion(latestVersion)}`
                    );
                  } else {
                    toast.success("You're running the latest version!");
                  }
                }}
                disabled={checkingUpdate || checkingManually}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors text-sm"
              >
                {checkingUpdate || checkingManually
                  ? "Checking..."
                  : "Check for Updates"}
              </button>
              {latestVersion && updateAvailable && (
                <a
                  href={`https://github.com/Blb3D/filaops/releases/tag/v${formatVersion(
                    latestVersion
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-sm underline"
                >
                  View Release Notes
                </a>
              )}
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
