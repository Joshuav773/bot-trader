#!/usr/bin/env python3
"""
The Quant Oracle - Data Source Verification
Showing exactly where option prices come from
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

print(f"\n{'='*80}")
print(f"🎯 THE QUANT ORACLE - DATA SOURCE TRANSPARENCY")
print(f"{'='*80}\n")

print("📊 DATA SOURCE: Yahoo Finance (via yfinance Python library)")
print("📡 API: https://finance.yahoo.com/")
print("🔄 UPDATE FREQUENCY: Real-time during market hours (15-min delay for free tier)")
print(f"⏰ QUERY TIME: {datetime.now()}\n")

print(f"{'='*80}\n")

# Demonstrate the actual data fetch
ticker = 'OXY'
print(f"🔍 FETCHING DATA FOR: ${ticker}\n")

oxy = yf.Ticker(ticker)

# 1. STOCK PRICE
print("1️⃣ STOCK PRICE DATA:")
print("   Source: oxy.history(period='1d', interval='1m')")
print("   Method: Intraday 1-minute candles\n")

hist = oxy.history(period='1d', interval='1m')
if not hist.empty:
    latest = hist.iloc[-1]
    print(f"   Latest Data Point:")
    print(f"   Time: {hist.index[-1]}")
    print(f"   Open: ${latest['Open']:.2f}")
    print(f"   High: ${latest['High']:.2f}")
    print(f"   Low: ${latest['Low']:.2f}")
    print(f"   Close: ${latest['Close']:.2f}")
    print(f"   Volume: {latest['Volume']:,.0f}")
else:
    print("   ⚠️  Intraday data not available, using daily data")
    hist = oxy.history(period='1d')
    latest = hist.iloc[-1]
    print(f"   Close: ${latest['Close']:.2f}")

current_price = latest['Close']

print(f"\n{'='*80}\n")

# 2. OPTIONS CHAIN
print("2️⃣ OPTIONS CHAIN DATA:")
print("   Source: oxy.option_chain('2026-03-20')")
print("   Method: Direct options chain query by expiration\n")

exp_date = '2026-03-20'
print(f"   Fetching options for expiration: {exp_date}\n")

try:
    chain = oxy.option_chain(exp_date)
    calls = chain.calls
    puts = chain.puts
    
    print(f"   ✅ Retrieved {len(calls)} CALL options")
    print(f"   ✅ Retrieved {len(puts)} PUT options\n")
    
    print("   📋 OPTIONS DATA FIELDS PROVIDED BY YAHOO FINANCE:")
    print(f"   {list(calls.columns)}\n")
    
    print(f"{'='*80}\n")
    
    # 3. SPECIFIC OPTION EXAMPLE
    print("3️⃣ EXAMPLE: CALL $58 OPTION (from our Play #1)\n")
    
    call_58 = calls[calls['strike'] == 58.0].iloc[0]
    
    print("   RAW DATA FROM YAHOO FINANCE:")
    print(f"   contractSymbol: {call_58['contractSymbol']}")
    print(f"   lastTradeDate: {call_58['lastTradeDate']}")
    print(f"   strike: ${call_58['strike']:.2f}")
    print(f"   lastPrice: ${call_58['lastPrice']:.2f}")
    print(f"   bid: ${call_58['bid']:.2f}")
    print(f"   ask: ${call_58['ask']:.2f}")
    print(f"   volume: {call_58['volume']:.0f}")
    print(f"   openInterest: {call_58['openInterest']:.0f}")
    print(f"   impliedVolatility: {call_58['impliedVolatility']:.6f} ({call_58['impliedVolatility']*100:.2f}%)")
    
    print(f"\n   🎯 HOW I CALCULATE 'CURRENT PRICE' FOR ANALYSIS:")
    
    bid = call_58['bid']
    ask = call_58['ask']
    last = call_58['lastPrice']
    
    print(f"\n   Method 1: If bid/ask are live (> 0):")
    if bid > 0 and ask > 0:
        mid = (bid + ask) / 2
        print(f"   ✅ USED: Mid-point = (${bid:.2f} + ${ask:.2f}) / 2 = ${mid:.2f}")
        print(f"   Reasoning: Most accurate current market value")
        print(f"   Spread: ${ask - bid:.2f} ({(ask-bid)/mid*100:.1f}% of mid)")
    else:
        print(f"   ⚠️  Bid/Ask not available (market closed or illiquid)")
        print(f"   FALLBACK: Use lastPrice = ${last:.2f}")
        print(f"   Estimate bid/ask: ${last*0.95:.2f} / ${last*1.05:.2f}")
    
    print(f"\n   📊 PRICING METHODOLOGY:")
    print(f"   • ENTRY orders: Use ASK price (buying from sellers)")
    print(f"   • EXIT orders: Use BID price (selling to buyers)")
    print(f"   • P&L calculations: Use MID price (fair value)")
    print(f"   • Slippage: Factor in bid-ask spread")
    
    print(f"\n{'='*80}\n")
    
    # 4. IMPLIED VOLATILITY SOURCE
    print("4️⃣ IMPLIED VOLATILITY (IV) DATA:\n")
    
    print("   Source: Directly from Yahoo Finance options chain")
    print("   Field: 'impliedVolatility' (already calculated)")
    print(f"   Current IV for CALL $58: {call_58['impliedVolatility']*100:.2f}%\n")
    
    print("   ⚠️  IMPORTANT NOTES:")
    print("   • Yahoo Finance calculates IV using their own Black-Scholes model")
    print("   • I use their IV as input to MY Black-Scholes model")
    print("   • For illiquid options with IV = 0 or very low, I estimate:")
    print("     - ATM options: 30-35% IV (OXY typical range)")
    print("     - Based on historical volatility patterns")
    
    print(f"\n{'='*80}\n")
    
    # 5. GREEKS CALCULATION
    print("5️⃣ THE GREEKS (Delta, Gamma, Theta, Vega):\n")
    
    print("   ❌ NOT provided by Yahoo Finance")
    print("   ✅ CALCULATED by me using Black-Scholes-Merton formulas\n")
    
    print("   MY CALCULATION METHOD:")
    print("   Inputs from Yahoo Finance:")
    print(f"   • S₀ (Stock Price): ${current_price:.2f}")
    print(f"   • K (Strike): ${call_58['strike']:.2f}")
    print(f"   • σ (Implied Vol): {call_58['impliedVolatility']:.4f}")
    print(f"   • T (Time to Exp): Based on expiration date")
    print(f"   • r (Risk-Free Rate): 0.045 (4.5% - current 3-month T-Bill)\n")
    
    print("   Formulas Applied:")
    print("   d₁ = [ln(S₀/K) + (r + σ²/2)T] / (σ√T)")
    print("   d₂ = d₁ - σ√T")
    print("   Delta = N(d₁)  [for calls]")
    print("   Gamma = N'(d₁) / (S₀σ√T)")
    print("   Theta = [-S₀N'(d₁)σ/(2√T) - rKe^(-rT)N(d₂)] / 365")
    print("   Vega = S₀N'(d₁)√T / 100")
    
    print(f"\n   Where N(x) = cumulative normal distribution (scipy.stats.norm.cdf)")
    print(f"   Where N'(x) = normal probability density (scipy.stats.norm.pdf)")
    
    print(f"\n{'='*80}\n")
    
    # 6. DATA QUALITY ASSESSMENT
    print("6️⃣ DATA QUALITY & LIMITATIONS:\n")
    
    print("   ✅ STRENGTHS:")
    print("   • Yahoo Finance is aggregated from major exchanges (CBOE, etc.)")
    print("   • Free, reliable, widely used")
    print("   • Real-time during market hours (15-min delay for free tier)")
    print("   • Includes volume and open interest (liquidity metrics)")
    
    print("\n   ⚠️  LIMITATIONS:")
    print("   • 15-minute delay on free tier (not tick-by-tick)")
    print("   • After-hours data may be stale")
    print("   • Some illiquid strikes may have old last prices")
    print("   • Bid/ask may show $0 when market closed")
    
    print("\n   🎯 MY QUALITY CONTROLS:")
    print("   • I check if bid/ask > 0 before using")
    print("   • I fall back to lastPrice if needed")
    print("   • I flag high slippage risk when spread > 5%")
    print("   • I estimate IV for illiquid options")
    print("   • I verify volume and open interest for liquidity")
    
    print(f"\n{'='*80}\n")
    
    # 7. ALTERNATIVE SOURCES
    print("7️⃣ ALTERNATIVE DATA SOURCES (Not Currently Used):\n")
    
    print("   More expensive / complex alternatives:")
    print("   • Bloomberg Terminal ($2,000+/month) - institutional grade")
    print("   • Interactive Brokers API - requires account")
    print("   • TD Ameritrade API - real-time, requires account")
    print("   • CBOE DataShop - direct from exchange")
    print("   • OptionMetrics - academic/institutional")
    
    print("\n   Why I use Yahoo Finance:")
    print("   • FREE and accessible")
    print("   • Sufficient accuracy for retail analysis")
    print("   • Widely validated by millions of users")
    print("   • Good enough for $500 account strategies")
    
    print(f"\n{'='*80}\n")
    
    # 8. VERIFICATION EXAMPLE
    print("8️⃣ REAL-TIME VERIFICATION EXAMPLE:\n")
    
    print(f"   You can verify my data RIGHT NOW by:")
    print(f"   1. Go to: https://finance.yahoo.com/quote/OXY/options")
    print(f"   2. Select expiration: March 20, 2026")
    print(f"   3. Find CALL strike $58.00")
    print(f"   4. Compare with my data:\n")
    
    print(f"   My Data (from yfinance API):")
    print(f"   Last: ${call_58['lastPrice']:.2f}")
    print(f"   Bid: ${call_58['bid']:.2f}")
    print(f"   Ask: ${call_58['ask']:.2f}")
    print(f"   Vol: {call_58['volume']:.0f}")
    print(f"   OI: {call_58['openInterest']:.0f}")
    print(f"   IV: {call_58['impliedVolatility']*100:.2f}%\n")
    
    print(f"   Should match Yahoo Finance website exactly! ✅")
    
    print(f"\n{'='*80}\n")
    
    # 9. CODE TRANSPARENCY
    print("9️⃣ EXACT CODE I USE:\n")
    
    print("```python")
    print("import yfinance as yf")
    print("")
    print("# Fetch ticker object")
    print("oxy = yf.Ticker('OXY')")
    print("")
    print("# Get current stock price")
    print("hist = oxy.history(period='1d', interval='1m')")
    print("current_price = hist['Close'].iloc[-1]")
    print("")
    print("# Get options chain for specific expiration")
    print("chain = oxy.option_chain('2026-03-20')")
    print("calls = chain.calls")
    print("puts = chain.puts")
    print("")
    print("# Get specific strike")
    print("call_58 = calls[calls['strike'] == 58.0].iloc[0]")
    print("")
    print("# Extract pricing")
    print("bid = call_58['bid']")
    print("ask = call_58['ask']")
    print("mid = (bid + ask) / 2  # This is what I use")
    print("iv = call_58['impliedVolatility']")
    print("```\n")
    
    print(f"{'='*80}\n")
    
    # 10. CONCLUSION
    print("🎯 CONCLUSION:\n")
    
    print("   DATA SOURCE: Yahoo Finance (yfinance library)")
    print("   PRICING: Real bid/ask/last prices from exchanges")
    print("   IMPLIED VOLATILITY: Provided by Yahoo Finance")
    print("   GREEKS: Calculated by me using Black-Scholes")
    print("   QUALITY: Sufficient for retail options analysis")
    print("   VERIFICATION: Cross-check at finance.yahoo.com/quote/OXY/options")
    print("   TRANSPARENCY: 100% open-source, replicable methodology")
    
    print(f"\n   As The Quant Oracle: I show my work. Always.")
    print(f"   The physics is only valid if the inputs are trustworthy.")
    print(f"   Yahoo Finance is the industry standard for free retail data.")
    
    print(f"\n{'='*80}\n")
    
    # Save sample data
    sample_calls = calls[calls['strike'].isin([57.0, 57.5, 58.0, 58.5, 59.0])].copy()
    sample_calls.to_csv('yahoo_finance_sample_data.csv', index=False)
    print("💾 Sample data saved to: yahoo_finance_sample_data.csv")
    print("   (You can inspect the raw Yahoo Finance data yourself)\n")
    
except Exception as e:
    print(f"   ❌ Error fetching data: {e}")
    print("   This could mean:")
    print("   • Market is closed and data is cached")
    print("   • Network connectivity issue")
    print("   • Yahoo Finance API temporarily down")
