#!/usr/bin/env python3
"""
The Quant Oracle - 3 Plays for TODAY on $OXY
$500 Cash Account | Intraday to 2-Day Holds
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TodayTradeBuilder:
    """Build specific trades for today with exact entry/exit points"""
    
    def __init__(self, ticker='OXY', capital=500, risk_free_rate=0.045):
        self.ticker = ticker
        self.capital = capital
        self.r = risk_free_rate
        self.stock = yf.Ticker(ticker)
        
    def get_market_data(self):
        """Fetch current OXY price and options"""
        print(f"\n{'='*80}")
        print(f"🎯 QUANT ORACLE - TRADE BUILDER FOR TODAY")
        print(f"{'='*80}\n")
        
        # Get current price
        hist = self.stock.history(period='1d', interval='1m')
        if not hist.empty:
            self.current_price = hist['Close'].iloc[-1]
            self.current_time = hist.index[-1]
            
            # Get intraday high/low for support/resistance
            self.day_high = hist['High'].max()
            self.day_low = hist['Low'].min()
            self.day_open = hist['Open'].iloc[0]
        else:
            hist = self.stock.history(period='5d')
            self.current_price = hist['Close'].iloc[-1]
            self.current_time = datetime.now()
            self.day_high = hist['High'].iloc[-1]
            self.day_low = hist['Low'].iloc[-1]
            self.day_open = hist['Open'].iloc[-1]
        
        # Get recent price action for trend
        hist_5d = self.stock.history(period='5d')
        self.price_5d_ago = hist_5d['Close'].iloc[0]
        self.trend_5d = ((self.current_price - self.price_5d_ago) / self.price_5d_ago) * 100
        
        print(f"📊 CURRENT MARKET CONDITIONS:")
        print(f"   Time: {self.current_time}")
        print(f"   OXY Price: ${self.current_price:.2f}")
        print(f"   Today's Range: ${self.day_low:.2f} - ${self.day_high:.2f}")
        print(f"   Day Open: ${self.day_open:.2f}")
        print(f"   Intraday Move: {((self.current_price - self.day_open) / self.day_open * 100):+.2f}%")
        print(f"   5-Day Trend: {self.trend_5d:+.2f}%")
        
        # Get options expirations
        expirations = self.stock.options
        print(f"\n📅 Available Expirations:")
        for i, exp in enumerate(expirations[:5]):
            days_out = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days
            print(f"   {exp} ({days_out} days)")
        
        return expirations
    
    def get_option_chain(self, exp_date):
        """Fetch specific expiration chain"""
        opt_chain = self.stock.option_chain(exp_date)
        exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
        T = (exp_datetime - datetime.now()).total_seconds() / (365.25 * 24 * 3600)
        return opt_chain.calls, opt_chain.puts, T
    
    def calculate_technical_levels(self):
        """Calculate key support/resistance levels"""
        # Use recent price action
        hist = self.stock.history(period='20d')
        
        # Key levels
        self.resistance_1 = hist['High'].quantile(0.75)
        self.resistance_2 = hist['High'].max()
        self.support_1 = hist['Low'].quantile(0.25)
        self.support_2 = hist['Low'].min()
        self.pivot = (self.day_high + self.day_low + self.current_price) / 3
        
        print(f"\n📊 TECHNICAL LEVELS:")
        print(f"   Resistance 2: ${self.resistance_2:.2f}")
        print(f"   Resistance 1: ${self.resistance_1:.2f}")
        print(f"   Current:      ${self.current_price:.2f} ← YOU ARE HERE")
        print(f"   Pivot:        ${self.pivot:.2f}")
        print(f"   Support 1:    ${self.support_1:.2f}")
        print(f"   Support 2:    ${self.support_2:.2f}")
    
    def build_trades(self):
        """Build 3 specific trades for today"""
        print(f"\n{'='*80}")
        print(f"🎯 BUILDING 3 TRADES FOR $500 CASH ACCOUNT")
        print(f"{'='*80}\n")
        
        # Get March 20 chain (shortest expiration for max gamma)
        exp_date = '2026-03-20'
        calls, puts, T = self.get_option_chain(exp_date)
        
        days_remaining = T * 365.25
        hours_remaining = days_remaining * 24
        
        print(f"📅 Using Expiration: {exp_date} ({days_remaining:.2f} days | {hours_remaining:.1f} hours)")
        print(f"💰 Available Capital: ${self.capital}")
        print(f"🎯 Risk Per Trade: ~${self.capital / 3:.2f}\n")
        
        # Strategy: Build 3 different plays
        # 1. Quick scalp (high gamma, tight stops)
        # 2. Directional momentum play
        # 3. High-probability theta collection
        
        trades = []
        
        # TRADE 1: ATM GAMMA SCALP
        atm_strike = round(self.current_price * 2) / 2  # Round to nearest $0.50
        trade1 = self.build_gamma_scalp(calls, atm_strike, T, exp_date)
        if trade1:
            trades.append(trade1)
        
        # TRADE 2: DIRECTIONAL MOMENTUM
        if self.trend_5d > 0:  # Bullish
            itm_strike = atm_strike - 0.50
            trade2 = self.build_momentum_play(calls, itm_strike, T, exp_date, 'CALL')
        else:  # Bearish
            itm_strike = atm_strike + 0.50
            trade2 = self.build_momentum_play(puts, itm_strike, T, exp_date, 'PUT')
        if trade2:
            trades.append(trade2)
        
        # TRADE 3: CREDIT SPREAD (defined risk)
        trade3 = self.build_credit_spread(calls, puts, T, exp_date)
        if trade3:
            trades.append(trade3)
        
        return trades
    
    def build_gamma_scalp(self, calls, strike, T, exp_date):
        """Build ATM gamma scalp trade"""
        option = calls[calls['strike'] == strike]
        if option.empty:
            return None
        
        row = option.iloc[0]
        
        # Get pricing
        if row['bid'] > 0 and row['ask'] > 0:
            entry_price = row['ask']  # Buy at ask
            bid_price = row['bid']
        else:
            entry_price = row['lastPrice']
            bid_price = entry_price * 0.95
        
        iv = row['impliedVolatility'] if row['impliedVolatility'] > 0.01 else 0.30
        
        # Calculate Greeks
        d1 = (np.log(self.current_price / strike) + (self.r + 0.5 * iv**2) * T) / (iv * np.sqrt(T))
        d2 = d1 - iv * np.sqrt(T)
        
        delta = norm.cdf(d1)
        gamma = norm.pdf(d1) / (self.current_price * iv * np.sqrt(T))
        theta = (-self.current_price * norm.pdf(d1) * iv / (2 * np.sqrt(T)) 
                - self.r * strike * np.exp(-self.r * T) * norm.cdf(d2)) / 365
        
        # Position sizing
        max_contracts = int((self.capital / 3) / (entry_price * 100))
        if max_contracts < 1:
            max_contracts = 1
        
        # Entry/Exit levels based on technical analysis + Greeks
        # Entry: NOW (at ask)
        # Exit 1 (Target): +30% profit (quick scalp)
        # Exit 2 (Stop): -40% loss or if OXY breaks support
        
        target_price = entry_price * 1.30
        stop_price = entry_price * 0.60
        
        # Calculate OXY price targets using delta
        # For 30% option gain, need: 0.30 * entry_price / delta move in stock
        oxy_target = self.current_price + (0.30 * entry_price / delta)
        oxy_stop = self.current_price - (0.40 * entry_price / delta)
        
        # Time-based exit
        if T * 365.25 > 1:
            time_exit = "End of day today (avoid overnight theta)"
        else:
            time_exit = "Before 2pm tomorrow (avoid final theta burn)"
        
        return {
            'name': 'GAMMA SCALP',
            'type': 'CALL',
            'strike': strike,
            'expiration': exp_date,
            'contracts': max_contracts,
            'entry_price': entry_price,
            'entry_cost': entry_price * 100 * max_contracts,
            'target_price': target_price,
            'stop_price': stop_price,
            'oxy_target': oxy_target,
            'oxy_stop': oxy_stop,
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'iv': iv,
            'time_exit': time_exit,
            'strategy': 'Quick intraday scalp on high gamma ATM option'
        }
    
    def build_momentum_play(self, options, strike, T, exp_date, option_type):
        """Build directional momentum play"""
        option = options[options['strike'] == strike]
        if option.empty:
            return None
        
        row = option.iloc[0]
        
        if row['bid'] > 0 and row['ask'] > 0:
            entry_price = row['ask']
            bid_price = row['bid']
        else:
            entry_price = row['lastPrice']
            bid_price = entry_price * 0.95
        
        iv = row['impliedVolatility'] if row['impliedVolatility'] > 0.01 else 0.30
        
        # Calculate Greeks
        d1 = (np.log(self.current_price / strike) + (self.r + 0.5 * iv**2) * T) / (iv * np.sqrt(T))
        d2 = d1 - iv * np.sqrt(T)
        
        if option_type == 'CALL':
            delta = norm.cdf(d1)
        else:
            delta = -norm.cdf(-d1)
        
        gamma = norm.pdf(d1) / (self.current_price * iv * np.sqrt(T))
        
        max_contracts = int((self.capital / 3) / (entry_price * 100))
        if max_contracts < 1:
            max_contracts = 1
        
        # Entry/Exit for momentum
        target_price = entry_price * 1.50  # 50% target
        stop_price = entry_price * 0.70  # -30% stop
        
        if option_type == 'CALL':
            oxy_target = self.resistance_1
            oxy_stop = self.support_1
        else:
            oxy_target = self.support_1
            oxy_stop = self.resistance_1
        
        time_exit = "Hold until target or tomorrow morning (ride momentum)"
        
        return {
            'name': 'DIRECTIONAL MOMENTUM',
            'type': option_type,
            'strike': strike,
            'expiration': exp_date,
            'contracts': max_contracts,
            'entry_price': entry_price,
            'entry_cost': entry_price * 100 * max_contracts,
            'target_price': target_price,
            'stop_price': stop_price,
            'oxy_target': oxy_target,
            'oxy_stop': oxy_stop,
            'delta': delta,
            'gamma': gamma,
            'theta': theta if option_type == 'CALL' else -abs(theta),
            'iv': iv,
            'time_exit': time_exit,
            'strategy': f'Ride the {self.trend_5d:+.1f}% trend with high delta exposure'
        }
    
    def build_credit_spread(self, calls, puts, T, exp_date):
        """Build credit spread for defined risk"""
        # Sell OTM put, buy further OTM put (bull put spread if bullish)
        # Or sell OTM call, buy further OTM call (bear call spread if bearish)
        
        if self.trend_5d > 0:  # Bullish - bull put spread
            # Sell put at support level, buy put $1 lower
            sell_strike = round(self.support_1 * 2) / 2
            buy_strike = sell_strike - 1.0
            
            sell_put = puts[puts['strike'] == sell_strike]
            buy_put = puts[puts['strike'] == buy_strike]
            
            if sell_put.empty or buy_put.empty:
                return None
            
            sell_premium = sell_put.iloc[0]['bid'] if sell_put.iloc[0]['bid'] > 0 else sell_put.iloc[0]['lastPrice'] * 0.95
            buy_premium = buy_put.iloc[0]['ask'] if buy_put.iloc[0]['ask'] > 0 else buy_put.iloc[0]['lastPrice'] * 1.05
            
            net_credit = sell_premium - buy_premium
            max_loss = (sell_strike - buy_strike) - net_credit
            max_profit = net_credit
            
            # For credit spreads in cash account, need full collateral
            collateral_required = max_loss * 100
            max_contracts = int((self.capital / 3) / collateral_required)
            if max_contracts < 1:
                return None
            
            return {
                'name': 'BULL PUT SPREAD',
                'type': 'SPREAD',
                'strike': f"{sell_strike}/{buy_strike}",
                'expiration': exp_date,
                'contracts': max_contracts,
                'entry_price': net_credit,
                'entry_cost': -net_credit * 100 * max_contracts,  # Negative = credit received
                'target_price': net_credit * 0.5,  # Close at 50% profit
                'stop_price': max_loss * 0.75,  # Exit if reaches 75% max loss
                'oxy_target': sell_strike + 1,  # Stay above sell strike
                'oxy_stop': sell_strike - 0.5,  # If approaches sell strike
                'delta': 'Net short delta (bullish)',
                'gamma': 'Limited',
                'theta': 'Positive (time decay helps)',
                'iv': 'Short vega',
                'time_exit': 'Hold to expiration or 50% profit',
                'strategy': f'Collect ${net_credit * 100 * max_contracts:.2f} credit, profit if OXY stays above ${sell_strike}',
                'max_profit': max_profit * 100 * max_contracts,
                'max_loss': max_loss * 100 * max_contracts
            }
        
        return None

def main():
    builder = TodayTradeBuilder(ticker='OXY', capital=500)
    
    # Get market data
    expirations = builder.get_market_data()
    
    # Calculate technical levels
    builder.calculate_technical_levels()
    
    # Build trades
    trades = builder.build_trades()
    
    # Display trades
    print(f"\n{'='*80}")
    print(f"🎯 THE QUANT ORACLE'S 3 PLAYS FOR TODAY")
    print(f"{'='*80}\n")
    
    total_capital_used = 0
    
    for i, trade in enumerate(trades, 1):
        print(f"\n{'#'*80}")
        print(f"🎯 PLAY #{i}: {trade['name']}")
        print(f"{'#'*80}\n")
        
        print(f"📊 POSITION DETAILS:")
        print(f"   Type: {trade['type']}")
        print(f"   Strike: ${trade['strike']}")
        print(f"   Expiration: {trade['expiration']}")
        print(f"   Contracts: {trade['contracts']}")
        print(f"   Strategy: {trade['strategy']}")
        
        print(f"\n💰 ENTRY/EXIT POINTS:")
        print(f"   ✅ ENTRY PRICE: ${trade['entry_price']:.2f} per option")
        print(f"   ✅ ENTRY COST: ${trade['entry_cost']:.2f} total")
        print(f"   🎯 TARGET PRICE: ${trade['target_price']:.2f} per option")
        print(f"   🛑 STOP PRICE: ${trade['stop_price']:.2f} per option")
        
        print(f"\n📈 OXY PRICE LEVELS:")
        print(f"   Entry Level: ${builder.current_price:.2f} (current)")
        print(f"   Target Level: ${trade['oxy_target']:.2f} (OXY needs to reach)")
        print(f"   Stop Level: ${trade['oxy_stop']:.2f} (exit if OXY hits)")
        
        print(f"\n⚡ THE GREEKS:")
        print(f"   Delta: {trade['delta']}")
        print(f"   Gamma: {trade['gamma']}")
        print(f"   Theta: {trade['theta']}")
        print(f"   IV: {trade['iv'] * 100 if isinstance(trade['iv'], float) else trade['iv']}")
        
        print(f"\n⏰ TIME MANAGEMENT:")
        print(f"   Time Exit: {trade['time_exit']}")
        
        if 'max_profit' in trade:
            print(f"\n💰 RISK/REWARD:")
            print(f"   Max Profit: ${trade['max_profit']:.2f}")
            print(f"   Max Loss: ${trade['max_loss']:.2f}")
            print(f"   Risk/Reward: 1:{trade['max_profit']/trade['max_loss']:.2f}")
        else:
            potential_profit = (trade['target_price'] - trade['entry_price']) * 100 * trade['contracts']
            potential_loss = (trade['entry_price'] - trade['stop_price']) * 100 * trade['contracts']
            print(f"\n💰 POTENTIAL OUTCOMES:")
            print(f"   Target Profit: ${potential_profit:.2f} ({((trade['target_price'] - trade['entry_price']) / trade['entry_price'] * 100):+.1f}%)")
            print(f"   Stop Loss: ${potential_loss:.2f} ({((trade['stop_price'] - trade['entry_price']) / trade['entry_price'] * 100):+.1f}%)")
        
        total_capital_used += abs(trade['entry_cost'])
        
        print(f"\n{'#'*80}\n")
    
    print(f"\n{'='*80}")
    print(f"💰 CAPITAL ALLOCATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"   Total Capital: ${builder.capital:.2f}")
    print(f"   Capital Used: ${total_capital_used:.2f}")
    print(f"   Remaining: ${builder.capital - total_capital_used:.2f}")
    print(f"   Utilization: {(total_capital_used / builder.capital * 100):.1f}%")
    print(f"\n{'='*80}\n")
    
    # Save trades
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv('oxy_today_trades.csv', index=False)
    print(f"💾 Trades saved to: oxy_today_trades.csv\n")

if __name__ == "__main__":
    main()
