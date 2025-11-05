"use client";
import { useState } from "react";
import Navbar from "@/components/Navbar";
import { getDate2YearsAgo, getToday } from "@/utils/dates";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function ConfluencePage() {
  const [ticker, setTicker] = useState("AAPL");
  const [start, setStart] = useState(getDate2YearsAgo());
  const [end, setEnd] = useState(getToday());
  const [timeframe, setTimeframe] = useState("1d");
  const [fastMa, setFastMa] = useState(10);
  const [slowMa, setSlowMa] = useState(50);
  const [rsiOversold, setRsiOversold] = useState(30);
  const [rsiOverbought, setRsiOverbought] = useState(70);
  const [minConfirmations, setMinConfirmations] = useState(3);
  const [requireCandlestick, setRequireCandlestick] = useState(true);
  const [requireNews, setRequireNews] = useState(true);
  const [newsSentimentThreshold, setNewsSentimentThreshold] = useState(0.1);
  const [newsDaysBack, setNewsDaysBack] = useState(7);
  const [result, setResult] = useState<any>(null);
  const [optimizeResult, setOptimizeResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);

  async function runBacktest() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/confluence/backtest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
          body: JSON.stringify({
            ticker,
            start_date: start,
            end_date: end,
            timeframe,
            fast_ma: fastMa,
            slow_ma: slowMa,
            rsi_oversold: rsiOversold,
            rsi_overbought: rsiOverbought,
            require_candlestick: requireCandlestick,
            require_news: requireNews,
            news_sentiment_threshold: newsSentimentThreshold,
            news_days_back: newsDaysBack,
            min_confirmations: minConfirmations,
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

  async function optimize() {
    setOptimizing(true);
    setError(null);
    setOptimizeResult(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/confluence/optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticker,
          start_date: start,
          end_date: end,
          timeframe,
          fast_ma_range: [5, 10, 15, 20],
          slow_ma_range: [30, 50, 100],
          rsi_oversold_range: [25, 30, 35],
          rsi_overbought_range: [65, 70, 75],
          min_confirmations_range: [2, 3, 4],
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setOptimizeResult(data);
      // Auto-fill best parameters
      if (data.best_parameters) {
        setFastMa(data.best_parameters.fast_ma);
        setSlowMa(data.best_parameters.slow_ma);
        setRsiOversold(data.best_parameters.rsi_oversold);
        setRsiOverbought(data.best_parameters.rsi_overbought);
        setMinConfirmations(data.best_parameters.min_confirmations);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setOptimizing(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar currentPage="/confluence" />
      <main className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">Confluence Strategy</h1>
          <p className="text-gray-500 text-sm mt-1">
            Multi-confirmation strategy: trend + momentum + volume + candlestick + news sentiment
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg border border-gray-200/50 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-1 h-6 bg-gradient-to-b from-primary-500 to-primary-700 rounded-full"></span>
              Parameters
            </h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Ticker</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm font-medium transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Start Date</label>
                  <input
                    type="date"
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">End Date</label>
                  <input
                    type="date"
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Timeframe</label>
                  <select
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  >
                    <option value="1d">1 Day</option>
                    <option value="4h">4 Hour</option>
                    <option value="1h">1 Hour</option>
                    <option value="30m">30 Minute</option>
                    <option value="15m">15 Minute</option>
                    <option value="5m">5 Minute</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Fast MA</label>
                  <input
                    type="number"
                    value={fastMa}
                    onChange={(e) => setFastMa(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Slow MA</label>
                  <input
                    type="number"
                    value={slowMa}
                    onChange={(e) => setSlowMa(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">RSI Oversold</label>
                  <input
                    type="number"
                    step="0.1"
                    value={rsiOversold}
                    onChange={(e) => setRsiOversold(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">RSI Overbought</label>
                  <input
                    type="number"
                    step="0.1"
                    value={rsiOverbought}
                    onChange={(e) => setRsiOverbought(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Min Confirmations</label>
                  <input
                    type="number"
                    value={minConfirmations}
                    onChange={(e) => setMinConfirmations(Number(e.target.value))}
                    min={1}
                    max={5}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={requireCandlestick}
                    onChange={(e) => setRequireCandlestick(e.target.checked)}
                    className="mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded accent-primary-600"
                  />
                  <span className="text-sm text-gray-700">Require Candlestick Pattern</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={requireNews}
                    onChange={(e) => setRequireNews(e.target.checked)}
                    className="mr-2 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded accent-primary-600"
                  />
                  <span className="text-sm text-gray-700">Require News Sentiment</span>
                </label>
              </div>

              {requireNews && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">News Sentiment Threshold</label>
                    <input
                      type="number"
                      step="0.1"
                      value={newsSentimentThreshold}
                      onChange={(e) => setNewsSentimentThreshold(Number(e.target.value))}
                      className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">News Days Back</label>
                    <input
                      type="number"
                      value={newsDaysBack}
                      onChange={(e) => setNewsDaysBack(Number(e.target.value))}
                      min={1}
                      max={30}
                      className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                    />
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                    <button
                      onClick={() => runBacktest()}
                      disabled={loading || optimizing}
                      className="flex-1 px-4 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 shadow-md hover:shadow-lg transition-all font-semibold text-sm"
                    >
                      {loading ? "Running..." : "▶ Run Backtest"}
                    </button>
                    <button
                      onClick={() => optimize()}
                      disabled={loading || optimizing}
                      className="flex-1 px-4 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-lg hover:from-gray-700 hover:to-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 shadow-md hover:shadow-lg transition-all font-semibold text-sm"
                    >
                      {optimizing ? "Optimizing..." : "⚙ Optimize"}
                    </button>
                  </div>
            </div>
          </div>

          <div className="space-y-6">
                {error && (
                  <div className="bg-red-50 border-2 border-red-200 text-red-700 px-4 py-3 rounded-lg shadow-sm">
                    {error}
                  </div>
                )}

                {result && (
                  <div className="bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg border border-gray-200/50 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <span className="w-1 h-6 bg-gradient-to-b from-primary-500 to-primary-700 rounded-full"></span>
                      Backtest Result
                    </h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Start Value:</span>
                    <span className="font-medium">${result.start_portfolio_value?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">End Value:</span>
                    <span className="font-medium">${result.end_portfolio_value?.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">P&L:</span>
                    <span className={`font-bold ${result.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${result.pnl?.toFixed(2)} ({result.pnl_percentage?.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>
            )}

                {optimizeResult && (
                  <div className="bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg border border-gray-200/50 p-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                      <span className="w-1 h-6 bg-gradient-to-b from-primary-500 to-primary-700 rounded-full"></span>
                      Optimization Result
                    </h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">Best PnL</p>
                    <p className="text-2xl font-bold text-green-600">
                      {optimizeResult.best_result?.pnl_percentage}%
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-2">Best Parameters</p>
                    <div className="bg-gray-50 rounded-md p-3">
                      <pre className="text-xs text-gray-700 overflow-auto">
                        {JSON.stringify(optimizeResult.best_parameters, null, 2)}
                      </pre>
                    </div>
                  </div>
                  {optimizeResult.top_10_results && (
                    <div>
                      <p className="text-sm text-gray-600 mb-2">Top 10 Results</p>
                      <div className="bg-gray-50 rounded-md p-3 max-h-64 overflow-auto">
                        <pre className="text-xs text-gray-700">
                          {JSON.stringify(optimizeResult.top_10_results, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

