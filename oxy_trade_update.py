#!/usr/bin/env python3
"""
The Quant Oracle - LIVE TRADE UPDATE
Status check on all 3 OXY plays
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Original trade entries
TRADES = [
    {
        'id': 1,
        'name': 'GAMMA SCALP',
        'type': 'CALL',
        'strike': 58.0,
        'contracts': 2,
        'entry_price': 0.90,
        'entry_cost': 180.00,
        'target_1': 1.12,
        'target_2': 1.35,
        'stop': 0.59,
        'time_exit': '3:45 PM TODAY',
        'entry_time': '11:00 AM March 18'
    },
    {
        'id': 2,
        'name': 'DIRECTIONAL',
        'type': 'CALL',
        'strike': 57.0,
        'contracts': 1,
        'entry_price': 1.65,
        'entry_cost': 165.00,
        'target': 2.31,
        'stop': 1.24,
        'time_exit': 'Tomorrow 10 AM',
        'entry_time': '11:00 AM March 18'
    },
    {
        'id': 3,
        'name': 'CREDIT SPREAD',
        'type': 'SPREAD',
        'sell_strike': 56.0,
        'buy_strike': 55.0,
        'contracts': 1,
        'entry_credit': 0.01,
        'credit_received': 1.00,
        'collateral': 99.00,
        'max_profit': 1.00,
        'max_loss': 99.00,
        'time_exit': 'Friday Expiration',
        'entry_time': '11:00 AM March 18'
    }
]

# Get current market data
print(f"\n{'='*80}")
print(f"🎯 QUANT ORACLE - LIVE TRADE UPDATE")
print(f"{'='*80}\n")

oxy = yf.Ticker('OXY')

# Get current price
hist = oxy.history(period='1d', interval='1m')
if not hist.empty:
    current_price = hist['Close'].iloc[-1]
    current_time = hist.index[-1]
    day_high = hist['High'].max()
    day_low = hist['Low'].min()
else:
    hist = oxy.history(period='1d')
    current_price = hist['Close'].iloc[-1]
    current_time = datetime.now()
    day_high = hist['High'].iloc[-1]
    day_low = hist['Low'].iloc[-1]

# Time elapsed since entry (assuming 11am entry)
if hasattr(current_time, 'tz'):
    from datetime import timezone
    import pytz
    entry_time = datetime(2026, 3, 18, 11, 0, tzinfo=pytz.timezone('US/Eastern'))
else:
    entry_time = datetime(2026, 3, 18, 11, 0)

try:
    hours_elapsed = (current_time - entry_time).total_seconds() / 3600
except:
    hours_elapsed = (datetime.now() - datetime(2026, 3, 18, 11, 0)).total_seconds() / 3600

print(f"⏰ CURRENT TIME: {current_time}")
print(f"📊 OXY PRICE: ${current_price:.2f}")
print(f"📈 TODAY'S RANGE: ${day_low:.2f} - ${day_high:.2f}")
print(f"⏱️  HOURS SINCE ENTRY: {hours_elapsed:.1f} hours")

# Get options chain
exp_date = '2026-03-20'
chain = oxy.option_chain(exp_date)
calls = chain.calls
puts = chain.puts

# Calculate time remaining
exp_datetime = datetime.strptime(exp_date, '%Y-%m-%d')
T = (exp_datetime - datetime.now()).total_seconds() / (365.25 * 24 * 3600)
hours_remaining = T * 365.25 * 24

print(f"⏰ TIME TO EXPIRATION: {hours_remaining:.1f} hours ({T*365.25:.2f} days)")
print(f"\n{'='*80}\n")

# Helper function for Greeks
def calc_greeks(S, K, T, r, sigma, opt_type='call'):
    if T <= 0 or sigma <= 0:
        return 0, 0, 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    delta = norm.cdf(d1) if opt_type == 'call' else -norm.cdf(-d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) 
            - r * K * np.exp(-r * T) * (norm.cdf(d2) if opt_type == 'call' else norm.cdf(-d2))) / 365
    return delta, gamma, theta

# ============================================================================
# PLAY #1 UPDATE
# ============================================================================
print(f"\n{'#'*80}")
print(f"🎯 PLAY #1: GAMMA SCALP - LIVE UPDATE")
print(f"{'#'*80}\n")

trade1 = TRADES[0]
call_58 = calls[calls['strike'] == trade1['strike']].iloc[0]

# Get current pricing
if call_58['bid'] > 0 and call_58['ask'] > 0:
    current_price_1 = (call_58['bid'] + call_58['ask']) / 2
    bid_1 = call_58['bid']
    ask_1 = call_58['ask']
else:
    current_price_1 = call_58['lastPrice']
    bid_1 = current_price_1 * 0.95
    ask_1 = current_price_1 * 1.05

iv_1 = call_58['impliedVolatility'] if call_58['impliedVolatility'] > 0.01 else 0.35

# Calculate P&L
entry_value_1 = trade1['entry_cost']
current_value_1 = current_price_1 * 100 * trade1['contracts']
pnl_1 = current_value_1 - entry_value_1
pnl_pct_1 = (pnl_1 / entry_value_1) * 100

# Greeks
delta_1, gamma_1, theta_1 = calc_greeks(current_price, trade1['strike'], T, 0.045, iv_1, 'call')

print(f"📊 POSITION STATUS:")
print(f"   Entry: {trade1['contracts']} x CALL ${trade1['strike']} @ ${trade1['entry_price']:.2f}")
print(f"   Entry Cost: ${entry_value_1:.2f}")
print(f"   Entry Time: {trade1['entry_time']}")
print(f"   Time Held: {hours_elapsed:.1f} hours")

print(f"\n💰 CURRENT VALUATION:")
print(f"   Current Bid/Ask: ${bid_1:.2f} / ${ask_1:.2f}")
print(f"   Current Mid: ${current_price_1:.2f}")
print(f"   Current Value: ${current_value_1:.2f}")
print(f"   P&L: ${pnl_1:+.2f} ({pnl_pct_1:+.2f}%)")

# Status indicator
if current_price_1 >= trade1['target_2']:
    status_1 = "🟢 TARGET 2 HIT - SELL ALL NOW!"
    action_1 = "IMMEDIATE SELL"
elif current_price_1 >= trade1['target_1']:
    status_1 = "🟢 TARGET 1 HIT - SELL 50%"
    action_1 = "SELL 1 CONTRACT, TRAIL STOP OTHER"
elif pnl_pct_1 > 10:
    status_1 = "🟢 PROFITABLE - Monitor closely"
    action_1 = "HOLD, watch for $1.12"
elif pnl_pct_1 > -10:
    status_1 = "🟡 NEAR BREAK-EVEN"
    action_1 = "HOLD, monitor support at $58"
elif current_price_1 <= trade1['stop']:
    status_1 = "🔴 STOP LOSS HIT - EXIT NOW"
    action_1 = "IMMEDIATE SELL - STOP TRIGGERED"
else:
    status_1 = "🟡 UNDERWATER - Watch stop"
    action_1 = "MONITOR, exit if OXY breaks $57.70"

print(f"\n🎯 STATUS: {status_1}")
print(f"   Recommended Action: {action_1}")

print(f"\n📊 TARGET CHECK:")
if current_price_1 >= trade1['target_1']:
    print(f"   Target 1 ($1.12): ✅ HIT")
else:
    print(f"   Target 1 ($1.12): ${trade1['target_1'] - current_price_1:.2f} away")
if current_price_1 >= trade1['target_2']:
    print(f"   Target 2 ($1.35): ✅ HIT")
else:
    print(f"   Target 2 ($1.35): ${trade1['target_2'] - current_price_1:.2f} away")
if current_price_1 <= trade1['stop']:
    print(f"   Stop ($0.59): 🔴 TRIGGERED")
else:
    print(f"   Stop ($0.59): ${current_price_1 - trade1['stop']:.2f} cushion")

print(f"\n⚡ CURRENT GREEKS:")
print(f"   Delta: {delta_1:.4f} (was 0.6025 at entry)")
print(f"   Gamma: {gamma_1:.6f} (was 0.3095 at entry)")
print(f"   Theta: ${theta_1:.4f}/day (theta burn accelerating)")
print(f"   Hourly Theta Cost: ${abs(theta_1)/24:.4f}")

print(f"\n⏰ TIME MANAGEMENT:")
print(f"   Time Exit Deadline: {trade1['time_exit']}")
print(f"   Hours Remaining to Deadline: {15.75 - hours_elapsed:.1f} hours")
if hours_elapsed >= 4.75:
    print(f"   ⚠️  APPROACHING TIME LIMIT - Consider exit")
else:
    print(f"   ✅ Still within acceptable hold time")

theta_cost = abs(theta_1) * (hours_elapsed / 24)
print(f"\n💸 THETA DECAY ANALYSIS:")
print(f"   Theta cost so far: ${theta_cost:.4f}")
print(f"   Remaining theta risk: ${abs(theta_1) * ((15.75 - hours_elapsed) / 24):.4f}")

print(f"\n🎯 QUANT ORACLE RECOMMENDATION:")
if current_price_1 >= trade1['target_2']:
    print(f"   🔥 SELL ALL 2 CONTRACTS IMMEDIATELY at ${current_price_1:.2f}")
    print(f"   Profit: ${pnl_1:+.2f} ({pnl_pct_1:+.2f}%)")
    print(f"   This is your TARGET 2 - TAKE THE MONEY!")
elif current_price_1 >= trade1['target_1']:
    print(f"   ✅ SELL 1 CONTRACT at ${current_price_1:.2f}")
    print(f"   Lock in ${(current_price_1 - trade1['entry_price']) * 100:.2f} profit")
    print(f"   Set trailing stop on remaining contract at ${trade1['entry_price'] * 1.15:.2f}")
elif current_price_1 <= trade1['stop']:
    print(f"   🛑 STOP LOSS TRIGGERED - EXIT ALL NOW")
    print(f"   Sell at market, accept loss of ${abs(pnl_1):.2f}")
    print(f"   Protect remaining capital for other trades")
elif hours_elapsed >= 4.5:
    print(f"   ⏰ APPROACHING TIME LIMIT")
    print(f"   Exit by 3:45 PM regardless of P&L")
    print(f"   Current P&L: {pnl_pct_1:+.2f}%")
else:
    print(f"   📊 HOLD for now, but monitor closely")
    print(f"   Watch for OXY move to $58.50 (target 1)")
    print(f"   Exit if OXY drops to $57.70 (stop)")

print(f"\n{'#'*80}\n")

# ============================================================================
# PLAY #2 UPDATE
# ============================================================================
print(f"\n{'#'*80}")
print(f"🎯 PLAY #2: DIRECTIONAL - LIVE UPDATE")
print(f"{'#'*80}\n")

trade2 = TRADES[1]
call_57 = calls[calls['strike'] == trade2['strike']].iloc[0]

if call_57['bid'] > 0 and call_57['ask'] > 0:
    current_price_2 = (call_57['bid'] + call_57['ask']) / 2
    bid_2 = call_57['bid']
    ask_2 = call_57['ask']
else:
    current_price_2 = call_57['lastPrice']
    bid_2 = current_price_2 * 0.95
    ask_2 = current_price_2 * 1.05

iv_2 = call_57['impliedVolatility'] if call_57['impliedVolatility'] > 0.01 else 0.35

entry_value_2 = trade2['entry_cost']
current_value_2 = current_price_2 * 100 * trade2['contracts']
pnl_2 = current_value_2 - entry_value_2
pnl_pct_2 = (pnl_2 / entry_value_2) * 100

delta_2, gamma_2, theta_2 = calc_greeks(current_price, trade2['strike'], T, 0.045, iv_2, 'call')

print(f"📊 POSITION STATUS:")
print(f"   Entry: {trade2['contracts']} x CALL ${trade2['strike']} @ ${trade2['entry_price']:.2f}")
print(f"   Entry Cost: ${entry_value_2:.2f}")
print(f"   Time Held: {hours_elapsed:.1f} hours")

print(f"\n💰 CURRENT VALUATION:")
print(f"   Current Bid/Ask: ${bid_2:.2f} / ${ask_2:.2f}")
print(f"   Current Mid: ${current_price_2:.2f}")
print(f"   Current Value: ${current_value_2:.2f}")
print(f"   P&L: ${pnl_2:+.2f} ({pnl_pct_2:+.2f}%)")

if current_price_2 >= trade2['target']:
    status_2 = "🟢 TARGET HIT - SELL NOW!"
    action_2 = "IMMEDIATE SELL"
elif pnl_pct_2 > 20:
    status_2 = "🟢 STRONG PROFIT"
    action_2 = "Consider taking profit or trailing stop"
elif pnl_pct_2 > 0:
    status_2 = "🟢 PROFITABLE"
    action_2 = "HOLD, watch for $59 target"
elif current_price_2 <= trade2['stop']:
    status_2 = "🔴 STOP LOSS HIT"
    action_2 = "EXIT NOW"
else:
    status_2 = "🟡 MONITORING"
    action_2 = "Watch support at $57.50"

print(f"\n🎯 STATUS: {status_2}")
print(f"   Recommended Action: {action_2}")

print(f"\n📊 TARGET CHECK:")
if current_price_2 >= trade2['target']:
    print(f"   Target ($2.31): ✅ HIT")
else:
    print(f"   Target ($2.31): ${trade2['target'] - current_price_2:.2f} away")
if current_price_2 <= trade2['stop']:
    print(f"   Stop ($1.24): 🔴 TRIGGERED")
else:
    print(f"   Stop ($1.24): ${current_price_2 - trade2['stop']:.2f} cushion")
print(f"   OXY needs to reach: $59.00 for target")

print(f"\n⚡ CURRENT GREEKS:")
print(f"   Delta: {delta_2:.4f} (was 0.8249 at entry)")
print(f"   Gamma: {gamma_2:.6f}")
print(f"   Theta: ${theta_2:.4f}/day")

print(f"\n⏰ TIME MANAGEMENT:")
print(f"   This trade CAN hold overnight")
print(f"   Max hold until: Tomorrow 10 AM")
print(f"   Overnight theta cost: ~${abs(theta_2):.2f}")

print(f"\n🎯 QUANT ORACLE RECOMMENDATION:")
if current_price_2 >= trade2['target']:
    print(f"   🔥 TARGET HIT - SELL NOW at ${current_price_2:.2f}")
    print(f"   Profit: ${pnl_2:+.2f} ({pnl_pct_2:+.2f}%)")
elif pnl_pct_2 > 25:
    print(f"   ✅ TAKE PROFITS - Close position")
    print(f"   You're at {pnl_pct_2:+.1f}%, very close to 40% target")
elif current_price_2 <= trade2['stop']:
    print(f"   🛑 STOP TRIGGERED - Exit now")
else:
    print(f"   📊 Can hold overnight if needed")
    print(f"   Watch for OXY move to $59.00")
    print(f"   Exit tomorrow 10 AM if target not hit")

print(f"\n{'#'*80}\n")

# ============================================================================
# PLAY #3 UPDATE
# ============================================================================
print(f"\n{'#'*80}")
print(f"🎯 PLAY #3: CREDIT SPREAD - LIVE UPDATE")
print(f"{'#'*80}\n")

trade3 = TRADES[2]
put_56 = puts[puts['strike'] == trade3['sell_strike']].iloc[0]
put_55 = puts[puts['strike'] == trade3['buy_strike']].iloc[0]

# Current spread value
sell_current = (put_56['bid'] + put_56['ask']) / 2 if put_56['bid'] > 0 else put_56['lastPrice']
buy_current = (put_55['bid'] + put_55['ask']) / 2 if put_55['bid'] > 0 else put_55['lastPrice']
spread_value = sell_current - buy_current

# P&L (remember: we SOLD the spread, so we want it to decrease)
entry_credit = trade3['entry_credit']
pnl_3 = (entry_credit - spread_value) * 100 * trade3['contracts']
pnl_pct_3 = (pnl_3 / trade3['collateral']) * 100

print(f"📊 POSITION STATUS:")
print(f"   SHORT {trade3['contracts']} x PUT ${trade3['sell_strike']}")
print(f"   LONG {trade3['contracts']} x PUT ${trade3['buy_strike']}")
print(f"   Entry Credit: ${entry_credit:.2f} per spread (${trade3['credit_received']:.2f} total)")
print(f"   Collateral: ${trade3['collateral']:.2f}")

print(f"\n💰 CURRENT VALUATION:")
print(f"   Sell PUT $56: ${sell_current:.2f}")
print(f"   Buy PUT $55: ${buy_current:.2f}")
print(f"   Spread Value: ${spread_value:.2f}")
print(f"   P&L: ${pnl_3:+.2f} ({pnl_pct_3:+.2f}% on collateral)")

# Distance from danger
distance_from_sell = current_price - trade3['sell_strike']
distance_pct = (distance_from_sell / current_price) * 100

if current_price > trade3['sell_strike'] + 1:
    status_3 = "🟢 SAFE ZONE - Well above strikes"
    action_3 = "HOLD to expiration"
elif current_price > trade3['sell_strike']:
    status_3 = "🟢 PROFIT ZONE - Above sell strike"
    action_3 = "HOLD, let theta work"
elif current_price > trade3['buy_strike']:
    status_3 = "🟡 RISK ZONE - Between strikes"
    action_3 = "MONITOR closely, consider exit"
else:
    status_3 = "🔴 MAX LOSS ZONE"
    action_3 = "EXIT NOW if not already"

print(f"\n🎯 STATUS: {status_3}")
print(f"   Recommended Action: {action_3}")

print(f"\n📊 PRICE LEVELS:")
print(f"   Current OXY: ${current_price:.2f}")
print(f"   Sell Strike $56: ${distance_from_sell:+.2f} away ({distance_pct:+.1f}%)")
print(f"   Buy Strike $55: ${current_price - trade3['buy_strike']:+.2f} away")
print(f"   Safety Cushion: {distance_pct:.1f}% above short strike")

print(f"\n⏰ TIME DECAY (Working FOR You):")
print(f"   Time to Expiration: {hours_remaining:.1f} hours")
print(f"   Theta working in your favor")
print(f"   Every hour = more decay on short put")

print(f"\n💰 PROFIT SCENARIOS:")
print(f"   Current P&L: ${pnl_3:+.2f}")
print(f"   Max Profit: ${trade3['max_profit']:.2f} (if OXY > $56 at exp)")
print(f"   Max Loss: ${trade3['max_loss']:.2f} (if OXY < $55 at exp)")
print(f"   Profit Progress: {(pnl_3 / trade3['max_profit'] * 100):.1f}% of max")

print(f"\n🎯 QUANT ORACLE RECOMMENDATION:")
if spread_value <= entry_credit * 0.5:
    print(f"   ✅ 50% PROFIT ACHIEVED - Can close for profit")
    print(f"   Buy back spread at ${spread_value:.2f}")
elif current_price > trade3['sell_strike'] + 1:
    print(f"   🟢 HOLD TO EXPIRATION")
    print(f"   OXY is {distance_pct:.1f}% above danger zone")
    print(f"   Let theta continue working for you")
    print(f"   Max profit if OXY stays above $56")
elif current_price < trade3['sell_strike']:
    print(f"   ⚠️  OXY BELOW SELL STRIKE")
    print(f"   Consider closing to limit losses")
    print(f"   Current loss: ${abs(pnl_3):.2f}")
else:
    print(f"   📊 HOLD - Still in profit zone")
    print(f"   Monitor if OXY approaches $56")

print(f"\n{'#'*80}\n")

# ============================================================================
# PORTFOLIO SUMMARY
# ============================================================================
total_pnl = pnl_1 + pnl_2 + pnl_3
total_investment = entry_value_1 + entry_value_2 + trade3['collateral']
total_pnl_pct = (total_pnl / total_investment) * 100

print(f"\n{'='*80}")
print(f"💰 PORTFOLIO SUMMARY")
print(f"{'='*80}\n")

print(f"📊 INDIVIDUAL P&L:")
print(f"   Play #1 (Gamma Scalp):  ${pnl_1:+8.2f} ({pnl_pct_1:+6.2f}%)")
print(f"   Play #2 (Directional):  ${pnl_2:+8.2f} ({pnl_pct_2:+6.2f}%)")
print(f"   Play #3 (Credit Spread): ${pnl_3:+8.2f} ({pnl_pct_3:+6.2f}%)")
print(f"   {'─'*50}")
print(f"   TOTAL P&L:              ${total_pnl:+8.2f} ({total_pnl_pct:+6.2f}%)")

print(f"\n💰 CAPITAL SUMMARY:")
print(f"   Total Invested: ${total_investment:.2f}")
print(f"   Current Value: ${total_investment + total_pnl:.2f}")
print(f"   Cash Reserve: $56.00")
print(f"   Total Account: ${total_investment + total_pnl + 56:.2f}")

print(f"\n🎯 RECOMMENDED ACTIONS:")
actions = []
if current_price_1 >= trade1['target_1']:
    actions.append("✅ PLAY #1: SELL 1 CONTRACT NOW (target 1 hit)")
elif current_price_1 <= trade1['stop']:
    actions.append("🔴 PLAY #1: EXIT ALL (stop triggered)")
else:
    actions.append(f"📊 PLAY #1: Monitor (current: ${pnl_1:+.2f})")

if current_price_2 >= trade2['target']:
    actions.append("✅ PLAY #2: SELL NOW (target hit)")
elif current_price_2 <= trade2['stop']:
    actions.append("🔴 PLAY #2: EXIT NOW (stop hit)")
else:
    actions.append(f"📊 PLAY #2: Hold overnight OK (current: ${pnl_2:+.2f})")

if current_price > trade3['sell_strike'] + 1:
    actions.append("✅ PLAY #3: Hold to expiration (safe zone)")
else:
    actions.append(f"⚠️  PLAY #3: Monitor OXY vs $56 (current cushion: ${distance_from_sell:.2f})")

for action in actions:
    print(f"   {action}")

print(f"\n⏰ TIME-CRITICAL DEADLINES:")
print(f"   Play #1: {15.75 - hours_elapsed:.1f} hours until 3:45 PM exit")
print(f"   Play #2: ~23 hours until tomorrow 10 AM exit")
print(f"   Play #3: {hours_remaining:.1f} hours until Friday expiration")

print(f"\n{'='*80}")
print(f"✅ UPDATE COMPLETE - The Greeks have spoken.")
print(f"{'='*80}\n")

# Save update
update_data = {
    'update_time': current_time,
    'hours_elapsed': hours_elapsed,
    'oxy_price': current_price,
    'play1_price': current_price_1,
    'play1_pnl': pnl_1,
    'play1_pnl_pct': pnl_pct_1,
    'play2_price': current_price_2,
    'play2_pnl': pnl_2,
    'play2_pnl_pct': pnl_pct_2,
    'play3_spread': spread_value,
    'play3_pnl': pnl_3,
    'play3_pnl_pct': pnl_pct_3,
    'total_pnl': total_pnl,
    'total_pnl_pct': total_pnl_pct
}

pd.DataFrame([update_data]).to_csv('oxy_trade_update.csv', index=False)
print(f"💾 Update saved to: oxy_trade_update.csv\n")
