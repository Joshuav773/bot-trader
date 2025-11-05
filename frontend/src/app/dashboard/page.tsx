"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import { getToday, getStartDateForTimeframeSync, fetchDataLimits, getStartDateForTimeframe } from "@/utils/dates";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Dashboard() {
  const [strategy, setStrategy] = useState<"sma" | "bbands" | "enhanced">("sma");
  const [ticker, setTicker] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1d");
  const [start, setStart] = useState(() => getStartDateForTimeframeSync("1d"));
  const [end, setEnd] = useState(getToday());
  const [dataLimits, setDataLimits] = useState<Record<string, number> | null>(null);
  const [cash, setCash] = useState(10000);
  // SMA parameters
  const [fast, setFast] = useState(10);
  const [slow, setSlow] = useState(50);
  // Bollinger Bands parameters
  const [period, setPeriod] = useState(20);
  const [devfactor, setDevfactor] = useState(2.0);
  const [size, setSize] = useState(0.95);
  const [chart, setChart] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [bt, setBt] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function load(customStart?: string, customTimeframe?: string) {
    setLoading(true);
    setError(null);
    setBt(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      const res = await fetch(`${API_URL}/analysis/chart`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          ticker, 
          start_date: customStart || start, 
          end_date: end, 
          timeframe: customTimeframe || timeframe 
        }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Request failed (${res.status})`);
      }
      setChart(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runBacktest() {
    setLoading(true);
    setError(null);
    setBt(null);
    try {
      const token = localStorage.getItem("bt_jwt");
      if (!token) throw new Error("Missing token. Please login.");
      
      let endpoint: string;
      let body: any;
      
      if (strategy === "sma") {
        endpoint = "/backtest/sma-crossover";
        body = {
          ticker,
          start_date: start,
          end_date: end,
          timeframe,
          cash,
          fast_length: fast,
          slow_length: slow,
        };
      } else if (strategy === "bbands") {
        endpoint = "/backtest/bollinger-bands";
        body = {
          ticker,
          start_date: start,
          end_date: end,
          timeframe,
          cash,
          period,
          devfactor,
          size,
        };
      } else {
        // Enhanced strategy
        endpoint = "/backtest/enhanced-sma";
        body = {
          ticker,
          start_date: start,
          end_date: end,
          timeframe,
          cash,
          fast_length: fast,
          slow_length: slow,
          use_advanced_slippage: true,
          slippage_model: "dynamic",
          max_drawdown_pct: 20.0,
          risk_per_trade: 0.02,
        };
      }
      
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || `Backtest failed (${res.status})`);
      }
      setBt(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Fetch data limits on mount
  useEffect(() => {
    fetchDataLimits().then((limits) => {
      setDataLimits(limits);
      // Update start date with fetched limits
      getStartDateForTimeframe(timeframe, limits).then((newStart) => {
        setStart(newStart);
      });
    });
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-adjust start date when timeframe changes
  useEffect(() => {
    if (dataLimits) {
      getStartDateForTimeframe(timeframe, dataLimits).then((newStart) => {
        if (newStart !== start) {
          setStart(newStart);
        }
      });
    } else {
      // Fallback to sync version if limits not loaded yet
      const newStart = getStartDateForTimeframeSync(timeframe);
      if (newStart !== start) {
        setStart(newStart);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeframe, dataLimits]);

  const candleTrace = chart
    ? {
        x: chart.index,
        open: chart.open,
        high: chart.high,
        low: chart.low,
        close: chart.close,
        type: "candlestick" as const,
        name: `${ticker} OHLC`,
        xaxis: "x",
        yaxis: "y",
      }
    : null;

  const smaTrace = chart
    ? {
        x: chart.index,
        y: chart.sma,
        type: "scatter" as const,
        mode: "lines" as const,
        name: "SMA",
        line: { color: "#3b82f6", width: 2 },
        xaxis: "x",
        yaxis: "y",
      }
    : null;

  const emaTrace = chart
    ? {
        x: chart.index,
        y: chart.ema,
        type: "scatter" as const,
        mode: "lines" as const,
        name: "EMA",
        line: { color: "#10b981", width: 2 },
        xaxis: "x",
        yaxis: "y",
      }
    : null;

  const rsiTrace = chart
    ? {
        x: chart.index,
        y: chart.rsi,
        type: "scatter" as const,
        mode: "lines" as const,
        name: "RSI",
        line: { color: "#f59e0b" },
        xaxis: "x",
        yaxis: "y2",
      }
    : null;

  const layout = {
    height: 600,
    margin: { l: 50, r: 20, t: 30, b: 50 },
    grid: { rows: 2, columns: 1, subplots: [["xy"], ["xy2"]] },
    xaxis: { rangeslider: { visible: false } },
    yaxis: { title: "Price ($)" },
    xaxis2: { matches: "x" },
    yaxis2: { title: "RSI", domain: [0, 0.25] },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
  } as any;

  const data = [candleTrace, smaTrace, emaTrace, rsiTrace].filter(Boolean) as any[];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar currentPage="/dashboard" />
      <main className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time analysis and strategy backtesting</p>
        </div>

        {/* Main Dashboard Grid - Chart First, Controls Second */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Chart Section - Takes 2/3 width, prioritized */}
          <div className="lg:col-span-2 bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg border border-gray-200/50 p-6">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Price Chart</h2>
                <p className="text-xs text-gray-500 mt-0.5">{ticker} • {timeframe}</p>
              </div>
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      load();
                    }
                  }}
                  placeholder="Ticker..."
                  className="px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm w-24 font-medium bg-white shadow-sm transition-all"
                />
                <select
                  value={timeframe}
                  onChange={async (e) => {
                    const newTimeframe = e.target.value;
                    setTimeframe(newTimeframe);
                    // Get limits and calculate new start date
                    const limits = dataLimits || await fetchDataLimits();
                    const newStart = await getStartDateForTimeframe(newTimeframe, limits);
                    setStart(newStart);
                    // Reload with new timeframe and adjusted date
                    load(newStart, newTimeframe);
                  }}
                  className="px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm font-medium bg-white shadow-sm transition-all"
                >
                  <option value="1d">1d</option>
                  <option value="4h">4h</option>
                  <option value="1h">1h</option>
                  <option value="30m">30m</option>
                  <option value="15m">15m</option>
                  <option value="5m">5m</option>
                </select>
                <button
                  onClick={() => load()}
                  disabled={loading}
                  className="px-4 py-2 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 shadow-md hover:shadow-lg transition-all font-medium text-sm"
                >
                  {loading ? "..." : "↻"}
                </button>
              </div>
            </div>
            {chart ? (
              <div className="h-[600px] bg-white rounded-lg shadow-inner border border-gray-100 p-2">
                <Plot data={data} layout={{...layout, height: 580, margin: { l: 50, r: 20, t: 30, b: 50 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)"}} style={{ width: "100%", height: "100%" }} />
              </div>
            ) : (
              <div className="h-[600px] flex items-center justify-center text-gray-400 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                <div className="text-center">
                  <div className="text-4xl mb-2">📈</div>
                  <p className="text-sm">Click refresh to load chart</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Backtest Controls - Compact */}
          <div className="bg-gradient-to-br from-white to-gray-50 rounded-xl shadow-lg border border-gray-200/50 p-5">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-1 h-6 bg-gradient-to-b from-primary-500 to-primary-700 rounded-full"></span>
              Quick Backtest
            </h2>
          
          <div className="mb-4">
            <label className="block text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Strategy</label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value as "sma" | "bbands" | "enhanced")}
                    className="w-full px-3 py-2.5 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm font-medium text-sm transition-all"
                  >
                    <option value="sma">SMA Crossover</option>
                    <option value="bbands">Bollinger Bands</option>
                    <option value="enhanced">Enhanced SMA (Risk-Managed)</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                    {strategy === "sma" 
                      ? "Trend following: Buy when fast MA crosses above slow MA"
                      : strategy === "bbands"
                      ? "Mean reversion: Buy at lower band, sell at upper band"
                      : "Elite strategy: Risk-managed with drawdown protection, ATR stops, dynamic sizing"}
                  </p>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Ticker</label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm font-medium transition-all"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Start Date</label>
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">End Date</label>
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Timeframe</label>
              <select
                value={timeframe}
                onChange={async (e) => {
                  const newTimeframe = e.target.value;
                  setTimeframe(newTimeframe);
                  // Get limits and calculate new start date
                  const limits = dataLimits || await fetchDataLimits();
                  const newStart = await getStartDateForTimeframe(newTimeframe, limits);
                  setStart(newStart);
                  // Reload with new timeframe and adjusted date
                  load(newStart, newTimeframe);
                }}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm font-medium transition-all"
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
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">Initial Cash</label>
              <input
                type="number"
                value={cash}
                onChange={(e) => setCash(Number(e.target.value))}
                className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
              />
            </div>
            {(strategy === "sma" || strategy === "enhanced") ? (
              <>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Fast MA</label>
                  <input
                    type="number"
                    value={fast}
                    onChange={(e) => setFast(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Slow MA</label>
                  <input
                    type="number"
                    value={slow}
                    onChange={(e) => setSlow(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Period</label>
                  <input
                    type="number"
                    value={period}
                    onChange={(e) => setPeriod(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Dev Factor</label>
                  <input
                    type="number"
                    step="0.1"
                    value={devfactor}
                    onChange={(e) => setDevfactor(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-600 mb-1.5">Position Size</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    max="1"
                    value={size}
                    onChange={(e) => setSize(Number(e.target.value))}
                    className="w-full px-3 py-2 border-2 border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white shadow-sm text-sm transition-all"
                  />
                </div>
              </>
            )}
          </div>
          
          <button
            onClick={() => runBacktest()}
            disabled={loading}
            className="w-full px-4 py-3 bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 shadow-md hover:shadow-lg transition-all font-semibold text-sm"
          >
            {loading ? "Running..." : "▶ Run Backtest"}
          </button>

          {/* Backtest Results - Compact & Styled */}
          {bt && (
            <div className="mt-4 pt-4 border-t-2 border-gray-100">
              <div className="bg-gradient-to-r from-gray-50 to-white rounded-lg p-3 border border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">P&L</span>
                  <span className={`text-lg font-bold ${bt.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {bt.pnl >= 0 ? '+' : ''}${bt.pnl?.toFixed(2)} ({bt.pnl_percentage?.toFixed(2)}%)
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-gray-200">
                  <div>
                    <div className="text-xs text-gray-500 mb-0.5">Start</div>
                    <div className="text-sm font-semibold text-gray-700">${bt.start_portfolio_value?.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-0.5">End</div>
                    <div className="text-sm font-semibold text-gray-700">${bt.end_portfolio_value?.toFixed(2)}</div>
                  </div>
                </div>
                {bt.warnings && bt.warnings.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-yellow-200 bg-yellow-50 rounded-md p-2">
                    <div className="text-xs text-yellow-700 font-medium">
                      ⚠️ {bt.warnings[0]}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

        {/* Expanded Backtest Results - Collapsible */}
        {bt && (
          <details className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
            <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900 mb-3">
              Detailed Results
            </summary>
            
            {bt.warnings && bt.warnings.length > 0 && (
              <div className="mb-3 space-y-2">
                {bt.warnings.map((warning: string, idx: number) => (
                  <div key={idx} className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-3 py-2 rounded-md text-xs">
                    ⚠️ {warning}
                  </div>
                ))}
              </div>
            )}
            
            {bt.data_info && (
              <div className="mb-3 bg-blue-50 border border-blue-200 rounded-md p-2 text-xs text-blue-800">
                <p><strong>Data Range:</strong> {bt.data_info.start} to {bt.data_info.end}</p>
                <p><strong>Data Points:</strong> {bt.data_info.bars_count} bars</p>
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
              <div>
                <span className="text-gray-600">Start Value:</span>
                <span className="block font-medium">${bt.start_portfolio_value?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">End Value:</span>
                <span className="block font-medium">${bt.end_portfolio_value?.toFixed(2)}</span>
              </div>
              <div>
                <span className="text-gray-600">P&L:</span>
                <span className={`block font-bold ${bt.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ${bt.pnl?.toFixed(2)} ({bt.pnl_percentage?.toFixed(2)}%)
                </span>
              </div>
            </div>
            
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">Show raw JSON</summary>
              <div className="bg-gray-50 rounded-md p-3 mt-2">
                <pre className="text-xs text-gray-700 overflow-auto">{JSON.stringify(bt, null, 2)}</pre>
              </div>
            </details>
          </details>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4 text-sm">
            {error}
          </div>
        )}
      </main>
    </div>
  );
}

