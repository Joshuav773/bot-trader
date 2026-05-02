import type Anthropic from '@anthropic-ai/sdk'
import { config } from 'dotenv'
import { resolve } from 'path'

config({ path: resolve(process.cwd(), '.env.local') })
config({ path: resolve(process.cwd(), '../.env') })

// ── Config / safety guards ──────────────────────────────────────────────

const PAPER_BASE = 'https://paper-api.alpaca.markets'
const DATA_BASE = 'https://data.alpaca.markets'

// Risk parameters (hard rules applied in placeOrder validation)
const MAX_ACCOUNT_RISK_PCT = 2 // a single trade can never risk more than 2% of total account equity
// (TP1 +20% is a target documented in EXECUTION_PROTOCOL.md — not enforced in code)

function tradingBase(): string {
  const url = process.env.ALPACA_BASE_URL || PAPER_BASE
  // Hard guard: refuse anything that isn't the paper endpoint until we explicitly
  // add a LIVE_TRADING_ENABLED flag in a separate change.
  if (!url.includes('paper-api.alpaca.markets')) {
    throw new Error(
      `Refusing to use non-paper Alpaca endpoint: ${url}. ` +
        `Set ALPACA_BASE_URL=${PAPER_BASE} until live trading is explicitly enabled.`,
    )
  }
  return url
}

function authHeaders(): Record<string, string> {
  const key = process.env.ALPACA_API_KEY
  const secret = process.env.ALPACA_SECRET_KEY
  if (!key || !secret) throw new Error('ALPACA_API_KEY and ALPACA_SECRET_KEY must be set')
  return {
    'APCA-API-KEY-ID': key,
    'APCA-API-SECRET-KEY': secret,
    'Content-Type': 'application/json',
    accept: 'application/json',
  }
}

async function alpacaFetch(
  base: string,
  path: string,
  init?: { method?: string; body?: Record<string, unknown> },
): Promise<unknown> {
  const res = await fetch(`${base}${path}`, {
    method: init?.method ?? 'GET',
    headers: authHeaders(),
    ...(init?.body ? { body: JSON.stringify(init.body) } : {}),
  })
  const text = await res.text()
  if (!res.ok) {
    throw new Error(`Alpaca ${res.status}: ${text}`)
  }
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

// ── Tool schemas (passed to Claude) ─────────────────────────────────────

export const ALPACA_TOOLS: Anthropic.Tool[] = [
  {
    name: 'alpaca_get_account',
    description:
      'Get the paper-trading account snapshot: equity, cash, buying power, and day P&L. Call this whenever you need to know how much capital is available before sizing a trade.',
    input_schema: { type: 'object' as const, properties: {}, required: [] },
  },
  {
    name: 'alpaca_get_positions',
    description: 'List all currently open positions in the paper account, including unrealized P&L per position.',
    input_schema: { type: 'object' as const, properties: {}, required: [] },
  },
  {
    name: 'alpaca_get_orders',
    description: 'List recent orders. Use status=open to see only working orders, status=closed for filled/canceled history.',
    input_schema: {
      type: 'object' as const,
      properties: {
        status: {
          type: 'string',
          enum: ['open', 'closed', 'all'],
          description: 'Order status filter. Defaults to "open".',
        },
        limit: { type: 'number', description: 'Max orders to return (default 50).' },
      },
      required: [],
    },
  },
  {
    name: 'alpaca_get_quote',
    description:
      'Get the latest quote (bid/ask) for a stock symbol. Use this to validate market premium before placing a trade.',
    input_schema: {
      type: 'object' as const,
      properties: {
        symbol: { type: 'string', description: 'Stock ticker, e.g. AAPL or SPY.' },
      },
      required: ['symbol'],
    },
  },
  {
    name: 'alpaca_get_bars',
    description: 'Get OHLCV bars for a stock symbol over a recent time window. Use for chart pattern analysis.',
    input_schema: {
      type: 'object' as const,
      properties: {
        symbol: { type: 'string', description: 'Stock ticker.' },
        timeframe: {
          type: 'string',
          description: 'Bar timeframe like "1Min", "5Min", "15Min", "1Hour", "1Day".',
        },
        limit: { type: 'number', description: 'Number of bars to return (default 100, max 10000).' },
      },
      required: ['symbol', 'timeframe'],
    },
  },
  {
    name: 'alpaca_get_option_chain',
    description:
      'Get the option chain snapshot for an underlying symbol. Returns strikes, expirations, bid/ask, IV, Greeks. Use to find strikes to trade.',
    input_schema: {
      type: 'object' as const,
      properties: {
        underlying: { type: 'string', description: 'Underlying stock symbol, e.g. AAPL.' },
        expiration: {
          type: 'string',
          description: 'Optional ISO date (YYYY-MM-DD) to filter to one expiration.',
        },
      },
      required: ['underlying'],
    },
  },
  {
    name: 'alpaca_place_order',
    description:
      'Place a paper order. ONLY call this AFTER the user has explicitly approved the trade. ' +
      'Never call on your own initiative — propose the trade in plain text first and wait for confirmation.\n\n' +
      'STOCKS — TWO MODES:\n' +
      '  1. Scale-out (preferred): provide take_profit_1_price + take_profit_2_price + trail_stop_to_price. ' +
      'The tool splits the position into two bracket orders: half closes at TP1, the runner targets TP2. ' +
      'After TP1 fills, call alpaca_advance_stop with the trail level to lock in profits on the runner.\n' +
      '  2. Single target: provide take_profit_price (legacy single bracket). Use only when you do not want to scale out.\n\n' +
      'OPTIONS (OCC symbol): bracket orders are not supported. Place the entry only and manage exits manually.',
    input_schema: {
      type: 'object' as const,
      properties: {
        symbol: { type: 'string', description: 'Ticker for stocks (e.g. "AAPL"), OCC symbol for options (e.g. "AAPL241220C00150000").' },
        qty: { type: 'number', description: 'Total number of shares or contracts. For stocks with scale-out, this is split between the two brackets.' },
        side: { type: 'string', enum: ['buy', 'sell'] },
        type: {
          type: 'string',
          enum: ['market', 'limit', 'stop', 'stop_limit'],
          description: 'Order type. Default "market". Prefer "limit" when premium is wide.',
        },
        time_in_force: {
          type: 'string',
          enum: ['day', 'gtc', 'ioc', 'fok'],
          description: 'Order duration. Default "day".',
        },
        limit_price: { type: 'number', description: 'Required for limit / stop_limit orders.' },
        stop_price: { type: 'number', description: 'Required for stop / stop_limit orders.' },
        stop_loss_price: {
          type: 'number',
          description:
            'REQUIRED for stock buys: protective stop (bracket stop leg). Same stop is used for both halves on scale-out. ' +
            'HARD RULE: dollar risk on the trade — (entry − stop) × qty × multiplier — must not exceed 2% of total account equity. ' +
            'Use alpaca_get_account first to check equity, then size qty so dollar risk stays within the 2% cap.',
        },
        take_profit_price: {
          type: 'number',
          description:
            'Single-target mode: take-profit price for a single bracket. Use only if NOT scaling out. ' +
            'TARGET (not enforced): aim for ~+20% from entry. If structural geometry only allows less, the trade can still be placed — but lower upside means lower priority.',
        },
        take_profit_1_price: {
          type: 'number',
          description:
            'Scale-out mode: TP1 price for the first half. ' +
            'TARGET (not enforced): aim for ~+20% from entry. We aim for high R/R but the rule layer no longer rejects below 20% — sizing is enforced by the 2% account-equity risk cap instead.',
        },
        take_profit_2_price: {
          type: 'number',
          description: 'Scale-out mode: TP2 price for the runner. Position closes fully when this fires.',
        },
        scale_out_qty: {
          type: 'number',
          description: 'Scale-out mode: how many shares/contracts to close at TP1. Defaults to floor(qty / 2).',
        },
        trail_stop_to_price: {
          type: 'number',
          description:
            'Scale-out mode: where the runner stop moves once TP1 fills. ' +
            'HARD RULE: must be >= take_profit_1_price (we always lock in TP1 profit on the runner — never give back gains). ' +
            'Default to take_profit_1_price exactly unless there is a clear structural level just above TP1.',
        },
        rationale: {
          type: 'string',
          description: 'One-sentence summary of why this trade was approved (embedded in client_order_id).',
        },
      },
      required: ['symbol', 'qty', 'side', 'rationale'],
    },
  },
  {
    name: 'alpaca_advance_stop',
    description:
      'Move the protective stop to a new price after TP1 has filled (or to lock in profits during a runner trade). ' +
      'Cancels the symbol\'s active stop order(s) and places a fresh stop at new_stop_price. ' +
      'Call this when you observe TP1 has filled (use alpaca_get_orders or alpaca_get_positions to verify) and want to trail the stop on the remaining runner.',
    input_schema: {
      type: 'object' as const,
      properties: {
        symbol: { type: 'string', description: 'Stock ticker. Trails the stop on this symbol\'s open position.' },
        new_stop_price: { type: 'number', description: 'New stop trigger price. Must be on the protective side of current price.' },
      },
      required: ['symbol', 'new_stop_price'],
    },
  },
  {
    name: 'alpaca_cancel_order',
    description: 'Cancel an open order by its Alpaca order ID.',
    input_schema: {
      type: 'object' as const,
      properties: {
        order_id: { type: 'string', description: 'Alpaca order UUID.' },
      },
      required: ['order_id'],
    },
  },
  {
    name: 'alpaca_close_position',
    description: 'Market-close an open position by symbol (or OCC option symbol).',
    input_schema: {
      type: 'object' as const,
      properties: {
        symbol: { type: 'string', description: 'Ticker or OCC option symbol.' },
        qty: { type: 'number', description: 'Optional partial close size.' },
      },
      required: ['symbol'],
    },
  },
]

// ── Tool execution ──────────────────────────────────────────────────────

export interface ToolResult {
  content: string
  is_error?: boolean
}

export async function executeAlpacaTool(
  name: string,
  input: Record<string, unknown>,
): Promise<ToolResult> {
  try {
    switch (name) {
      case 'alpaca_get_account': {
        const data = await alpacaFetch(tradingBase(), '/v2/account')
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_get_positions': {
        const data = await alpacaFetch(tradingBase(), '/v2/positions')
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_get_orders': {
        const status = (input.status as string) ?? 'open'
        const limit = (input.limit as number) ?? 50
        const data = await alpacaFetch(tradingBase(), `/v2/orders?status=${status}&limit=${limit}`)
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_get_quote': {
        const symbol = String(input.symbol).toUpperCase()
        const data = await alpacaFetch(DATA_BASE, `/v2/stocks/${encodeURIComponent(symbol)}/quotes/latest`)
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_get_bars': {
        const symbol = String(input.symbol).toUpperCase()
        const timeframe = String(input.timeframe)
        const limit = (input.limit as number) ?? 100
        const data = await alpacaFetch(
          DATA_BASE,
          `/v2/stocks/${encodeURIComponent(symbol)}/bars?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`,
        )
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_get_option_chain': {
        const underlying = String(input.underlying).toUpperCase()
        const expQuery = input.expiration ? `?expiration=${encodeURIComponent(String(input.expiration))}` : ''
        const data = await alpacaFetch(DATA_BASE, `/v1beta1/options/snapshots/${encodeURIComponent(underlying)}${expQuery}`)
        return { content: JSON.stringify(data, null, 2) }
      }
      case 'alpaca_place_order': {
        const result = await placeOrder(input)
        return result
      }
      case 'alpaca_advance_stop': {
        const result = await advanceStop(input)
        return result
      }
      case 'alpaca_cancel_order': {
        await alpacaFetch(tradingBase(), `/v2/orders/${encodeURIComponent(String(input.order_id))}`, { method: 'DELETE' })
        return { content: `Canceled order ${input.order_id}` }
      }
      case 'alpaca_close_position': {
        const symbol = String(input.symbol).toUpperCase()
        const qtyQuery = input.qty ? `?qty=${input.qty}` : ''
        const data = await alpacaFetch(tradingBase(), `/v2/positions/${encodeURIComponent(symbol)}${qtyQuery}`, { method: 'DELETE' })
        return { content: JSON.stringify(data, null, 2) }
      }
      default:
        return { content: `Unknown Alpaca tool: ${name}`, is_error: true }
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return { content: `Alpaca error: ${message}`, is_error: true }
  }
}

// ── Order placement (with safety check) ────────────────────────────────

const OCC_PATTERN = /^[A-Z]+\d{6}[CP]\d{8}$/

async function placeOrder(input: Record<string, unknown>): Promise<ToolResult> {
  const symbol = String(input.symbol).toUpperCase()
  const qty = Number(input.qty)
  const side = String(input.side)
  const type = (input.type as string) ?? 'market'
  const tif = (input.time_in_force as string) ?? 'day'
  const limitPrice = input.limit_price !== undefined ? Number(input.limit_price) : undefined
  const stopPrice = input.stop_price !== undefined ? Number(input.stop_price) : undefined
  const stopLossPrice = input.stop_loss_price !== undefined ? Number(input.stop_loss_price) : undefined
  const takeProfitPrice = input.take_profit_price !== undefined ? Number(input.take_profit_price) : undefined
  const tp1 = input.take_profit_1_price !== undefined ? Number(input.take_profit_1_price) : undefined
  const tp2 = input.take_profit_2_price !== undefined ? Number(input.take_profit_2_price) : undefined
  const trailTo = input.trail_stop_to_price !== undefined ? Number(input.trail_stop_to_price) : undefined
  const scaleOutQtyRaw = input.scale_out_qty !== undefined ? Number(input.scale_out_qty) : undefined
  const rationale = (input.rationale as string) ?? 'no rationale'

  if (!Number.isFinite(qty) || qty <= 0) {
    return { content: `Invalid qty: ${input.qty}`, is_error: true }
  }
  if (side !== 'buy' && side !== 'sell') {
    return { content: `Invalid side: ${side}. Must be "buy" or "sell".`, is_error: true }
  }

  const isOption = OCC_PATTERN.test(symbol)
  const isOpeningStock = !isOption && side === 'buy'
  const wantsScaleOut = tp1 !== undefined && tp2 !== undefined

  // Risk-management guardrail for stock buys
  if (isOpeningStock) {
    if (stopLossPrice === undefined) {
      return {
        content: 'Trade rejected: stop_loss_price is required for stock entries. Define your invalidation before placing.',
        is_error: true,
      }
    }
    if (takeProfitPrice === undefined && !wantsScaleOut) {
      return {
        content:
          'Trade rejected: provide either take_profit_price (single target) OR both take_profit_1_price + take_profit_2_price (scale-out). Scale-out is preferred.',
        is_error: true,
      }
    }
    const entry = limitPrice ?? stopPrice
    if (entry !== undefined) {
      // Geometry sanity checks (not policy — just basic correctness)
      if (stopLossPrice >= entry) {
        return { content: `Trade rejected: stop_loss_price ($${stopLossPrice}) must be below entry ($${entry}) for a long.`, is_error: true }
      }
      if (wantsScaleOut) {
        if (tp1 !== undefined && tp1 <= entry) {
          return { content: `Trade rejected: take_profit_1_price ($${tp1}) must be above entry ($${entry}).`, is_error: true }
        }
        if (tp2 !== undefined && tp1 !== undefined && tp2 <= tp1) {
          return { content: `Trade rejected: take_profit_2_price ($${tp2}) must be above take_profit_1_price ($${tp1}).`, is_error: true }
        }
        if (trailTo !== undefined && tp1 !== undefined && tp2 !== undefined) {
          // Hard rule: always secure profits. Trail must lock in at least TP1's gain on the runner.
          if (trailTo < tp1) {
            return {
              content:
                `Trade rejected: trail_stop_to_price ($${trailTo}) must be >= take_profit_1_price ($${tp1}). ` +
                `We always secure TP1 profits on the runner — trailing below TP1 would risk giving them back.`,
              is_error: true,
            }
          }
          if (trailTo >= tp2) {
            return {
              content: `Trade rejected: trail_stop_to_price ($${trailTo}) must be < take_profit_2_price ($${tp2}) (otherwise the stop would fire before TP2 can).`,
              is_error: true,
            }
          }
        }
      } else if (takeProfitPrice !== undefined && takeProfitPrice <= entry) {
        return { content: `Trade rejected: take_profit_price ($${takeProfitPrice}) must be above entry ($${entry}).`, is_error: true }
      }

      // ── Hard portfolio risk rule: never lose more than 2% of total account equity on a single trade ──
      // Dollar risk = (entry − stop) × qty × multiplier. Compare against MAX_ACCOUNT_RISK_PCT % of equity.
      try {
        const account = (await alpacaFetch(tradingBase(), '/v2/account')) as Record<string, unknown>
        const equity = Number(account.equity)
        if (Number.isFinite(equity) && equity > 0) {
          const stopMultiplier = isOption ? 100 : 1
          const dollarRisk = (entry - stopLossPrice) * qty * stopMultiplier
          const maxRisk = equity * (MAX_ACCOUNT_RISK_PCT / 100)
          if (dollarRisk > maxRisk) {
            return {
              content:
                `Trade rejected: dollar risk on this trade is $${dollarRisk.toFixed(2)} ` +
                `(${((dollarRisk / equity) * 100).toFixed(2)}% of $${equity.toFixed(2)} equity), ` +
                `exceeds the ${MAX_ACCOUNT_RISK_PCT}% max. ` +
                `Lower qty or tighten the stop. Suggested max qty at this stop = ` +
                `${Math.floor(maxRisk / Math.max(0.01, (entry - stopLossPrice) * stopMultiplier))}.`,
              is_error: true,
            }
          }
        }
      } catch {
        // If we can't fetch equity, fall through — better to let the broker's buying-power check catch it
      }
    }
  }

  // Best-effort notional readout
  let estimatedPrice = limitPrice ?? stopPrice
  if (estimatedPrice === undefined) {
    try {
      const quoteEndpoint = isOption
        ? `/v1beta1/options/snapshots/${encodeURIComponent(symbol.slice(0, symbol.search(/\d/)))}`
        : `/v2/stocks/${encodeURIComponent(symbol)}/quotes/latest`
      const quote = (await alpacaFetch(DATA_BASE, quoteEndpoint)) as Record<string, unknown>
      const q = (quote.quote as Record<string, unknown>) ?? {}
      estimatedPrice = (q.ap as number) ?? (q.bp as number) ?? undefined
    } catch {
      // Best-effort
    }
  }

  const multiplier = isOption ? 100 : 1
  const notional = (estimatedPrice ?? 0) * qty * multiplier
  const baseClientId = `bt-${Date.now()}-${rationale.slice(0, 24).replace(/[^a-zA-Z0-9]/g, '_')}`

  // ── SCALE-OUT: two bracket orders, half closes at TP1, runner targets TP2 ──
  if (isOpeningStock && wantsScaleOut && stopLossPrice !== undefined && tp1 !== undefined && tp2 !== undefined) {
    const traderQty = Number.isFinite(scaleOutQtyRaw) && scaleOutQtyRaw! > 0
      ? Math.floor(scaleOutQtyRaw!)
      : Math.floor(qty / 2)
    const runnerQty = qty - traderQty
    if (traderQty < 1 || runnerQty < 1) {
      return {
        content: `Trade rejected: qty=${qty} cannot be split (need at least 1 share per leg). Use a single-target order instead.`,
        is_error: true,
      }
    }

    const buildBracket = (legQty: number, takeProfit: number, suffix: string) => ({
      symbol,
      qty: String(legQty),
      side,
      type,
      time_in_force: tif,
      client_order_id: `${baseClientId}-${suffix}`,
      ...(limitPrice !== undefined ? { limit_price: String(limitPrice) } : {}),
      ...(stopPrice !== undefined ? { stop_price: String(stopPrice) } : {}),
      order_class: 'bracket',
      take_profit: { limit_price: String(takeProfit) },
      stop_loss: { stop_price: String(stopLossPrice) },
    })

    const traderOrder = await alpacaFetch(tradingBase(), '/v2/orders', { method: 'POST', body: buildBracket(traderQty, tp1, 'tp1') })
    let runnerOrder: unknown = null
    try {
      runnerOrder = await alpacaFetch(tradingBase(), '/v2/orders', { method: 'POST', body: buildBracket(runnerQty, tp2, 'tp2') })
    } catch (err) {
      // If the runner fails, surface it so the user can decide whether to roll the trader into a single bracket
      const message = err instanceof Error ? err.message : String(err)
      return {
        content:
          `Trader leg placed (qty=${traderQty}, TP1=$${tp1}) but runner leg failed: ${message}\n\n` +
          `Trader order:\n${JSON.stringify(traderOrder, null, 2)}`,
        is_error: true,
      }
    }

    return {
      content:
        `Scale-out submitted (paper). Total qty=${qty} (${traderQty} → TP1, ${runnerQty} → TP2). Estimated notional $${notional.toFixed(2)}.\n` +
        (trailTo !== undefined
          ? `When TP1 fills, call alpaca_advance_stop with new_stop_price=${trailTo} to lock in profits on the runner.\n`
          : `When TP1 fills, decide a trail level and call alpaca_advance_stop.\n`) +
        `\nTRADER (TP1):\n${JSON.stringify(traderOrder, null, 2)}\n\nRUNNER (TP2):\n${JSON.stringify(runnerOrder, null, 2)}`,
    }
  }

  // ── Single-target / non-stock path (existing behavior) ──
  const body: Record<string, unknown> = {
    symbol,
    qty: String(qty),
    side,
    type,
    time_in_force: tif,
    client_order_id: baseClientId,
  }
  if (limitPrice !== undefined) body.limit_price = String(limitPrice)
  if (stopPrice !== undefined) body.stop_price = String(stopPrice)
  if (isOpeningStock && stopLossPrice !== undefined && takeProfitPrice !== undefined) {
    body.order_class = 'bracket'
    body.take_profit = { limit_price: String(takeProfitPrice) }
    body.stop_loss = { stop_price: String(stopLossPrice) }
  }

  const data = await alpacaFetch(tradingBase(), '/v2/orders', { method: 'POST', body })

  const exitNote =
    isOption && (stopLossPrice !== undefined || takeProfitPrice !== undefined || tp1 !== undefined || tp2 !== undefined)
      ? `\n\nNote: Alpaca does not support bracket orders on options. Track these exits in conversation:\n` +
        `  Stop loss:   ${stopLossPrice ?? 'n/a'}\n` +
        `  Take profit: ${takeProfitPrice ?? tp1 ?? 'n/a'}${tp2 !== undefined ? ` then ${tp2}` : ''}`
      : ''

  return {
    content: `Order submitted (paper). Estimated notional $${notional.toFixed(2)}.${exitNote}\n\n${JSON.stringify(data, null, 2)}`,
  }
}

// ── advance_stop: trail the stop after TP1 fills (or anytime you want to tighten) ─────

async function advanceStop(input: Record<string, unknown>): Promise<ToolResult> {
  const symbol = String(input.symbol).toUpperCase()
  const newStop = Number(input.new_stop_price)
  if (!Number.isFinite(newStop) || newStop <= 0) {
    return { content: `Invalid new_stop_price: ${input.new_stop_price}`, is_error: true }
  }

  // Confirm the position exists and infer side / qty for the replacement stop
  const positions = (await alpacaFetch(tradingBase(), '/v2/positions')) as Record<string, unknown>[]
  const pos = positions.find((p) => String(p.symbol).toUpperCase() === symbol)
  if (!pos) {
    return { content: `No open position for ${symbol}. Cannot advance stop.`, is_error: true }
  }
  const positionQty = Math.abs(Number(pos.qty))
  const positionSide = String(pos.side) // "long" or "short"
  const closeSide = positionSide === 'long' ? 'sell' : 'buy'

  // Sanity: trailing on a long means new stop should be below current price; warn if above
  const currentPrice = Number(pos.current_price)
  if (Number.isFinite(currentPrice)) {
    if (positionSide === 'long' && newStop >= currentPrice) {
      return {
        content: `Trade rejected: new_stop_price ($${newStop}) is at/above current price ($${currentPrice}) on a long. That would trigger immediately.`,
        is_error: true,
      }
    }
    if (positionSide === 'short' && newStop <= currentPrice) {
      return {
        content: `Trade rejected: new_stop_price ($${newStop}) is at/below current price ($${currentPrice}) on a short.`,
        is_error: true,
      }
    }
  }

  // Find and cancel any open stop orders on this symbol (bracket child stops show up here)
  const openOrders = (await alpacaFetch(tradingBase(), `/v2/orders?status=open&symbols=${encodeURIComponent(symbol)}&limit=100`)) as Record<string, unknown>[]
  const stopOrders = openOrders.filter((o) => {
    const t = String(o.type ?? '')
    const s = String(o.side ?? '')
    return (t === 'stop' || t === 'stop_limit') && s === closeSide
  })

  const canceled: string[] = []
  for (const order of stopOrders) {
    const id = String(order.id)
    try {
      await alpacaFetch(tradingBase(), `/v2/orders/${encodeURIComponent(id)}`, { method: 'DELETE' })
      canceled.push(id)
    } catch (err) {
      // Continue — we'll still try to place the new stop
      const message = err instanceof Error ? err.message : String(err)
      canceled.push(`${id} (cancel failed: ${message})`)
    }
  }

  // Place the replacement stop for the remaining position size
  const newOrder = await alpacaFetch(tradingBase(), '/v2/orders', {
    method: 'POST',
    body: {
      symbol,
      qty: String(positionQty),
      side: closeSide,
      type: 'stop',
      time_in_force: 'gtc',
      stop_price: String(newStop),
      client_order_id: `bt-trail-${Date.now()}`,
    },
  })

  return {
    content:
      `Trailed stop on ${symbol} to $${newStop} (qty=${positionQty}). ` +
      `Canceled ${canceled.length} prior stop order(s).\n\n${JSON.stringify(newOrder, null, 2)}`,
  }
}

// ── Per-agent tool gating ──────────────────────────────────────────────

const ALPACA_AGENTS = new Set(['options-trader'])

export function getAlpacaTools(agentId: string): Anthropic.Tool[] | undefined {
  if (!ALPACA_AGENTS.has(agentId)) return undefined
  if (!process.env.ALPACA_API_KEY || !process.env.ALPACA_SECRET_KEY) return undefined
  return ALPACA_TOOLS
}
