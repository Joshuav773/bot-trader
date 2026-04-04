# Bot Trader - Claude Code Workspace

## Project Overview
Trading agent chat platform with two specialized AI personas (Options Analyst & Forex Trader), deployed on Vercel with React frontend and Claude API backend using GitHub MCP for repo access.

## Architecture
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS (`agent_chat_ui/src/`)
- **Backend**: Vercel serverless functions with Anthropic SDK (`agent_chat_ui/api/`)
- **Agents**: Persona JSON files in `agents/` — these are living documents that Claude updates via GitHub MCP
- **Streaming**: SSE from `POST /api/chat` — no polling
- **State**: In-memory session store (conversations lost on cold start)

## Multi-Agent Orchestration Protocol
- Agent personas are defined in `./agents/` as JSON files
- When the user selects an agent from the UI, adopt that persona's full "Thought Architecture"
- Global Constraint: All agents must prioritize the S&P 500 index and track institutional orders >$500k

### Agent Switch Logic
- **Analyst**: Focus on OHLC data, RSI, and volume gaps
- **Strategist**: Focus on macro trends, sentiment, and long-term positioning
- **Quant**: Focus on mean-reversion code execution and backtesting logic

## Key Files
- `agents/options-trader-agent.json` — Quant Oracle persona (BSM, Greeks, volatility)
- `agents/forex-trader-agent.json` — Global Macro Sentinel persona (carry trades, FVG, liquidity)
- `agent_chat_ui/api/_lib/claude.ts` — Core backend: auth, system prompt builder, streaming loop
- `agent_chat_ui/api/_lib/sessions.ts` — In-memory conversation store
- `agent_chat_ui/api/chat.ts` — Unified SSE chat endpoint
- `agent_chat_ui/api/conversations.ts` — List/get conversations
- `agent_chat_ui/src/App.tsx` — Main React app with SSE streaming
- `agent_chat_ui/src/api.ts` — Frontend API client

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude API key
- `GITHUB_MCP_URL` — GitHub MCP server endpoint (`https://api.githubcopilot.com/mcp`)
- `GITHUB_TOKEN` — GitHub PAT for MCP auth
- `CLAUDE_MODEL` — Model ID (default: `claude-sonnet-4-6-20250514`)
- `AGENT_CHAT_API_KEY` — Frontend auth key
- `GITHUB_REPO_URL` — Target repo URL
- `GITHUB_REPO_REF` — Target branch (default: `main`)

## Commands
- `cd agent_chat_ui && npm run dev` — Vite dev server (frontend only)
- `cd agent_chat_ui && npx vercel dev` — Full dev server (frontend + API)
- `cd agent_chat_ui && npm run build` — Production build
- `cd agent_chat_ui && npm run lint` — ESLint

## Conventions
- Persona files are the source of truth for agent behavior
- Claude self-evolves personas via GitHub MCP (commits to `learned_context` field)
- No database — repo is the persistence layer for agent knowledge
- SSE streaming for all chat responses, no polling
- Bearer token auth on all API endpoints
