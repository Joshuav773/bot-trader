#!/usr/bin/env python3
"""Quick check of OXY options data"""

import yfinance as yf
import pandas as pd

ticker = yf.Ticker('OXY')

# Get current price
hist = ticker.history(period='1d')
current_price = hist['Close'].iloc[-1]
print(f"Current OXY Price: ${current_price:.2f}")

# Check March 20 expiration
exp_date = '2026-03-20'
try:
    chain = ticker.option_chain(exp_date)
    
    print(f"\nCALLS for {exp_date}:")
    print(chain.calls[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(20))
    
    print(f"\nPUTS for {exp_date}:")
    print(chain.puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(20))
    
    print(f"\nCALLS shape: {chain.calls.shape}")
    print(f"PUTS shape: {chain.puts.shape}")
    
    # Check for valid data
    valid_calls = chain.calls[
        (chain.calls['bid'] > 0) & 
        (chain.calls['ask'] > 0) & 
        (chain.calls['impliedVolatility'] > 0)
    ]
    valid_puts = chain.puts[
        (chain.puts['bid'] > 0) & 
        (chain.puts['ask'] > 0) & 
        (chain.puts['impliedVolatility'] > 0)
    ]
    
    print(f"\nValid CALLS with pricing: {len(valid_calls)}")
    print(f"Valid PUTS with pricing: {len(valid_puts)}")
    
except Exception as e:
    print(f"Error: {e}")

# Check next expiration
print(f"\n\n{'='*80}")
exp_date = '2026-03-27'
try:
    chain = ticker.option_chain(exp_date)
    
    print(f"\nCALLS for {exp_date}:")
    print(chain.calls[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(20))
    
    print(f"\nPUTS for {exp_date}:")
    print(chain.puts[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(20))
    
    valid_calls = chain.calls[
        (chain.calls['bid'] > 0) & 
        (chain.calls['ask'] > 0) & 
        (chain.calls['impliedVolatility'] > 0)
    ]
    valid_puts = chain.puts[
        (chain.puts['bid'] > 0) & 
        (chain.puts['ask'] > 0) & 
        (chain.puts['impliedVolatility'] > 0)
    ]
    
    print(f"\nValid CALLS with pricing: {len(valid_calls)}")
    print(f"Valid PUTS with pricing: {len(valid_puts)}")
    
except Exception as e:
    print(f"Error: {e}")
