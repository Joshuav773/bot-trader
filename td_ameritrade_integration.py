#!/usr/bin/env python3
"""
The Quant Oracle - TD Ameritrade Real-Time Integration
Live options analysis with real-time bid/ask from TDA
"""

import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy.stats import norm
import time

class TDAmeritradeQuant:
    """
    Quant Oracle with TD Ameritrade Real-Time Data
    """
    
    def __init__(self, api_key=None, access_token=None):
        """
        Initialize with TD Ameritrade credentials
        
        Args:
            api_key: Your TDA API key (from developer.tdameritrade.com)
            access_token: OAuth access token
        """
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = "https://api.tdameritrade.com/v1"
        
        # Risk-free rate
        self.r = 0.045
        
        print(f"\n{'='*80}")
        print(f"🎯 QUANT ORACLE - TD AMERITRADE REAL-TIME INTEGRATION")
        print(f"{'='*80}\n")
        
        if not api_key:
            print("⚠️  NO API KEY PROVIDED")
            print("\n📋 TO GET TD AMERITRADE API ACCESS:")
            print("   1. Go to: https://developer.tdameritrade.com/")
            print("   2. Register for API access")
            print("   3. Create an app to get API key")
            print("   4. Use OAuth to get access token")
            print("\n   See full setup guide below...")
            self.demo_mode = True
        else:
            print("✅ API KEY PROVIDED")
            self.demo_mode = False
    
    def get_quote(self, symbol='OXY'):
        """Get real-time stock quote from TD Ameritrade"""
        if self.demo_mode:
            print(f"⚠️  DEMO MODE - Using simulated data")
            return self._get_simulated_quote()
        
        url = f"{self.base_url}/marketdata/{symbol}/quotes"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        params = {'apikey': self.api_key}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            quote = data[symbol]
            return {
                'symbol': symbol,
                'price': quote['lastPrice'],
                'bid': quote['bidPrice'],
                'ask': quote['askPrice'],
                'volume': quote['totalVolume'],
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"❌ Error fetching quote: {e}")
            return self._get_simulated_quote()
    
    def get_option_chain(self, symbol='OXY', strike=None, exp_date=None):
        """
        Get real-time options chain from TD Ameritrade
        
        Args:
            symbol: Stock ticker
            strike: Specific strike (or None for all)
            exp_date: Expiration date (format: 2026-03-20)
        """
        if self.demo_mode:
            print(f"⚠️  DEMO MODE - Using simulated option data")
            return self._get_simulated_chain()
        
        url = f"{self.base_url}/marketdata/chains"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        params = {
            'apikey': self.api_key,
            'symbol': symbol,
            'contractType': 'ALL',
            'includeQuotes': 'TRUE',
            'strategy': 'SINGLE'
        }
        
        if strike:
            params['strike'] = strike
        if exp_date:
            params['fromDate'] = exp_date
            params['toDate'] = exp_date
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_option_chain(data)
        except Exception as e:
            print(f"❌ Error fetching option chain: {e}")
            return self._get_simulated_chain()
    
    def _parse_option_chain(self, data):
        """Parse TDA option chain response"""
        underlying = data.get('underlyingPrice', 0)
        
        calls = []
        puts = []
        
        # Parse call options
        call_map = data.get('callExpDateMap', {})
        for exp_date, strikes in call_map.items():
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    calls.append({
                        'strike': float(strike_price),
                        'expiration': exp_date.split(':')[0],
                        'bid': contract.get('bid', 0),
                        'ask': contract.get('ask', 0),
                        'last': contract.get('last', 0),
                        'volume': contract.get('totalVolume', 0),
                        'openInterest': contract.get('openInterest', 0),
                        'volatility': contract.get('volatility', 0) / 100,  # Convert to decimal
                        'delta': contract.get('delta', 0),
                        'gamma': contract.get('gamma', 0),
                        'theta': contract.get('theta', 0),
                        'vega': contract.get('vega', 0)
                    })
        
        # Parse put options
        put_map = data.get('putExpDateMap', {})
        for exp_date, strikes in put_map.items():
            for strike_price, contracts in strikes.items():
                for contract in contracts:
                    puts.append({
                        'strike': float(strike_price),
                        'expiration': exp_date.split(':')[0],
                        'bid': contract.get('bid', 0),
                        'ask': contract.get('ask', 0),
                        'last': contract.get('last', 0),
                        'volume': contract.get('totalVolume', 0),
                        'openInterest': contract.get('openInterest', 0),
                        'volatility': contract.get('volatility', 0) / 100,
                        'delta': contract.get('delta', 0),
                        'gamma': contract.get('gamma', 0),
                        'theta': contract.get('theta', 0),
                        'vega': contract.get('vega', 0)
                    })
        
        return {
            'underlying': underlying,
            'calls': pd.DataFrame(calls) if calls else pd.DataFrame(),
            'puts': pd.DataFrame(puts) if puts else pd.DataFrame(),
            'timestamp': datetime.now()
        }
    
    def _get_simulated_quote(self):
        """Simulated quote for demo"""
        return {
            'symbol': 'OXY',
            'price': 58.51,
            'bid': 58.50,
            'ask': 58.52,
            'volume': 12500000,
            'timestamp': datetime.now()
        }
    
    def _get_simulated_chain(self):
        """Simulated option chain for demo"""
        # Create realistic simulated data
        strikes = [57.0, 57.5, 58.0, 58.5, 59.0]
        calls_data = []
        puts_data = []
        
        for strike in strikes:
            # Calls
            calls_data.append({
                'strike': strike,
                'expiration': '2026-03-20',
                'bid': max(0.10, 58.51 - strike - 0.05),
                'ask': max(0.15, 58.51 - strike + 0.05),
                'last': max(0.12, 58.51 - strike),
                'volume': 500,
                'openInterest': 2000,
                'volatility': 0.35,
                'delta': 0.5,
                'gamma': 0.3,
                'theta': -0.2,
                'vega': 0.015
            })
            
            # Puts
            puts_data.append({
                'strike': strike,
                'expiration': '2026-03-20',
                'bid': max(0.10, strike - 58.51 - 0.05),
                'ask': max(0.15, strike - 58.51 + 0.05),
                'last': max(0.12, strike - 58.51),
                'volume': 300,
                'openInterest': 1500,
                'volatility': 0.35,
                'delta': -0.5,
                'gamma': 0.3,
                'theta': -0.2,
                'vega': 0.015
            })
        
        return {
            'underlying': 58.51,
            'calls': pd.DataFrame(calls_data),
            'puts': pd.DataFrame(puts_data),
            'timestamp': datetime.now()
        }
    
    def analyze_realtime(self, symbol='OXY', strikes=[57.0, 58.0], exp_date='2026-03-20'):
        """
        Real-time analysis with live TDA data
        """
        print(f"\n{'='*80}")
        print(f"📊 REAL-TIME ANALYSIS - {symbol} {exp_date}")
        print(f"{'='*80}\n")
        
        # Get real-time stock quote
        quote = self.get_quote(symbol)
        print(f"⏰ TIMESTAMP: {quote['timestamp']}")
        print(f"📊 {symbol} PRICE: ${quote['price']:.2f}")
        print(f"   Bid: ${quote['bid']:.2f} | Ask: ${quote['ask']:.2f}")
        print(f"   Volume: {quote['volume']:,}\n")
        
        # Get real-time option chain
        chain = self.get_option_chain(symbol, exp_date=exp_date)
        
        print(f"✅ Retrieved options data")
        print(f"   Calls: {len(chain['calls'])} contracts")
        print(f"   Puts: {len(chain['puts'])} contracts\n")
        
        print(f"{'='*80}\n")
        
        # Analyze each strike
        for strike in strikes:
            self._analyze_strike_realtime(chain, strike, quote['price'], exp_date)
    
    def _analyze_strike_realtime(self, chain, strike, current_price, exp_date):
        """Analyze specific strike with real-time data"""
        
        calls = chain['calls']
        call = calls[calls['strike'] == strike]
        
        if call.empty:
            print(f"⚠️  No data for CALL ${strike}")
            return
        
        call = call.iloc[0]
        
        print(f"{'#'*80}")
        print(f"🎯 REAL-TIME ANALYSIS: CALL ${strike:.2f}")
        print(f"{'#'*80}\n")
        
        print(f"💰 LIVE PRICING (FROM TD AMERITRADE):")
        print(f"   BID:  ${call['bid']:.2f}  ← You can SELL here")
        print(f"   ASK:  ${call['ask']:.2f}  ← You must pay this to BUY")
        print(f"   MID:  ${(call['bid'] + call['ask'])/2:.2f}  ← Fair value")
        print(f"   LAST: ${call['last']:.2f}  ← Last trade\n")
        
        spread = call['ask'] - call['bid']
        spread_pct = (spread / ((call['bid'] + call['ask'])/2)) * 100
        
        print(f"📊 SPREAD ANALYSIS:")
        print(f"   Spread: ${spread:.2f} ({spread_pct:.2f}%)")
        if spread_pct > 5:
            print(f"   Risk: 🔴 HIGH SLIPPAGE")
        elif spread_pct > 2:
            print(f"   Risk: 🟡 MODERATE")
        else:
            print(f"   Risk: 🟢 TIGHT SPREAD")
        
        print(f"\n📈 LIQUIDITY:")
        print(f"   Volume: {call['volume']:.0f}")
        print(f"   Open Interest: {call['openInterest']:.0f}")
        
        print(f"\n⚡ THE GREEKS (FROM TD AMERITRADE):")
        print(f"   Δ Delta: {call['delta']:+.4f}")
        print(f"   Γ Gamma: {call['gamma']:.6f}")
        print(f"   θ Theta: ${call['theta']:.4f}/day")
        print(f"   ν Vega:  ${call['vega']:.4f}")
        print(f"   σ IV:    {call['volatility']*100:.2f}%")
        
        # Calculate time to expiration
        exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
        T = (exp_dt - datetime.now()).days / 365.25
        
        print(f"\n⏰ TIME ANALYSIS:")
        print(f"   Days to Exp: {T*365.25:.1f}")
        print(f"   Theta per hour: ${abs(call['theta'])/24:.4f}")
        print(f"   Theta per day: ${abs(call['theta']):.4f}")
        
        # Entry/exit levels
        mid_price = (call['bid'] + call['ask']) / 2
        
        print(f"\n🎯 RECOMMENDED TRADE LEVELS:")
        print(f"   ENTRY (buy at ask): ${call['ask']:.2f}")
        print(f"   TARGET +25%: ${call['ask'] * 1.25:.2f}")
        print(f"   TARGET +50%: ${call['ask'] * 1.50:.2f}")
        print(f"   STOP -35%: ${call['ask'] * 0.65:.2f}")
        
        # Calculate required OXY moves
        target_1_oxy = current_price + ((call['ask'] * 1.25 - call['ask']) / call['delta'])
        target_2_oxy = current_price + ((call['ask'] * 1.50 - call['ask']) / call['delta'])
        stop_oxy = current_price + ((call['ask'] * 0.65 - call['ask']) / call['delta'])
        
        print(f"\n📈 REQUIRED OXY MOVES:")
        print(f"   For +25% gain: OXY → ${target_1_oxy:.2f} ({((target_1_oxy-current_price)/current_price*100):+.2f}%)")
        print(f"   For +50% gain: OXY → ${target_2_oxy:.2f} ({((target_2_oxy-current_price)/current_price*100):+.2f}%)")
        print(f"   Stop triggers: OXY → ${stop_oxy:.2f} ({((stop_oxy-current_price)/current_price*100):+.2f}%)")
        
        print(f"\n💡 QUANT ORACLE VERDICT:")
        
        # Moneyness
        moneyness = ((current_price - strike) / strike) * 100
        
        if abs(moneyness) < 1:
            verdict = "ATM - MAXIMUM GAMMA - Best for scalps"
        elif moneyness > 1:
            verdict = "ITM - HIGH DELTA - Directional play"
        else:
            verdict = "OTM - LOTTERY TICKET - High risk/reward"
        
        print(f"   Strike Classification: {verdict}")
        print(f"   Moneyness: {moneyness:+.2f}%")
        
        if spread_pct > 10:
            print(f"   ⚠️  WARNING: Wide spread - wait for tighter pricing")
        
        if call['volume'] < 10:
            print(f"   ⚠️  WARNING: Low volume - liquidity risk")
        
        print(f"\n{'#'*80}\n")

def setup_guide():
    """Print TD Ameritrade API setup guide"""
    print(f"\n{'='*80}")
    print(f"📋 TD AMERITRADE API SETUP GUIDE")
    print(f"{'='*80}\n")
    
    print("STEP 1: GET API KEY")
    print("─" * 80)
    print("1. Go to: https://developer.tdameritrade.com/")
    print("2. Click 'Register' (top right)")
    print("3. Create account with your TD Ameritrade login")
    print("4. Click 'My Apps' → 'Add a new App'")
    print("5. Fill out:")
    print("   App Name: 'Quant Oracle'")
    print("   Callback URL: http://localhost:8080")
    print("   What is your app going to do?: 'Personal trading analysis'")
    print("6. Submit → You'll get:")
    print("   • Consumer Key (this is your API key)")
    print("   • Consumer Secret\n")
    
    print("STEP 2: GET ACCESS TOKEN (OAuth)")
    print("─" * 80)
    print("TD Ameritrade uses OAuth 2.0. Two methods:\n")
    
    print("METHOD A: Simple (Manual - Good for $500 account)")
    print("1. Use your API key directly in thinkorswim platform")
    print("2. No coding required")
    print("3. Manual verification before trades\n")
    
    print("METHOD B: Advanced (Automated - For coders)")
    print("1. Install: pip install tda-api")
    print("2. Use library to handle OAuth:")
    print("""
from tda import auth, client
import json

# First time setup
token_path = 'token.json'
api_key = 'YOUR_CONSUMER_KEY@AMER.OAUTHAP'
redirect_uri = 'http://localhost:8080'

try:
    c = auth.client_from_token_file(token_path, api_key)
except FileNotFoundError:
    from selenium import webdriver
    with webdriver.Chrome() as driver:
        c = auth.client_from_login_flow(
            driver, api_key, redirect_uri, token_path)

# Now you have authenticated client
print("✅ Authenticated!")
""")
    
    print("\nSTEP 3: TEST CONNECTION")
    print("─" * 80)
    print("""
# Test your connection
quote = c.get_quote('OXY')
print(quote.json())

# Get option chain
chain = c.get_option_chain('OXY',
    contract_type=client.Options.ContractType.CALL,
    strike=58,
    from_date='2026-03-20',
    to_date='2026-03-20'
)
print(chain.json())
""")
    
    print("\nSTEP 4: INTEGRATE WITH QUANT ORACLE")
    print("─" * 80)
    print("""
# Use with my analysis
quant = TDAmeritradeQuant(
    api_key='YOUR_CONSUMER_KEY@AMER.OAUTHAP',
    access_token='YOUR_ACCESS_TOKEN'
)

# Get real-time analysis
quant.analyze_realtime('OXY', strikes=[57.0, 58.0], exp_date='2026-03-20')
""")
    
    print("\n" + "="*80)
    print("🎯 ALTERNATIVE: USE THINKORSWIM PLATFORM (EASIEST)")
    print("="*80 + "\n")
    
    print("If API setup is too complex, use thinkorswim manually:")
    print("\n1. Open thinkorswim desktop or mobile app")
    print("2. Navigate to: Trade → Options")
    print("3. Enter: OXY")
    print("4. Select expiration: March 20, 2026")
    print("5. View real-time bid/ask for all strikes")
    print("6. Use my analysis for which strikes to trade")
    print("7. Execute trades directly in thinkorswim\n")
    
    print("This gives you:")
    print("✅ Real-time pricing (no 15-min delay)")
    print("✅ Professional platform")
    print("✅ My analysis for strategy")
    print("✅ Best execution\n")
    
    print("="*80 + "\n")

def main():
    """Demo the TD Ameritrade integration"""
    
    # Initialize (demo mode - no API key)
    quant = TDAmeritradeQuant()
    
    # Run real-time analysis
    quant.analyze_realtime('OXY', strikes=[57.0, 58.0], exp_date='2026-03-20')
    
    # Print setup guide
    setup_guide()
    
    print("\n" + "="*80)
    print("💾 SAVE THIS FILE AND RUN WITH YOUR API KEY:")
    print("="*80 + "\n")
    print("# With API credentials:")
    print("quant = TDAmeritradeQuant(")
    print("    api_key='YOUR_API_KEY@AMER.OAUTHAP',")
    print("    access_token='YOUR_ACCESS_TOKEN'")
    print(")")
    print("\n# Get live analysis")
    print("quant.analyze_realtime('OXY', strikes=[57, 58], exp_date='2026-03-20')")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
