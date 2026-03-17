#!/usr/bin/env python3
"""
The Quant Oracle - Refined OXY Options Analysis
Focusing on AT-THE-MONEY trades with actual edge and gamma exposure
"""

import pandas as pd
import numpy as np

# Read the full analysis
df = pd.read_csv('oxy_full_analysis.csv')

print("\n" + "="*80)
print("🎯 QUANT ORACLE - REFINED ANALYSIS FOR OXY MARCH 20TH, 2026")
print("="*80)
print("\n📊 Current OXY Price: $57.41")
print("📅 Expiration: March 20, 2026 (2 Days | 0.0055 years)")
print("⚡ Analysis Focus: AT-THE-MONEY options with HIGH GAMMA exposure")
print("\n" + "="*80 + "\n")

# Filter for ATM options (strikes between $56-$59)
atm_options = df[(df['strike'] >= 56) & (df['strike'] <= 59)].copy()

# Score based on Quant Oracle criteria:
# 1. High Gamma (explosive move potential)
# 2. Reasonable liquidity (volume + OI)
# 3. Edge opportunity (theoretical vs market)
atm_options['liquidity_score'] = atm_options['volume'] + atm_options['open_interest'] * 0.5
atm_options['quant_score'] = (
    atm_options['gamma'] * 1000 +  # Gamma is key for 2-day plays
    abs(atm_options['edge_pct']) * 0.5 +  # Edge matters
    atm_options['liquidity_score'] * 0.01 +  # Liquidity
    abs(atm_options['delta'] - 0.5) * -10  # Prefer Delta near 0.5 (ATM)
)

# Get top 5 trades
top_5 = atm_options.nlargest(5, 'quant_score')

print("📋 TOP 5 OXY OPTIONS TRADES - MARCH 20TH EXPIRATION\n")
print("="*80)

for i, (idx, trade) in enumerate(top_5.iterrows(), 1):
    print(f"\n{'#'*80}")
    print(f"🎯 TRADE #{i}: {'LONG' if trade['gamma'] > 0.25 else 'THETA HARVEST'} {trade['type']} ${trade['strike']:.2f}")
    print(f"{'#'*80}\n")
    
    # Determine strategy based on Greeks
    if trade['strike'] == 57.5:
        strategy_type = "⚡ GAMMA EXPLOSION SETUP"
        battle_plan = "Maximum gamma exposure at the money"
    elif abs(trade['delta']) > 0.75:
        strategy_type = "📈 DIRECTIONAL MOMENTUM"
        battle_plan = "High delta with theta decay"
    elif trade['gamma'] > 0.25:
        strategy_type = "💥 GAMMA SCALP OPPORTUNITY"
        battle_plan = "Profit from volatility expansion"
    else:
        strategy_type = "⏱️ THETA HARVEST"
        battle_plan = "Collect premium decay"
    
    print(f"🎲 STRATEGY: {strategy_type}")
    print(f"📖 Battle Plan: {battle_plan}")
    
    print(f"\n💹 MARKET STRUCTURE:")
    print(f"   Strike: ${trade['strike']:.2f}")
    print(f"   Market Premium: ${trade['market_price']:.2f}")
    print(f"   BSM Theoretical: ${trade['theo_price']:.4f}")
    print(f"   Edge: {trade['edge_pct']:+.2f}% {'(Market Overpriced - SELL signal)' if trade['edge_pct'] < 0 else '(Market Underpriced - BUY signal)'}")
    print(f"   IV: {trade['iv']:.1f}%")
    print(f"   Volume: {trade['volume']:.0f} | OI: {trade['open_interest']:.0f}")
    
    print(f"\n⚡ THE GREEKS (The Physics of This Trade):")
    print(f"   Δ Delta = {trade['delta']:+.4f}")
    print(f"      → For every $1 move in OXY, this option moves ${abs(trade['delta']):.4f}")
    print(f"   Γ Gamma = {trade['gamma']:.6f}")
    print(f"      → Your delta changes by {trade['gamma']:.6f} per $1 move")
    print(f"      → {'🔥 EXPLOSIVE GAMMA - Max acceleration potential!' if trade['gamma'] > 0.28 else '⚡ Moderate gamma exposure'}")
    print(f"   ν Vega = ${trade['vega']:.4f}")
    print(f"      → 1% IV change = ${trade['vega']:.4f} P&L impact")
    print(f"   θ Theta = ${trade['theta']:.4f}/day")
    print(f"      → Daily time decay: ${abs(trade['theta']):.4f} per day")
    print(f"      → Over 2 days: ${abs(trade['theta']) * 2:.4f} total decay")
    
    print(f"\n📊 PROBABILITY METRICS (N(d₂) Analysis):")
    print(f"   ITM Probability: {trade['prob_itm']:.2f}%")
    print(f"   Moneyness: {trade['moneyness_pct']:+.2f}%")
    
    # Calculate break-even
    if trade['type'] == 'CALL':
        break_even = trade['strike'] + trade['market_price']
        pct_to_be = ((break_even - 57.41) / 57.41) * 100
    else:
        break_even = trade['strike'] - trade['market_price']
        pct_to_be = ((57.41 - break_even) / 57.41) * 100
    
    print(f"   Break-Even: ${break_even:.2f} ({pct_to_be:+.2f}% move needed)")
    
    print(f"\n🎯 TRADE EXECUTION PLAN:")
    
    # Determine recommended action
    if trade['edge_pct'] < -30 and abs(trade['delta']) < 0.3:
        # Overpriced + far from money = sell
        action = "SELL (SHORT)"
        print(f"   ✅ VERDICT: {action} - Market Premium >> Theoretical Value")
        print(f"   📍 Entry: Sell {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
        print(f"   💰 Max Profit: ${trade['market_price']:.2f} (if expires OTM)")
        print(f"   🛑 Risk: ${trade['strike'] if trade['type'] == 'PUT' else 'Unlimited'} (use stop or spread)")
        print(f"   🎯 Profit Target: Close at 50% profit (${trade['market_price'] * 0.5:.2f})")
        print(f"   ⏱️  Time Advantage: Theta works FOR you at ${abs(trade['theta']):.4f}/day")
    elif trade['gamma'] > 0.28:
        # Max gamma = buy for volatility play
        action = "BUY (LONG)"
        print(f"   ✅ VERDICT: {action} - MAXIMUM GAMMA EXPOSURE")
        print(f"   📍 Entry: Buy {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
        print(f"   💰 Max Profit: Unlimited {'upside' if trade['type'] == 'CALL' else 'to $' + str(trade['strike'])}")
        print(f"   🛑 Max Loss: ${trade['market_price']:.2f} (premium paid)")
        print(f"   🎯 Profit Target: 50-100% gain (${trade['market_price'] * 1.5:.2f} - ${trade['market_price'] * 2:.2f})")
        print(f"   ⚡ Gamma Play: Best for day-trading volatility spikes")
        print(f"   ⚠️  Time Risk: Theta costs you ${abs(trade['theta']):.4f}/day")
    elif abs(trade['delta']) > 0.75:
        # Deep ITM = directional
        action = "DIRECTIONAL PLAY"
        print(f"   ✅ VERDICT: {action} - Quasi-Stock Position")
        print(f"   📍 Entry: Buy {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
        print(f"   💰 Acts like owning/shorting stock with {abs(trade['delta'])*100:.1f}% exposure")
        print(f"   🛑 Stop Loss: Exit if OXY moves against you by $1.00")
        print(f"   🎯 Target: Ride the momentum or take profit at 50% gain")
    else:
        # Moderate setup
        action = "NEUTRAL - SCALP OPPORTUNITY"
        print(f"   ✅ VERDICT: {action}")
        print(f"   📍 Entry: Buy {trade['type']} ${trade['strike']:.2f} @ ${trade['market_price']:.2f}")
        print(f"   💰 Target: Quick 20-30% gain on volatility")
        print(f"   🛑 Stop: -40% of premium")
    
    print(f"\n⚠️  RISK WARNINGS:")
    if trade['slippage_risk'] == 'HIGH':
        print(f"   🔴 HIGH SLIPPAGE RISK: Bid-ask spread is {trade['spread_pct']:.1f}%")
    if abs(trade['theta']) > 0.50:
        print(f"   🔴 SEVERE THETA DECAY: Losing ${abs(trade['theta']):.2f} per day")
    if trade['gamma'] > 0.30:
        print(f"   ⚡ EXPLOSIVE GAMMA: Your delta can swing wildly - manage actively!")
    
    print(f"\n💡 QUANT ORACLE INSIGHT:")
    if trade['strike'] == 57.5:
        print(f"   This is THE MONEY STRIKE with maximum gamma. Perfect for:")
        print(f"   • Day-trading volatility expansions")
        print(f"   • Scalping quick moves in OXY")
        print(f"   • Gamma hedging strategies")
        print(f"   ⚠️  Not a hold-to-expiration trade - theta will crush it!")
    elif trade['edge_pct'] < -50:
        print(f"   Market is paying {abs(trade['edge_pct']):.1f}% OVER theoretical value.")
        print(f"   Classic short premium setup if you can manage the risk.")
    elif trade['gamma'] > 0.25:
        print(f"   High gamma = high sensitivity to price moves.")
        print(f"   Best for active traders who can monitor and adjust.")
    
    print(f"\n{'#'*80}\n")

print("\n" + "="*80)
print("📊 QUANT ORACLE SUMMARY - KEY INSIGHTS")
print("="*80)
print("""
🎯 BEST OVERALL TRADE: 
   The $57.50 strike (calls or puts) offers MAXIMUM GAMMA exposure.
   With OXY at $57.41, this is the epicenter of options action.
   
⚡ GAMMA EXPLOSION SETUP:
   Buy the $57.50 CALL or PUT for a volatility play
   • Massive gamma = explosive P&L on moves
   • Must day-trade or scalp - don't hold to expiration
   • Theta decay is brutal at -$0.13/day
   
🔥 THETA HARVEST SETUP:
   Sell the deep OTM puts ($46-47) or calls ($60+)
   • Collect pennies with 99%+ probability of profit
   • Use stops or convert to spreads for risk management
   
⏰ TIME CONSIDERATION:
   With only 2 days to expiration, these are NOT hold positions.
   Every option will decay rapidly. Trade accordingly.
   
📈 MARKET CONTEXT:
   OXY currently at $57.41. For profitable trades:
   • Calls need OXY > break-even
   • Puts need OXY < break-even
   • Gamma plays need MOVEMENT (direction matters less)

💰 INSTITUTIONAL FLOW ALERT:
   Per operational rules, check for $500k+ orders in OXY or SPX
   Align your delta with detected institutional flow for edge.
""")
print("="*80)
print("✅ QUANT ORACLE ANALYSIS COMPLETE")
print("="*80 + "\n")

# Save refined analysis
top_5.to_csv('oxy_top_5_refined.csv', index=False)
print("💾 Refined analysis saved to: oxy_top_5_refined.csv\n")
