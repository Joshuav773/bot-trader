"use client";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Page() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function login(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || "Login failed");
      }
      const data = await res.json();
      localStorage.setItem("bt_jwt", data.access_token);
      window.location.href = "/dashboard";
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <main style={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <form onSubmit={login} style={{ width: 320, display: "grid", gap: 12 }}>
        <h1>Bot Trader Login</h1>
        <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button type="submit">Login</button>
        {error && <div style={{ color: "crimson" }}>{error}</div>}
        <p style={{ fontSize: 12, opacity: 0.7 }}>API: {API_URL}</p>
      </form>
    </main>
  );
}
