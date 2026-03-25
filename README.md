# 🤖 Multi-Agent Trading System

**Repository for specialized AI trading agents with distinct personas and strategies**

---

## 📁 Repository Structure

```
/workspace
├── agents/                          # Agent persona definitions
│   └── quant-oracle/               # Options trading specialist
│       ├── options-trader-agent.json    # Core persona definition
│       ├── ACCOUNT_LEDGER.md           # Live trade tracking
│       ├── PROTOCOL.md                 # Operational protocol
│       ├── README.md                   # Agent overview
│       └── context/                    # Analysis reports & guides
│           ├── OXY_MARCH_20_TRADE_RECOMMENDATIONS.md
│           ├── OXY_PERFORMANCE_UPDATE_MARCH_17.md
│           ├── TDA_QUICK_START_GUIDE.md
│           └── data_latency_solutions.md
│
├── .cursorrules                    # Global agent orchestration rules
└── README.md                       # This file
```

---

## 🎯 Active Agents

### **The Quant Oracle** (Lead Options Specialist)
- **Persona:** `agents/quant-oracle/options-trader-agent.json`
- **Focus:** Black-Scholes-Merton options analysis, Greek-based risk management
- **Performance:** +13.4% ($500 → $567) over 2 weeks
- **Specialties:**
  - Gamma scalping (2-6 hour holds)
  - Directional momentum (1-3 day holds)
  - Credit spreads (hold to expiration)
  - High-conviction trade identification (85%+ scoring)

**Access:** Invoke with "You are Options Analyst (The Quant Oracle)..."

---

## 📋 Usage Guidelines

### **Working with The Quant Oracle:**

**Optimal query format:**
```
"[Day] [Time] - [Ticker] at $[Price] - Account $[Amount] - [Request]"
```

**Example:**
```
"Wednesday 9:50 AM - SPY at $658.50 - Account $567 - Scan for high-conviction play"
```

**The Oracle provides:**
- Real-time price refresh (15-min delay acknowledged)
- Greek calculations and probability analysis
- Specific strikes, entry prices, targets, stops
- Position sizing (typically 80-90% allocation)
- Chart pattern analysis (1/5/15-min candles based on strategy)
- Account ledger updates

---

## 🎯 Agent Philosophy

**From `.cursorrules`:**
- All agents prioritize S&P 500 index tracking
- Institutional orders >$500k alignment required
- Each agent has distinct "Thought Architecture"

**The Quant Oracle specifically:**
- Treats options as physics problems (Black-Scholes)
- Greeks > directional bias
- Identifies "mispriced risk" as edge
- Uses LaTeX for pricing: $C = S_0N(d_1) - Ke^{-rT}N(d_2)$

---

## 📊 Performance Tracking

**Maintained in:** `agents/quant-oracle/ACCOUNT_LEDGER.md`

**Current status:**
- Starting: $500
- Current: $567
- Return: +13.4%
- Trades: 6 (4W-2L)
- Win rate: 66.7%

---

## 🔧 Future Enhancements

**Planned agent expansions:**
- **Macro Strategist** - Long-term positioning, sentiment analysis
- **Technical Analyst** - Pure chart-based entries
- **Volatility Trader** - IV crush and expansion specialist
- **Earnings Specialist** - Pre/post-earnings strategies

**Each will have:**
- Dedicated folder in `/agents/`
- Persona JSON definition
- Context documentation
- Protocol specifications

---

## 📝 Contributing

**When adding new agents:**
1. Create folder: `agents/[agent-name]/`
2. Define persona: `[agent-name]-agent.json`
3. Add protocol: `PROTOCOL.md`
4. Document context: `/context/` subfolder
5. Update this README

---

## 🎯 Quick Start

**To invoke The Quant Oracle:**
1. Provide: Day, time, ticker price, account value
2. Request: Scan, position check, or specific analysis
3. Receive: Conviction-scored setups with exact execution details
4. Execute on thinkorswim with real-time verification
5. Confirm trade for ledger update

**The Oracle provides strategy. You provide execution.**

---

**Repository:** Multi-agent trading system  
**Primary Agent:** The Quant Oracle (Options specialist)  
**Focus:** Quantitative options analysis with 5-figure monthly profit target
