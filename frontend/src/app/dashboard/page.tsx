"use client";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Dashboard() {
  const [ticker, setTicker] = useState("AAPL");
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState("2023-12-31");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    setResult(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/analysis/signals`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ticker, start_date: start, end_date: end }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Dashboard</h1>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input value={ticker} onChange={(e) => setTicker(e.target.value)} />
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        <button onClick={load}>Refresh</button>
        <button onClick={() => { localStorage.removeItem("bt_jwt"); window.location.href = "/"; }}>Logout</button>
      </div>
      {error && <div style={{ color: "crimson", marginTop: 12 }}>{error}</div>}
      <pre style={{ marginTop: 16, background: "#f5f5f5", padding: 12, overflow: "auto" }}>
        {JSON.stringify(result, null, 2)}
      </pre>
    </main>
  );
}
