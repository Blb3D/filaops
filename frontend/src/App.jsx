import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { createContext, useMemo } from "react";
import { ToastProvider } from "./components/Toast";
import { createApiClient } from "./lib/apiClient";
import { API_URL } from "./config/api";
import ErrorBoundary from "./components/ErrorBoundary";
import ApiErrorToaster from "./components/ApiErrorToaster";
import UpgradeModal from "./components/UpgradeModal";
import AdminLayout from "./components/AdminLayout";
import Setup from "./pages/Setup";
import Onboarding from "./pages/Onboarding";

export const ApiContext = createContext(null);

// Admin pages
import AdminLogin from "./pages/admin/AdminLogin";
import ForgotPassword from "./pages/admin/ForgotPassword";
import ResetPassword from "./pages/admin/ResetPassword";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminOrders from "./pages/admin/AdminOrders";
import OrderDetail from "./pages/admin/OrderDetail";
import AdminBOM from "./pages/admin/AdminBOM";
import AdminItems from "./pages/admin/AdminItems";
import AdminPurchasing from "./pages/admin/AdminPurchasing";
import AdminProduction from "./pages/admin/AdminProduction";
import ProductionOrderDetail from "./pages/admin/ProductionOrderDetail";
import AdminShipping from "./pages/admin/AdminShipping";
import AdminManufacturing from "./pages/admin/AdminManufacturing";
import AdminPasswordResetApproval from "./pages/admin/AdminPasswordResetApproval";
import AdminCustomers from "./pages/admin/AdminCustomers";
import AdminInventoryTransactions from "./pages/admin/AdminInventoryTransactions";
import AdminAnalytics from "./pages/admin/AdminAnalytics";
import AdminMaterialImport from "./pages/admin/AdminMaterialImport";
import AdminOrderImport from "./pages/admin/AdminOrderImport";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminQuotes from "./pages/admin/AdminQuotes";
import AdminPayments from "./pages/admin/AdminPayments";
import AdminSettings from "./pages/admin/AdminSettings";
import AdminLocations from "./pages/admin/AdminLocations";
import AdminAccounting from "./pages/admin/AdminAccounting";
import AdminPrinters from "./pages/admin/AdminPrinters";
import AdminScrapReasons from "./pages/admin/AdminScrapReasons";
import AdminSpools from "./pages/admin/AdminSpools";
import MaterialTraceability from "./pages/admin/quality/MaterialTraceability";
// import AdminLicense from "./pages/admin/AdminLicense";  // Disabled until ready
import Pricing from "./pages/Pricing";

export default function App() {
  const api = useMemo(
    () =>
      createApiClient({
        baseUrl: API_URL,
        getToken: () => localStorage.getItem("adminToken"),
        onUnauthorized: async () => {
          localStorage.removeItem("adminToken");
          // optional: redirect to login
          window.location.href = "/admin/login";
        },
        onError: (err) => {
          // why: centralized logging hook (also toasts via ApiErrorToaster)
           
          console.warn("API error:", err.status, err.message);
        },
      }),
    []
  );

  return (
    <ErrorBoundary>
      <ApiContext.Provider value={api}>
        <ToastProvider>
          {/* Global API error toasts */}
          <ApiErrorToaster />
          {/* Upgrade modal for tier limits */}
          <UpgradeModal />
          <BrowserRouter>
        <Routes>
          {/* Redirect root to admin */}
          <Route path="/" element={<Navigate to="/admin" replace />} />

          {/* First-run setup */}
          <Route path="/setup" element={<Setup />} />
          <Route path="/onboarding" element={<Onboarding />} />

          {/* Auth */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password/:token" element={<ResetPassword />} />
          <Route
            path="/admin/password-reset/:action/:token"
            element={<AdminPasswordResetApproval />}
          />

          {/* Public Pricing Page */}
          <Route path="/pricing" element={<Pricing />} />

          {/* ERP Admin Panel */}
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="orders/:orderId" element={<OrderDetail />} />
            <Route path="quotes" element={<AdminQuotes />} />
            <Route path="payments" element={<AdminPayments />} />
            <Route path="customers" element={<AdminCustomers />} />
            <Route path="bom" element={<AdminBOM />} />
            <Route
              path="products"
              element={<Navigate to="/admin/items" replace />}
            />
            <Route path="items" element={<AdminItems />} />
            <Route path="purchasing" element={<AdminPurchasing />} />
            <Route path="manufacturing" element={<AdminManufacturing />} />
            <Route path="production" element={<AdminProduction />} />
            <Route path="production/:orderId" element={<ProductionOrderDetail />} />
            <Route path="shipping" element={<AdminShipping />} />
            <Route path="analytics" element={<AdminAnalytics />} />
            <Route path="materials/import" element={<AdminMaterialImport />} />
            <Route path="orders/import" element={<AdminOrderImport />} />
            {/* <Route path="license" element={<AdminLicense />} />  Disabled until ready */}
            <Route
              path="inventory/transactions"
              element={<AdminInventoryTransactions />}
            />
            <Route path="users" element={<AdminUsers />} />
            <Route path="locations" element={<AdminLocations />} />
            <Route path="accounting" element={<AdminAccounting />} />
            <Route path="printers" element={<AdminPrinters />} />
            <Route path="scrap-reasons" element={<AdminScrapReasons />} />
            <Route path="spools" element={<AdminSpools />} />
            <Route path="quality/traceability" element={<MaterialTraceability />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
        </Routes>
          </BrowserRouter>
        </ToastProvider>
      </ApiContext.Provider>
    </ErrorBoundary>
  );
}
