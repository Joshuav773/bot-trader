#!/usr/bin/env python3
"""
The Quant Oracle - OXY Options Analysis for March 20th, 2026 Expiration
Identifies mispriced risk using Black-Scholes-Merton framework
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class QuantOracle:
    """Black-Scholes-Merton Options Analyzer"""
    
    def __init__(self, ticker='OXY', risk_free_rate=0.045):
        self.ticker = ticker
        self.r = risk_free_rate  # Current 3-month T-Bill rate ~4.5%
        self.stock = yf.Ticker(ticker)
        self.current_price = None
        self.options_data = []
        
    def fetch_market_data(self):
        """Fetch current stock price and options chain"""
        print(f"\n{'='*80}")
        print(f"🎯 QUANT ORACLE INITIALIZING - {self.ticker} OPTIONS ANALYSIS")
        print(f"{'='*80}\n")
        
        # Get current stock price
        hist = self.stock.history(period='1d')
        self.current_price = hist['Close'].iloc[-1] if not hist.empty else None
        
        if self.current_price is None:
            # Fallback to info
            info = self.stock.info
            self.current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        print(f"📊 Current {self.ticker} Price: ${self.current_price:.2f}")
        
        # Get available expiration dates
        expirations = self.stock.options
        print(f"\n📅 Available Expiration Dates:")
        for exp in expirations[:10]:
            print(f"   {exp}")
        
        return expirations
    
    def get_march_20_chain(self, expirations):
        """Find and fetch the March 20th, 2026 options chain"""
        target_date = '2026-03-20'
        
        # Try to find exact match or closest date
        if target_date in expirations:
            exp_date = target_date
        else:
            # Find closest match to March 20, 2026
            for exp in expirations:
                if '2026-03' in exp:
                    exp_date = exp
                    break
            else:
                exp_date = expirations[0]  # Fallback to nearest
        
        print(f"\n🎯 Analyzing Expiration: {exp_date}")
        
        # Fetch options chain
        opt_chain = self.stock.option_chain(exp_date)
        
        # Calculate time to expiration in years
        exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
        today = datetime.now()
        self.T = (exp_datetime - today).days / 365.0
        
        print(f"⏰ Days to Expiration: {int(self.T * 365)} ({self.T:.4f} years)")
        
        return opt_chain.calls, opt_chain.puts, exp_date
    
    def black_scholes_call(self, S0, K, T, r, sigma):
        """Calculate Black-Scholes Call Option Price"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        call_price = S0 * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        
        return call_price, d1, d2
    
    def black_scholes_put(self, S0, K, T, r, sigma):
        """Calculate Black-Scholes Put Option Price"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S0 * norm.cdf(-d1)
        
        return put_price, d1, d2
    
    def calculate_greeks(self, S0, K, T, r, sigma, option_type='call'):
        """Calculate option Greeks"""
        if T <= 0 or sigma <= 0:
            return {}
        
        d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (S0 * sigma * np.sqrt(T))
        
        # Vega (per 1% change in volatility)
        vega = S0 * norm.pdf(d1) * np.sqrt(T) / 100
        
        # Theta (per day)
        if option_type == 'call':
            theta = (-S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Probability of Profit (ITM at expiration)
        if option_type == 'call':
            prob_itm = norm.cdf(d2) * 100
        else:
            prob_itm = norm.cdf(-d2) * 100
        
        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'prob_itm': prob_itm,
            'd1': d1,
            'd2': d2
        }
    
    def analyze_option(self, row, option_type='call'):
        """Analyze a single option contract"""
        K = row['strike']
        
        # Handle market closed scenario - use lastPrice
        if row['bid'] == 0 and row['ask'] == 0:
            if pd.isna(row['lastPrice']) or row['lastPrice'] <= 0:
                return None
            market_price = row['lastPrice']
            # Estimate bid/ask with 5% spread
            spread = market_price * 0.05
            bid = market_price - spread/2
            ask = market_price + spread/2
        else:
            market_price = (row['bid'] + row['ask']) / 2
            bid = row['bid']
            ask = row['ask']
        
        iv = row['impliedVolatility']
        volume = row['volume'] if not pd.isna(row['volume']) else 0
        open_interest = row['openInterest'] if not pd.isna(row['openInterest']) else 0
        
        # Skip if no valid data
        if pd.isna(iv) or market_price <= 0:
            return None
        
        # For very low IV (placeholder values), estimate based on moneyness
        if iv < 0.1:
            # Estimate IV based on typical OXY volatility (around 30-40%)
            if option_type == 'call':
                moneyness_raw = self.current_price / K
            else:
                moneyness_raw = K / self.current_price
            
            # Higher IV for OTM options
            if moneyness_raw < 0.95:
                iv = 0.35
            elif moneyness_raw < 1.05:
                iv = 0.30
            else:
                iv = 0.40
        
        # Calculate theoretical price
        if option_type == 'call':
            theo_price, d1, d2 = self.black_scholes_call(
                self.current_price, K, self.T, self.r, iv
            )
        else:
            theo_price, d1, d2 = self.black_scholes_put(
                self.current_price, K, self.T, self.r, iv
            )
        
        # Calculate edge
        edge = ((theo_price - market_price) / market_price) * 100 if market_price > 0 else 0
        
        # Calculate Greeks
        greeks = self.calculate_greeks(
            self.current_price, K, self.T, self.r, iv, option_type
        )
        
        # Bid-Ask spread analysis
        spread_pct = ((ask - bid) / market_price * 100) if market_price > 0 else 100
        slippage_risk = 'HIGH' if spread_pct > 5 else 'MEDIUM' if spread_pct > 2 else 'LOW'
        
        # Moneyness
        if option_type == 'call':
            moneyness = (self.current_price - K) / K * 100
        else:
            moneyness = (K - self.current_price) / K * 100
        
        # Risk/Reward calculation
        max_loss = market_price
        if option_type == 'call':
            # Simplified - assume 20% move potential
            potential_intrinsic = max(0, self.current_price * 1.2 - K)
            max_gain = potential_intrinsic - market_price
        else:
            potential_intrinsic = max(0, K - self.current_price * 0.8)
            max_gain = potential_intrinsic - market_price
        
        risk_reward = max_gain / max_loss if max_loss > 0 else 0
        
        return {
            'type': option_type.upper(),
            'strike': K,
            'market_price': market_price,
            'bid': bid,
            'ask': ask,
            'theo_price': theo_price,
            'edge_pct': edge,
            'iv': iv * 100,
            'volume': volume,
            'open_interest': open_interest,
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'vega': greeks['vega'],
            'theta': greeks['theta'],
            'prob_itm': greeks['prob_itm'],
            'spread_pct': spread_pct,
            'slippage_risk': slippage_risk,
            'moneyness_pct': moneyness,
            'risk_reward': risk_reward,
            'd2': greeks['d2']
        }
    
    def analyze_chain(self, calls, puts):
        """Analyze entire options chain"""
        print(f"\n{'='*80}")
        print(f"⚡ ANALYZING OPTIONS CHAIN - BLACK-SCHOLES-MERTON ENGINE")
        print(f"{'='*80}\n")
        
        results = []
        
        # Analyze calls
        print("📈 Analyzing CALLS...")
        for idx, row in calls.iterrows():
            analysis = self.analyze_option(row, 'call')
            if analysis:
                results.append(analysis)
        
        # Analyze puts
        print("📉 Analyzing PUTS...")
        for idx, row in puts.iterrows():
            analysis = self.analyze_option(row, 'put')
            if analysis:
                results.append(analysis)
        
        df = pd.DataFrame(results)
        print(f"\n✅ Analyzed {len(df)} option contracts")
        
        return df
    
    def identify_top_trades(self, df, n=5):
        """Identify top 5 trades based on Quant Oracle criteria"""
        print(f"\n{'='*80}")
        print(f"🎯 IDENTIFYING TOP {n} TRADES - MISPRICED RISK DETECTION")
        print(f"{'='*80}\n")
        
        if len(df) == 0:
            print("❌ No option contracts available for analysis")
            return pd.DataFrame()
        
        # Filter criteria (relaxed for short-dated options):
        # 1. Minimum liquidity (open interest > 5 OR volume > 1)
        # 2. Reasonable bid-ask spread (< 20% for short-dated)
        # 3. Focus on near-the-money options (abs(moneyness) < 25%)
        
        filtered = df[
            ((df['open_interest'] > 5) | (df['volume'] > 1)) &
            (df['spread_pct'] < 20) &
            (df['moneyness_pct'].abs() < 25)
        ].copy()
        
        print(f"📊 Filtered to {len(filtered)} liquid contracts with tight spreads")
        
        # If we don't have enough after filtering, relax criteria
        if len(filtered) < n:
            print(f"⚠️  Limited liquid options found. Expanding criteria...")
            filtered = df[
                (df['moneyness_pct'].abs() < 30)
            ].copy()
            print(f"📊 Expanded to {len(filtered)} contracts")
        
        if len(filtered) == 0:
            print("❌ No viable option contracts found")
            return pd.DataFrame()
        
        # Scoring system
        # Positive edge = underpriced (buy signal)
        # Negative edge = overpriced (sell signal)
        
        # For buying opportunities (long positions)
        buy_candidates = filtered[filtered['edge_pct'] > 3].copy()
        if len(buy_candidates) > 0:
            buy_candidates['score'] = (
                buy_candidates['edge_pct'] * 0.4 +
                buy_candidates['risk_reward'] * 20 +
                buy_candidates['gamma'] * 100 +
                (100 - buy_candidates['iv']) * 0.1  # Prefer lower IV for buying
            )
        
        # For selling opportunities (short premium)
        sell_candidates = filtered[filtered['edge_pct'] < -3].copy()
        if len(sell_candidates) > 0:
            sell_candidates['score'] = (
                abs(sell_candidates['edge_pct']) * 0.4 +
                abs(sell_candidates['theta']) * 10 +
                sell_candidates['iv'] * 0.1  # Prefer higher IV for selling
            )
        
        # Combine and rank
        if len(buy_candidates) > 0:
            buy_candidates['strategy'] = 'LONG'
        if len(sell_candidates) > 0:
            sell_candidates['strategy'] = 'SHORT'
        
        all_candidates = pd.concat([buy_candidates, sell_candidates]) if len(buy_candidates) > 0 or len(sell_candidates) > 0 else pd.DataFrame()
        
        if len(all_candidates) == 0:
            print("⚠️  No clear directional edge detected. Showing best available by activity...")
            # Fall back to most active contracts
            filtered['score'] = (
                filtered['volume'] * 0.5 +
                filtered['open_interest'] * 0.3 +
                abs(filtered['gamma']) * 1000
            )
            filtered['strategy'] = 'NEUTRAL'
            return filtered.nlargest(n, 'score')
        
        top_trades = all_candidates.nlargest(n, 'score')
        
        return top_trades
    
    def format_trade_report(self, trades, exp_date):
        """Generate detailed trade report"""
        print(f"\n{'='*80}")
        print(f"📋 QUANT ORACLE VERDICT - TOP 5 OXY TRADES")
        print(f"{'='*80}\n")
        print(f"📊 Underlying: ${self.ticker} @ ${self.current_price:.2f}")
        print(f"📅 Expiration: {exp_date} ({int(self.T * 365)} days)")
        print(f"💰 Risk-Free Rate: {self.r * 100:.2f}%")
        print(f"\n{'='*80}\n")
        
        report_lines = []
        
        for i, (idx, trade) in enumerate(trades.iterrows(), 1):
            verdict = f"🎯 TRADE #{i}: {trade['strategy']} {trade['type']} ${trade['strike']:.2f}"
            
            report_lines.append(f"\n{'='*80}")
            report_lines.append(verdict)
            report_lines.append(f"{'='*80}")
            
            # Market Data
            report_lines.append(f"\n💹 MARKET DATA:")
            report_lines.append(f"   Market Premium: ${trade['market_price']:.2f} (Bid: ${trade['bid']:.2f} / Ask: ${trade['ask']:.2f})")
            report_lines.append(f"   Theoretical Value (BSM): ${trade['theo_price']:.2f}")
            report_lines.append(f"   📊 EDGE: {trade['edge_pct']:+.2f}% {'✅ UNDERPRICED' if trade['edge_pct'] > 0 else '⚠️ OVERPRICED'}")
            report_lines.append(f"   Implied Volatility: {trade['iv']:.1f}%")
            report_lines.append(f"   Volume: {trade['volume']:.0f} | Open Interest: {trade['open_interest']:.0f}")
            
            # Greek Analysis
            report_lines.append(f"\n⚡ THE GREEKS (Risk Profile):")
            report_lines.append(f"   Δ Delta: {trade['delta']:+.3f} (Directional exposure)")
            report_lines.append(f"   Γ Gamma: {trade['gamma']:.4f} (Acceleration factor)")
            report_lines.append(f"   ν Vega: ${trade['vega']:.2f} (IV sensitivity per 1%)")
            report_lines.append(f"   θ Theta: ${trade['theta']:.2f}/day (Time decay)")
            
            # Probability & Risk
            report_lines.append(f"\n📈 PROBABILITY & RISK:")
            report_lines.append(f"   Prob. of ITM (N(d₂)): {trade['prob_itm']:.1f}%")
            report_lines.append(f"   Moneyness: {trade['moneyness_pct']:+.1f}%")
            report_lines.append(f"   Risk/Reward Ratio: {trade['risk_reward']:.2f}:1")
            report_lines.append(f"   Bid-Ask Spread: {trade['spread_pct']:.2f}% - {trade['slippage_risk']} SLIPPAGE RISK")
            
            # Action Plan
            report_lines.append(f"\n🎯 ACTIONABLE STEPS:")
            if trade['strategy'] == 'LONG':
                report_lines.append(f"   ✅ ENTRY: BUY {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
                report_lines.append(f"   🛑 STOP LOSS: Exit if position loses 50% of premium (${trade['market_price'] * 0.5:.2f})")
                report_lines.append(f"   💰 TARGET: Exit at 100% gain or if IV increases by 10 points")
                report_lines.append(f"   ⚠️  RISK: Maximum loss = ${trade['market_price']:.2f} per contract")
            else:
                report_lines.append(f"   ✅ ENTRY: SELL {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
                report_lines.append(f"   🛑 STOP LOSS: Exit if price moves against delta by 2x")
                report_lines.append(f"   💰 TARGET: Close at 50% of max profit (${trade['market_price'] * 0.5:.2f})")
                report_lines.append(f"   ⚠️  RISK: Manage with stop-loss or convert to spread")
            
            # Greek Risk Warning
            if abs(trade['vega']) > 0.1:
                report_lines.append(f"\n⚠️  VEGA RISK: A 1% drop in IV will impact position by ${trade['vega']:.2f}")
            
            report_lines.append(f"\n{'='*80}\n")
        
        report = '\n'.join(report_lines)
        print(report)
        
        return report

def main():
    """Main execution function"""
    oracle = QuantOracle(ticker='OXY')
    
    # Fetch market data
    expirations = oracle.fetch_market_data()
    
    if not expirations:
        print("❌ Could not fetch options data")
        return
    
    # Get March 20th chain
    calls, puts, exp_date = oracle.get_march_20_chain(expirations)
    
    # Analyze chain
    analysis_df = oracle.analyze_chain(calls, puts)
    
    # Save full analysis
    analysis_df.to_csv('oxy_full_analysis.csv', index=False)
    print(f"\n💾 Full analysis saved to: oxy_full_analysis.csv")
    
    # Identify top trades
    top_trades = oracle.identify_top_trades(analysis_df, n=5)
    
    # Generate report
    report = oracle.format_trade_report(top_trades, exp_date)
    
    # Save report
    with open('oxy_trade_report.txt', 'w') as f:
        f.write(report)
    
    print(f"\n💾 Trade report saved to: oxy_trade_report.txt")
    
    # Save top trades CSV
    top_trades.to_csv('oxy_top_5_trades.csv', index=False)
    print(f"💾 Top trades saved to: oxy_top_5_trades.csv")
    
    print(f"\n{'='*80}")
    print("✅ QUANT ORACLE ANALYSIS COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
