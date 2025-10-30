"use client";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function TrainPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState("2023-12-31");
  const [windowSize, setWindowSize] = useState(50);
  const [units, setUnits] = useState(32);
  const [epochs, setEpochs] = useState(5);
  const [modelId, setModelId] = useState<string | null>(null);
  const [trainRes, setTrainRes] = useState<any>(null);
  const [predictRes, setPredictRes] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function train() {
    setLoading(true);
    setError(null);
    setTrainRes(null);
    setPredictRes(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/ml/train/lstm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ticker, start_date: start, end_date: end, window: windowSize, units, epochs }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setTrainRes(data);
      setModelId(data.model_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function predict() {
    setLoading(true);
    setError(null);
    setPredictRes(null);
    try {
      if (!modelId) throw new Error("No model_id. Train first.");
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/ml/predict/lstm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ model_id: modelId, ticker, end_date: end, window: windowSize }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setPredictRes(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>Train LSTM</h1>
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
          Window
          <input type="number" value={windowSize} onChange={(e) => setWindowSize(Number(e.target.value))} />
        </label>
        <label>
          Units
          <input type="number" value={units} onChange={(e) => setUnits(Number(e.target.value))} />
        </label>
        <label>
          Epochs
          <input type="number" value={epochs} onChange={(e) => setEpochs(Number(e.target.value))} />
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={train} disabled={loading}>{loading ? "Training..." : "Train"}</button>
          <button onClick={predict} disabled={!modelId || loading}>{loading ? "Predicting..." : "Predict"}</button>
          <button onClick={() => { localStorage.removeItem("bt_jwt"); window.location.href = "/"; }}>Logout</button>
        </div>
      </div>
      {error && <div style={{ color: "crimson", marginTop: 12 }}>{error}</div>}
      <h3 style={{ marginTop: 16 }}>Training Response</h3>
      <pre style={{ background: "#f5f5f5", padding: 12, overflow: "auto" }}>{trainRes ? JSON.stringify(trainRes, null, 2) : ""}</pre>
      <h3>Prediction Response</h3>
      <pre style={{ background: "#f5f5f5", padding: 12, overflow: "auto" }}>{predictRes ? JSON.stringify(predictRes, null, 2) : ""}</pre>
    </main>
  );
}
