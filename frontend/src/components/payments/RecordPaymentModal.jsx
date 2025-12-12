/**
 * RecordPaymentModal - Record payment or refund for an order
 *
 * Features:
 * - Order search/selection
 * - Payment amount input
 * - Payment method selection
 * - Transaction ID and check number
 * - Shows order balance due
 */
import { useState, useEffect } from "react";
import { API_URL } from "../../config/api";
import { useToast } from "../Toast";

const paymentMethods = [
  { value: "cash", label: "Cash" },
  { value: "check", label: "Check" },
  { value: "credit_card", label: "Credit Card" },
  { value: "paypal", label: "PayPal" },
  { value: "stripe", label: "Stripe" },
  { value: "venmo", label: "Venmo" },
  { value: "zelle", label: "Zelle" },
  { value: "wire", label: "Wire Transfer" },
  { value: "other", label: "Other" },
];

export default function RecordPaymentModal({
  isRefund = false,
  orderId = null,  // Pre-selected order (from Order Detail page)
  onClose,
  onSuccess,
}) {
  const toast = useToast();
  const token = localStorage.getItem("adminToken");

  const [loading, setLoading] = useState(false);
  const [orders, setOrders] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [paymentSummary, setPaymentSummary] = useState(null);

  const [form, setForm] = useState({
    sales_order_id: orderId || "",
    amount: "",
    payment_method: "credit_card",
    transaction_id: "",
    check_number: "",
    notes: "",
    payment_date: new Date().toISOString().split("T")[0],
  });

  // Fetch orders for selection
  useEffect(() => {
    fetchOrders();
  }, []);

  // If orderId is provided, fetch that order
  useEffect(() => {
    if (orderId) {
      fetchOrderDetails(orderId);
    }
  }, [orderId]);

  // Fetch payment summary when order is selected
  useEffect(() => {
    if (form.sales_order_id) {
      fetchPaymentSummary(form.sales_order_id);
    } else {
      setPaymentSummary(null);
    }
  }, [form.sales_order_id]);

  const fetchOrders = async () => {
    try {
      // Fetch orders that might need payment (not cancelled, not fully paid for payments)
      const res = await fetch(`${API_URL}/api/v1/sales-orders?page_size=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setOrders(data.items || data);
      }
    } catch (err) {
      console.error("Failed to fetch orders:", err);
    }
  };

  const fetchOrderDetails = async (id) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/sales-orders/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const order = await res.json();
        setSelectedOrder(order);
        setForm({ ...form, sales_order_id: id });
      }
    } catch (err) {
      console.error("Failed to fetch order:", err);
    }
  };

  const fetchPaymentSummary = async (orderId) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/payments/order/${orderId}/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setPaymentSummary(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch payment summary:", err);
    }
  };

  const handleOrderSelect = (order) => {
    setSelectedOrder(order);
    setForm({ ...form, sales_order_id: order.id });
    setSearchQuery("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.sales_order_id) {
      toast.warning("Please select an order");
      return;
    }

    if (!form.amount || parseFloat(form.amount) <= 0) {
      toast.warning("Please enter a valid amount");
      return;
    }

    setLoading(true);
    try {
      const endpoint = isRefund
        ? `${API_URL}/api/v1/payments/refund`
        : `${API_URL}/api/v1/payments`;

      const body = {
        sales_order_id: parseInt(form.sales_order_id),
        amount: parseFloat(form.amount),
        payment_method: form.payment_method,
        payment_date: form.payment_date ? new Date(form.payment_date).toISOString() : null,
        transaction_id: form.transaction_id || null,
        check_number: form.payment_method === "check" ? form.check_number : null,
        notes: form.notes || null,
      };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        onSuccess();
      } else {
        const err = await res.json();
        toast.error(err.detail || `Failed to record ${isRefund ? "refund" : "payment"}`);
      }
    } catch (err) {
      toast.error(`Failed to record ${isRefund ? "refund" : "payment"}`);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return parseFloat(amount || 0).toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
    });
  };

  // Filter orders based on search
  const filteredOrders = orders.filter((order) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      order.order_number?.toLowerCase().includes(query) ||
      order.product_name?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black/70" onClick={onClose} />
        <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-xl max-w-lg w-full mx-auto p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold text-white">
              {isRefund ? "Record Refund" : "Record Payment"}
            </h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Order Selection */}
            {!orderId && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Order *</label>
                {selectedOrder ? (
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 flex justify-between items-center">
                    <div>
                      <div className="text-white font-medium">{selectedOrder.order_number}</div>
                      <div className="text-sm text-gray-400">{selectedOrder.product_name}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedOrder(null);
                        setForm({ ...form, sales_order_id: "" });
                      }}
                      className="text-gray-400 hover:text-white"
                    >
                      Change
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search by order number..."
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    />
                    {searchQuery && filteredOrders.length > 0 && (
                      <div className="absolute z-10 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-48 overflow-auto">
                        {filteredOrders.slice(0, 10).map((order) => (
                          <div
                            key={order.id}
                            onClick={() => handleOrderSelect(order)}
                            className="px-3 py-2 hover:bg-gray-700 cursor-pointer"
                          >
                            <div className="text-white">{order.order_number}</div>
                            <div className="text-xs text-gray-400 flex justify-between">
                              <span>{order.product_name}</span>
                              <span className={
                                order.payment_status === "paid" ? "text-green-400" :
                                order.payment_status === "partial" ? "text-yellow-400" :
                                "text-gray-400"
                              }>
                                {formatCurrency(order.grand_total)} - {order.payment_status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Payment Summary */}
            {paymentSummary && (
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div className="text-gray-400">Order Total:</div>
                  <div className="text-white text-right">{formatCurrency(paymentSummary.order_total)}</div>
                  <div className="text-gray-400">Already Paid:</div>
                  <div className="text-green-400 text-right">{formatCurrency(paymentSummary.total_paid)}</div>
                  {paymentSummary.total_refunded > 0 && (
                    <>
                      <div className="text-gray-400">Refunded:</div>
                      <div className="text-red-400 text-right">{formatCurrency(paymentSummary.total_refunded)}</div>
                    </>
                  )}
                  <div className="text-gray-400 font-medium border-t border-gray-700 pt-2">Balance Due:</div>
                  <div className={`text-right font-medium border-t border-gray-700 pt-2 ${
                    paymentSummary.balance_due > 0 ? "text-yellow-400" : "text-green-400"
                  }`}>
                    {formatCurrency(paymentSummary.balance_due)}
                  </div>
                </div>
              </div>
            )}

            {/* Amount */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                {isRefund ? "Refund Amount *" : "Payment Amount *"}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                <input
                  type="number"
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  placeholder="0.00"
                  min="0.01"
                  step="0.01"
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-2 text-white"
                />
              </div>
              {paymentSummary && !isRefund && paymentSummary.balance_due > 0 && (
                <button
                  type="button"
                  onClick={() => setForm({ ...form, amount: paymentSummary.balance_due.toString() })}
                  className="text-xs text-blue-400 hover:text-blue-300 mt-1"
                >
                  Pay full balance ({formatCurrency(paymentSummary.balance_due)})
                </button>
              )}
            </div>

            {/* Payment Method */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Payment Method *</label>
              <select
                value={form.payment_method}
                onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              >
                {paymentMethods.map((method) => (
                  <option key={method.value} value={method.value}>
                    {method.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Check Number (for check payments) */}
            {form.payment_method === "check" && (
              <div>
                <label className="block text-sm text-gray-400 mb-1">Check Number</label>
                <input
                  type="text"
                  value={form.check_number}
                  onChange={(e) => setForm({ ...form, check_number: e.target.value })}
                  placeholder="1234"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
            )}

            {/* Transaction ID */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Transaction ID (optional)</label>
              <input
                type="text"
                value={form.transaction_id}
                onChange={(e) => setForm({ ...form, transaction_id: e.target.value })}
                placeholder="Stripe, PayPal, or other reference"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            {/* Payment Date */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Payment Date</label>
              <input
                type="date"
                value={form.payment_date}
                onChange={(e) => setForm({ ...form, payment_date: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm text-gray-400 mb-1">Notes</label>
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
                placeholder={isRefund ? "Reason for refund..." : "Additional notes..."}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !form.sales_order_id || !form.amount}
                className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50 ${
                  isRefund
                    ? "bg-red-600 hover:bg-red-700 text-white"
                    : "bg-green-600 hover:bg-green-700 text-white"
                }`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Recording...
                  </>
                ) : isRefund ? (
                  "Record Refund"
                ) : (
                  "Record Payment"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
