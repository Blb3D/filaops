import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ToastProvider } from "./components/Toast";
import AdminLayout from "./components/AdminLayout";
import Setup from "./pages/Setup";
import Onboarding from "./pages/Onboarding";

// Admin pages
import AdminLogin from "./pages/admin/AdminLogin";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminOrders from "./pages/admin/AdminOrders";
import OrderDetail from "./pages/admin/OrderDetail";
import AdminBOM from "./pages/admin/AdminBOM";
import AdminItems from "./pages/admin/AdminItems";
import AdminPurchasing from "./pages/admin/AdminPurchasing";
import AdminProduction from "./pages/admin/AdminProduction";
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
import AdminSettings from "./pages/admin/AdminSettings";
// import AdminLicense from "./pages/admin/AdminLicense";  // Disabled until ready
import Pricing from "./pages/Pricing";

/**
 * Top-level application router that provides global toasts and registers all public and admin routes.
 *
 * The component wraps the route tree in a BrowserRouter and a ToastProvider, defines first-run pages
 * (setup, onboarding), auth and password-reset routes, a public pricing page, and an admin section
 * mounted at `/admin` which uses AdminLayout and includes nested admin routes and redirects.
 *
 * @returns {JSX.Element} The root React element containing the BrowserRouter, ToastProvider, and Routes.
 */
export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
      <Routes>
        {/* Redirect root to admin */}
        <Route path="/" element={<Navigate to="/admin" replace />} />

        {/* First-run setup */}
        <Route path="/setup" element={<Setup />} />
        <Route path="/onboarding" element={<Onboarding />} />

        {/* Auth */}
        <Route path="/admin/login" element={<AdminLogin />} />
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
          <Route path="settings" element={<AdminSettings />} />
        </Route>
      </Routes>
      </ToastProvider>
    </BrowserRouter>
  );
}