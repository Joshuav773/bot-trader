"use client";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function BacktestPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState("2023-12-31");
  const [cash, setCash] = useState(10000);
  const [fast, setFast] = useState(10);
  const [slow, setSlow] = useState(50);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runBacktest() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/backtest/sma-crossover`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticker,
          start_date: start,
          end_date: end,
          cash,
          fast_length: fast,
          slow_length: slow,
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>Backtest: SMA Crossover</h1>
      <div style={{ display: "grid", gap: 8, maxWidth: 640 }}>
        <label>
          Ticker
          <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
        </label>
        <label>
          Start Date
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          End Date
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label>
          Cash
          <input type="number" value={cash} onChange={(e) => setCash(Number(e.target.value))} />
        </label>
        <label>
          Fast Length
          <input type="number" value={fast} onChange={(e) => setFast(Number(e.target.value))} />
        </label>
        <label>
          Slow Length
          <input type="number" value={slow} onChange={(e) => setSlow(Number(e.target.value))} />
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={runBacktest} disabled={loading}>{loading ? "Running..." : "Run Backtest"}</button>
          <button onClick={() => { localStorage.removeItem("bt_jwt"); window.location.href = "/"; }}>Logout</button>
        </div>
      </div>
      {error && <div style={{ color: "crimson", marginTop: 12 }}>{error}</div>}
      <pre style={{ marginTop: 16, background: "#f5f5f5", padding: 12, overflow: "auto" }}>
        {result ? JSON.stringify(result, null, 2) : ""}
      </pre>
    </main>
  );
}
