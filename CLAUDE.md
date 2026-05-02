# Bot Trader - Claude Code Workspace

## Project Overview
Trading agent chat platform with two specialized AI personas (Options Analyst & Forex Trader), deployed on Vercel with React frontend and Claude API backend using GitHub MCP for repo access.

## Architecture
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS (`agent_chat_ui/src/`)
- **Backend**: Vercel serverless functions with Anthropic SDK (`agent_chat_ui/api/`)
- **Agents**: Each persona lives in its own folder under `agents/` with a JSON definition and optional context markdown files. These are living documents that Claude updates via GitHub MCP.
- **Streaming**: SSE from `POST /api/chat` — no polling
- **State**: In-memory session store (conversations lost on cold start)

## Agent Directory Structure

Each agent has its own folder. The system prompt combines the JSON persona with every markdown file in `context/`:

```
agents/
├── options-trader/
│   ├── options-trader-agent.json    # Persona definition (structured)
│   └── context/                     # Living context — loaded on every request
│       ├── ACCOUNT_LEDGER.md        # Trade history
│       ├── PROTOCOL.md              # Enhanced operational protocol
│       ├── MARKET_CONTEXT_FRAMEWORK.md
│       └── ...                      # Any *.md file here gets injected
└── forex-trader/
    ├── forex-trader-agent.json
    └── context/                     # May be empty — JSON is used alone
```

### Rules
- **Every `.md` file in `agents/<agent-id>/context/` is loaded** and injected into the system prompt on every request (sorted alphabetically by filename)
- **If `context/` is empty or missing**, only the JSON persona is used
- **Claude is expected to update its own files** via GitHub MCP after meaningful conversations — both the persona JSON (`learned_context` field) and the context markdown (protocols, ledgers, learnings)
- **Filenames should be descriptive** — e.g. `ACCOUNT_LEDGER.md`, `PROTOCOL.md`, `WINNING_PATTERNS.md` — so the model can maintain them over time

## Multi-Agent Orchestration Protocol
- Agent personas are defined in their respective folders under `./agents/`
- When the user selects an agent from the UI, adopt that persona's full "Thought Architecture"
- Global Constraint: All agents must prioritize the S&P 500 index and track institutional orders >$500k

### Agent Switch Logic
- **Analyst**: Focus on OHLC data, RSI, and volume gaps
- **Strategist**: Focus on macro trends, sentiment, and long-term positioning
- **Quant**: Focus on mean-reversion code execution and backtesting logic

## Key Files
- `agents/options-trader/` — Quant Oracle (BSM, Greeks, volatility) + full trading context
- `agents/forex-trader/` — Global Macro Sentinel (carry trades, FVG, liquidity)
- `agent_chat_ui/api/_lib/claude.ts` — Core backend: auth, persona + context loading, system prompt builder, streaming loop
- `agent_chat_ui/api/_lib/sessions.ts` — In-memory conversation store
- `agent_chat_ui/api/chat.ts` — Unified SSE chat endpoint (replaces Cursor's launch/followup/status/stop)
- `agent_chat_ui/api/conversations.ts` — List/get conversations
- `agent_chat_ui/api/auth.ts` — API key authentication
- `agent_chat_ui/src/App.tsx` — Main React app with SSE streaming (no more polling)
- `agent_chat_ui/src/api.ts` — Frontend API client with `streamChat`, `listConversations`, `getConversation`

## Trade Execution (Alpaca Paper)

The Options Analyst can place paper-trading orders against an Alpaca account using native Claude tools defined in `agent_chat_ui/api/_lib/alpaca.ts`. **The flow requires explicit user confirmation** — Claude proposes a trade ticket (entry/stop/target/qty/conviction), and only places it when the user approves.

### Hard guardrails
- **Paper-only**: `alpaca.ts` throws at module init if `ALPACA_BASE_URL` isn't the paper endpoint.
- **Stocks must have stop + target**: bracket orders are submitted automatically; the tool rejects stock buys without both.
- **Confirmation required**: the system prompt forbids `alpaca_place_order` without explicit user "yes / place it / approved" approval.

Position sizing is governed by [`agents/options-trader/context/EXECUTION_PROTOCOL.md`](agents/options-trader/context/EXECUTION_PROTOCOL.md), not by a hardcoded cap. The Alpaca account's buying power is the real ceiling.

### Tool surface
- Read-only (called freely): `alpaca_get_account`, `alpaca_get_positions`, `alpaca_get_orders`, `alpaca_get_quote`, `alpaca_get_bars`, `alpaca_get_option_chain`
- Mutating (require confirmation): `alpaca_place_order`, `alpaca_cancel_order`, `alpaca_close_position`

### Per-agent gating
Only `options-trader` gets Alpaca tools. The Forex Analyst stays analysis-only (Alpaca doesn't trade FX).

### Trade journal
Claude updates `agents/options-trader/context/ACCOUNT_LEDGER.md` via the GitHub MCP after every fill — see `EXECUTION_PROTOCOL.md` in the same folder for the full ruleset.

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude API key
- `GITHUB_MCP_URL` — GitHub MCP server endpoint (`https://api.githubcopilot.com/mcp`). If unset, chat runs without GitHub tools.
- `GITHUB_TOKEN` — GitHub PAT for MCP auth (requires `repo`, `read:user`, `read:org` scopes)
- `CLAUDE_MODEL` — Model ID (default: `claude-sonnet-4-6`)
- `AGENT_CHAT_API_KEY` — Frontend auth key
- `GITHUB_REPO_URL` — Target repo URL (where Claude writes persona/context updates)
- `GITHUB_REPO_REF` — Target branch (default: `main`)
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` — Alpaca paper account credentials (omit to disable trading tools)
- `ALPACA_BASE_URL` — Must be `https://paper-api.alpaca.markets` (anything else is rejected)

## Commands
- `cd agent_chat_ui && npm run dev` — Vite dev server (frontend only, API routes won't work)
- `cd agent_chat_ui && npx vercel dev` — Full dev server (frontend + API routes) ⭐ use this for testing
- `cd agent_chat_ui && npm run build` — Production build
- `cd agent_chat_ui && npm run lint` — ESLint

## Conventions
- **Persona + context are the source of truth** for agent behavior — both are injected into the system prompt on every request
- **Claude self-evolves its own files** via GitHub MCP (updates `learned_context` in JSON, creates/updates `.md` files in `context/`)
- **No database** — the repo is the persistence layer for agent knowledge, conversations are ephemeral (in-memory)
- **SSE streaming for all chat responses**, no polling
- **Bearer token auth** on all API endpoints (using `AGENT_CHAT_API_KEY`)
- **Stop = client aborts the SSE stream** — there is no `/api/stop` endpoint anymore
