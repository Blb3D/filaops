import { createContext, useContext, useState, useCallback } from "react";

const ToastContext = createContext(null);

/**
 * Provides toast helper methods via context and renders a toast container alongside its children.
 *
 * The provider manages an internal list of toasts and exposes methods for success, error,
 * warning, and info toasts that create and optionally auto-dismiss notifications.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child elements that will be wrapped by the provider.
 * @returns {JSX.Element} A React element that supplies toast methods through context and displays active toasts.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = "info", duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = {
    success: (msg, duration) => addToast(msg, "success", duration),
    error: (msg, duration) => addToast(msg, "error", duration),
    warning: (msg, duration) => addToast(msg, "warning", duration),
    info: (msg, duration) => addToast(msg, "info", duration),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

/**
 * Accesses the toast helpers provided by the nearest ToastProvider.
 *
 * @returns {{ success: Function, error: Function, warning: Function, info: Function, addToast: Function, removeToast: Function }}
 *   The toast helpers object with methods to create and remove toasts.
 * @throws {Error} If there is no surrounding ToastProvider.
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

/**
 * Renders a fixed-position list of toast notifications when one or more toasts are present.
 *
 * @param {Array<{id: string|number, message: string, type?: string}>} toasts - Array of toast objects to render.
 * @param {(id: string|number) => void} removeToast - Callback invoked with a toast `id` to remove that toast.
 * @returns {JSX.Element|null} The toast container element when `toasts` is non-empty, or `null` when there are no toasts.
 */
function ToastContainer({ toasts, removeToast }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

/**
 * Render a single toast notification with an icon, message text, and a dismiss button.
 *
 * @param {{ id?: string|number, message: string, type?: string }} toast - Toast data; `type` selects visual style (e.g., "success", "error", "warning", "info").
 * @param {() => void} onClose - Callback invoked when the toast's close control is activated.
 * @returns {JSX.Element} The toast item element.
 */
function ToastItem({ toast, onClose }) {
  const styles = {
    success: {
      bg: "bg-green-500/10 border-green-500/30",
      text: "text-green-400",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ),
    },
    error: {
      bg: "bg-red-500/10 border-red-500/30",
      text: "text-red-400",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      ),
    },
    warning: {
      bg: "bg-yellow-500/10 border-yellow-500/30",
      text: "text-yellow-400",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    info: {
      bg: "bg-blue-500/10 border-blue-500/30",
      text: "text-blue-400",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  };

  const style = styles[toast.type] || styles.info;

  return (
    <div
      className={`${style.bg} border rounded-lg p-4 shadow-lg backdrop-blur-sm animate-slide-in flex items-start gap-3`}
      role="alert"
    >
      <span className={style.text}>{style.icon}</span>
      <p className={`${style.text} text-sm flex-1`}>{toast.message}</p>
      <button
        onClick={onClose}
        className="text-gray-400 hover:text-white transition-colors"
        aria-label="Close"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}