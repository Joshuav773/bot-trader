# Agent Command — Chat UI

Chat interface for sending prompts to your Cursor cloud agents. Built with React + Tailwind CSS (frontend) and FastAPI (backend).

## Development

Start the Vite dev server with hot-reload (proxies API calls to the backend):

```bash
# Terminal 1 — backend
source venv/bin/activate
uvicorn agent_chat.main:app --reload --host 0.0.0.0 --port 8765

# Terminal 2 — frontend dev
cd agent_chat_ui
npm run dev          # → http://localhost:3000
```

## Production

Build the React app, then serve everything from FastAPI:

```bash
cd agent_chat_ui && npm run build   # outputs to agent_chat/static/
cd .. && uvicorn agent_chat.main:app --host 0.0.0.0 --port 8765
# → http://localhost:8765
```

## Structure

```
agent_chat/          # FastAPI backend
  main.py            # /api/prompt endpoint + serves SPA
  static/            # Built React output (git-ignored)

agent_chat_ui/       # React + Vite + Tailwind source
  src/
    App.tsx           # Main chat app
    agents.ts         # Agent personas
    api.ts            # Fetch helper
    types.ts          # Shared types
    components/
      AgentPicker.tsx
      ChatInput.tsx
      MessageBubble.tsx
      TypingIndicator.tsx
```
