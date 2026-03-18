#!/usr/bin/env python3
"""
The Quant Oracle - Performance Analysis
Track P&L from 11am March 17th entries
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class PerformanceTracker:
    """Track actual trade performance vs theoretical"""
    
    def __init__(self, ticker='OXY', risk_free_rate=0.045):
        self.ticker = ticker
        self.r = risk_free_rate
        self.stock = yf.Ticker(ticker)
        
        # Original entries at 11am March 17th
        self.entry_price = 57.41  # OXY price at analysis time
        self.entry_time = "11:00 AM EST, March 17, 2026"
        
        # Original trade entries (from our analysis)
        self.trades = [
            {
                'id': 1,
                'type': 'CALL',
                'strike': 57.50,
                'entry_premium': 0.99,
                'entry_delta': 0.4807,
                'entry_gamma': 0.312554,
                'entry_theta': -0.1303,
                'entry_vega': 0.0169,
                'entry_iv': 30.0,
                'strategy': 'GAMMA EXPLOSION',
                'position': 'LONG'
            },
            {
                'id': 2,
                'type': 'CALL',
                'strike': 58.00,
                'entry_premium': 0.79,
                'entry_delta': 0.3306,
                'entry_gamma': 0.284272,
                'entry_theta': -0.1178,
                'entry_vega': 0.0154,
                'entry_iv': 30.0,
                'strategy': 'GAMMA SCALP',
                'position': 'LONG'
            },
            {
                'id': 3,
                'type': 'PUT',
                'strike': 57.50,
                'entry_premium': 1.19,
                'entry_delta': -0.5193,
                'entry_gamma': 0.312554,
                'entry_theta': -0.1233,
                'entry_vega': 0.0169,
                'entry_iv': 30.0,
                'strategy': 'GAMMA EXPLOSION (BEARISH)',
                'position': 'LONG'
            },
            {
                'id': 4,
                'type': 'CALL',
                'strike': 57.00,
                'entry_premium': 1.25,
                'entry_delta': 0.6349,
                'entry_gamma': 0.294845,
                'entry_theta': -0.1242,
                'entry_vega': 0.0160,
                'entry_iv': 30.0,
                'strategy': 'DIRECTIONAL BULLISH',
                'position': 'LONG'
            },
            {
                'id': 5,
                'type': 'PUT',
                'strike': 57.00,
                'entry_premium': 0.88,
                'entry_delta': -0.3651,
                'entry_gamma': 0.294845,
                'entry_theta': -0.1172,
                'entry_vega': 0.0160,
                'entry_iv': 30.0,
                'strategy': 'BEARISH SPECULATION',
                'position': 'LONG'
            }
        ]
    
    def get_current_data(self):
        """Fetch current OXY price and options data"""
        print(f"\n{'='*80}")
        print(f"🎯 QUANT ORACLE - LIVE PERFORMANCE TRACKER")
        print(f"{'='*80}\n")
        
        # Get current stock price
        hist = self.stock.history(period='1d', interval='1m')
        if not hist.empty:
            self.current_price = hist['Close'].iloc[-1]
            self.current_time = hist.index[-1]
        else:
            hist = self.stock.history(period='1d')
            self.current_price = hist['Close'].iloc[-1] if not hist.empty else self.entry_price
            self.current_time = datetime.now()
        
        print(f"📊 ENTRY TIME: {self.entry_time}")
        print(f"📊 ENTRY PRICE: ${self.entry_price:.2f}")
        print(f"📊 CURRENT TIME: {self.current_time}")
        print(f"📊 CURRENT PRICE: ${self.current_price:.2f}")
        print(f"📊 PRICE CHANGE: {self.current_price - self.entry_price:+.2f} ({((self.current_price - self.entry_price) / self.entry_price * 100):+.2f}%)")
        
        # Fetch current options chain
        exp_date = '2026-03-20'
        try:
            opt_chain = self.stock.option_chain(exp_date)
            self.calls = opt_chain.calls
            self.puts = opt_chain.puts
            
            # Calculate remaining time
            exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
            self.T_remaining = (exp_datetime - datetime.now()).total_seconds() / (365.25 * 24 * 3600)
            
            print(f"⏰ TIME REMAINING: {self.T_remaining * 365.25:.3f} days")
            
            return True
        except Exception as e:
            print(f"❌ Error fetching options: {e}")
            return False
    
    def get_current_option_price(self, option_type, strike):
        """Get current market price for an option"""
        if option_type == 'CALL':
            option = self.calls[self.calls['strike'] == strike]
        else:
            option = self.puts[self.puts['strike'] == strike]
        
        if option.empty:
            return None, None
        
        row = option.iloc[0]
        
        # Use mid price or last price
        if row['bid'] > 0 and row['ask'] > 0:
            current_premium = (row['bid'] + row['ask']) / 2
        elif row['lastPrice'] > 0:
            current_premium = row['lastPrice']
        else:
            return None, None
        
        current_iv = row['impliedVolatility'] if row['impliedVolatility'] > 0.01 else 0.30
        
        return current_premium, current_iv
    
    def calculate_current_greeks(self, S0, K, T, r, sigma, option_type='call'):
        """Calculate current Greeks"""
        if T <= 0 or sigma <= 0:
            return {}
        
        d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type.upper() == 'CALL':
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        gamma = norm.pdf(d1) / (S0 * sigma * np.sqrt(T))
        vega = S0 * norm.pdf(d1) * np.sqrt(T) / 100
        
        if option_type.upper() == 'CALL':
            theta = (-S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (-S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta
        }
    
    def analyze_performance(self):
        """Analyze performance of each trade"""
        print(f"\n{'='*80}")
        print(f"📊 TRADE-BY-TRADE PERFORMANCE ANALYSIS")
        print(f"{'='*80}\n")
        
        results = []
        
        for trade in self.trades:
            print(f"\n{'#'*80}")
            print(f"🎯 TRADE #{trade['id']}: {trade['position']} {trade['type']} ${trade['strike']:.2f}")
            print(f"{'#'*80}\n")
            print(f"📖 Strategy: {trade['strategy']}")
            
            # Get current option price
            current_premium, current_iv = self.get_current_option_price(
                trade['type'], trade['strike']
            )
            
            if current_premium is None:
                print(f"⚠️  No current pricing data available")
                continue
            
            # Calculate P&L
            entry_cost = trade['entry_premium'] * 100  # Per contract
            current_value = current_premium * 100
            pnl = current_value - entry_cost
            pnl_pct = (pnl / entry_cost) * 100
            
            print(f"\n💰 POSITION P&L:")
            print(f"   Entry Premium: ${trade['entry_premium']:.2f} (${entry_cost:.2f} per contract)")
            print(f"   Current Premium: ${current_premium:.2f} (${current_value:.2f} per contract)")
            print(f"   P&L: ${pnl:+.2f} per contract ({pnl_pct:+.2f}%)")
            
            # Status indicator
            if pnl_pct > 50:
                status = "🟢 MASSIVE WIN - Take Profits!"
            elif pnl_pct > 20:
                status = "🟢 STRONG PROFIT - Consider exit"
            elif pnl_pct > 0:
                status = "🟡 SMALL PROFIT - Monitor"
            elif pnl_pct > -20:
                status = "🟡 SMALL LOSS - Manage risk"
            elif pnl_pct > -40:
                status = "🔴 MODERATE LOSS - Consider exit"
            else:
                status = "🔴 HEAVY LOSS - Exit now!"
            
            print(f"   Status: {status}")
            
            # Calculate current Greeks
            current_greeks = self.calculate_current_greeks(
                self.current_price,
                trade['strike'],
                self.T_remaining,
                self.r,
                current_iv,
                trade['type']
            )
            
            print(f"\n⚡ GREEK EVOLUTION:")
            print(f"   Delta:  {trade['entry_delta']:+.4f} → {current_greeks['delta']:+.4f} (Δ: {current_greeks['delta'] - trade['entry_delta']:+.4f})")
            print(f"   Gamma:  {trade['entry_gamma']:.6f} → {current_greeks['gamma']:.6f} (Δ: {current_greeks['gamma'] - trade['entry_gamma']:+.6f})")
            print(f"   Theta:  ${trade['entry_theta']:.4f} → ${current_greeks['theta']:.4f} (Δ: ${current_greeks['theta'] - trade['entry_theta']:+.4f})")
            print(f"   Vega:   ${trade['entry_vega']:.4f} → ${current_greeks['vega']:.4f} (Δ: ${current_greeks['vega'] - trade['entry_vega']:+.4f})")
            
            # Calculate theta decay impact
            time_elapsed = 0.0055 - self.T_remaining  # In years
            hours_elapsed = time_elapsed * 365.25 * 24
            theta_decay = trade['entry_theta'] * (time_elapsed * 365.25)
            
            print(f"\n⏰ TIME DECAY ANALYSIS:")
            print(f"   Time Elapsed: {hours_elapsed:.2f} hours")
            print(f"   Theta Decay Cost: ${theta_decay:.4f}")
            
            # Calculate delta P&L (from stock movement)
            stock_move = self.current_price - self.entry_price
            delta_pnl = trade['entry_delta'] * stock_move * 100
            gamma_pnl = 0.5 * trade['entry_gamma'] * (stock_move ** 2) * 100
            
            print(f"\n📊 P&L ATTRIBUTION:")
            print(f"   Stock Move: ${stock_move:+.2f} ({((stock_move / self.entry_price) * 100):+.2f}%)")
            print(f"   Delta P&L: ${delta_pnl:+.2f}")
            print(f"   Gamma P&L: ${gamma_pnl:+.2f}")
            print(f"   Theta Cost: ${theta_decay * 100:+.2f}")
            print(f"   IV Change Impact: ${(current_value - entry_cost - delta_pnl - gamma_pnl - theta_decay * 100):+.2f}")
            
            # Recommendation
            print(f"\n🎯 QUANT ORACLE RECOMMENDATION:")
            if pnl_pct > 50:
                print(f"   ✅ TAKE PROFITS NOW! You've hit the 50%+ target.")
                print(f"   Exit at market or set limit at ${current_premium:.2f}")
            elif pnl_pct > 20:
                print(f"   ✅ Strong profit zone. Consider taking 50% off, let rest run.")
            elif pnl_pct > 0:
                print(f"   🟡 Small profit. Set stop at break-even (${trade['entry_premium']:.2f})")
            elif pnl_pct > -20:
                print(f"   🟡 Manageable loss. Monitor for reversal or cut at -40%")
            elif pnl_pct > -40:
                print(f"   ⚠️  Approaching stop-loss. Consider exit.")
            else:
                print(f"   🔴 STOP-LOSS TRIGGERED! Exit immediately.")
            
            # Store result
            results.append({
                'trade_id': trade['id'],
                'type': trade['type'],
                'strike': trade['strike'],
                'strategy': trade['strategy'],
                'entry_premium': trade['entry_premium'],
                'current_premium': current_premium,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'status': status,
                'current_delta': current_greeks['delta'],
                'current_gamma': current_greeks['gamma']
            })
            
            print(f"\n{'#'*80}\n")
        
        return pd.DataFrame(results)
    
    def generate_summary(self, results_df):
        """Generate portfolio summary"""
        print(f"\n{'='*80}")
        print(f"📊 PORTFOLIO PERFORMANCE SUMMARY")
        print(f"{'='*80}\n")
        
        total_entry_cost = sum([t['entry_premium'] for t in self.trades]) * 100
        total_current_value = results_df['current_premium'].sum() * 100
        total_pnl = results_df['pnl'].sum()
        total_pnl_pct = (total_pnl / total_entry_cost) * 100
        
        print(f"💰 AGGREGATE PORTFOLIO (All 5 Trades):")
        print(f"   Total Entry Cost: ${total_entry_cost:.2f}")
        print(f"   Total Current Value: ${total_current_value:.2f}")
        print(f"   Total P&L: ${total_pnl:+.2f} ({total_pnl_pct:+.2f}%)")
        
        # Best and worst performers
        best = results_df.loc[results_df['pnl_pct'].idxmax()]
        worst = results_df.loc[results_df['pnl_pct'].idxmin()]
        
        print(f"\n🏆 BEST PERFORMER:")
        print(f"   Trade #{best['trade_id']}: {best['type']} ${best['strike']:.2f}")
        print(f"   P&L: {best['pnl_pct']:+.2f}% (${best['pnl']:+.2f})")
        print(f"   Strategy: {best['strategy']}")
        
        print(f"\n📉 WORST PERFORMER:")
        print(f"   Trade #{worst['trade_id']}: {worst['type']} ${worst['strike']:.2f}")
        print(f"   P&L: {worst['pnl_pct']:+.2f}% (${worst['pnl']:+.2f})")
        print(f"   Strategy: {worst['strategy']}")
        
        # Win rate
        winners = len(results_df[results_df['pnl'] > 0])
        win_rate = (winners / len(results_df)) * 100
        
        print(f"\n📊 STATISTICS:")
        print(f"   Win Rate: {winners}/{len(results_df)} ({win_rate:.1f}%)")
        print(f"   Average Return: {results_df['pnl_pct'].mean():+.2f}%")
        print(f"   Best Return: {results_df['pnl_pct'].max():+.2f}%")
        print(f"   Worst Return: {results_df['pnl_pct'].min():+.2f}%")
        
        print(f"\n🎯 OVERALL VERDICT:")
        if total_pnl_pct > 20:
            print(f"   🟢 PORTFOLIO OUTPERFORMING - Strong execution on gamma thesis")
        elif total_pnl_pct > 0:
            print(f"   🟡 PORTFOLIO PROFITABLE - Continue to manage risk")
        else:
            print(f"   🔴 PORTFOLIO UNDERWATER - Re-evaluate positions")
        
        # Gamma exposure summary
        total_gamma = results_df['current_gamma'].sum()
        print(f"\n⚡ CURRENT GAMMA EXPOSURE:")
        print(f"   Total Portfolio Gamma: {total_gamma:.6f}")
        print(f"   Risk: ${total_gamma * 100:.2f} delta change per $1 OXY move")
        
        print(f"\n{'='*80}\n")
        
        return results_df

def main():
    tracker = PerformanceTracker()
    
    # Get current market data
    if not tracker.get_current_data():
        print("Failed to fetch market data")
        return
    
    # Analyze performance
    results = tracker.analyze_performance()
    
    if results.empty:
        print("No performance data available")
        return
    
    # Generate summary
    summary = tracker.generate_summary(results)
    
    # Save results
    summary.to_csv('oxy_performance_results.csv', index=False)
    print(f"💾 Performance results saved to: oxy_performance_results.csv\n")

if __name__ == "__main__":
    main()
