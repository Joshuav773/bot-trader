"use client";
import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function OrderFlowPage() {
  const [ticker, setTicker] = useState("");
  const [orderType, setOrderType] = useState<string | null>(null);
  const [hours, setHours] = useState(24);
  const [orders, setOrders] = useState<any[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [impact, setImpact] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadOrders() {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const params = new URLSearchParams({ hours: hours.toString() });
      if (ticker) params.append("ticker", ticker);
      if (orderType) params.append("order_type", orderType);
      const res = await fetch(`${API_URL}/order-flow/large-orders?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setOrders(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadImpact(orderId: number) {
    setError(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/order-flow/price-impact/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setImpact(await res.json());
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar currentPage="/orderflow" />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Large Order Flow Tracker</h1>
          <p className="text-gray-600 mt-1">Track orders ≥ $500k and analyze price impact</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">Ticker (optional)</label>
              <input
                type="text"
                placeholder="AAPL"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Order Type</label>
              <select
                value={orderType || ""}
                onChange={(e) => setOrderType(e.target.value || null)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All Types</option>
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
              <input
                type="number"
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
                min={1}
                max={168}
                className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <button
              onClick={loadOrders}
              disabled={loading}
              className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Large Orders (≥ $500k) - Last {hours}h
            </h2>
            <div className="max-h-[600px] overflow-auto">
              {orders.length === 0 ? (
                <p className="text-gray-500">No large orders found. Streamer must be running to capture real-time trades.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ticker</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Size ($)</th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {orders.map((o) => (
                        <tr
                          key={o.id}
                          onClick={() => {
                            setSelectedOrder(o);
                            loadImpact(o.id);
                          }}
                          className="cursor-pointer hover:bg-gray-50"
                        >
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{o.ticker}</td>
                          <td className={`px-4 py-3 whitespace-nowrap text-sm font-medium ${o.order_type === "buy" ? "text-green-600" : "text-red-600"}`}>
                            {o.order_type.toUpperCase()}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${(o.order_size_usd / 1000).toFixed(0)}k
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${o.price.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                            {new Date(o.timestamp).toLocaleTimeString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Price Impact Analysis</h2>
            {selectedOrder ? (
              <div>
                <div className="mb-4 p-3 bg-gray-50 rounded-md">
                  <p className="font-medium text-gray-900">
                    <span className="font-bold">{selectedOrder.ticker}</span>{" "}
                    <span className={selectedOrder.order_type === "buy" ? "text-green-600" : "text-red-600"}>
                      {selectedOrder.order_type.toUpperCase()}
                    </span>{" "}
                    @ ${selectedOrder.price.toFixed(2)}
                  </p>
                  <p className="text-sm text-gray-600">Order Size: ${(selectedOrder.order_size_usd / 1000).toFixed(0)}k</p>
                </div>
                {impact.length === 0 ? (
                  <p className="text-gray-500">No snapshots yet. Price tracking will capture movements automatically.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Interval</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Change %</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {impact.map((i) => (
                          <tr key={i.order_flow_id + i.interval_minutes}>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{i.interval_minutes}m</td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                              ${i.price.toFixed(2)}
                            </td>
                            <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${i.price_change_pct >= 0 ? "text-green-600" : "text-red-600"}`}>
                              {i.price_change_pct >= 0 ? "+" : ""}{i.price_change_pct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">Select an order to view price impact</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

