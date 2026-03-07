"""
Agent Chat — FastAPI backend that launches Cursor Cloud Agents
and streams their conversation back to the UI via SSE.
"""
import os
import json
import time
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_chat.cursor_client import CursorAgents

load_dotenv()
log = logging.getLogger(__name__)

AGENT_LABELS = {
    "scanner": "Market Scanner",
    "analyst": "Options Analyst",
}


def build_prompt(agent_id: str | None, user_prompt: str) -> str:
    label = AGENT_LABELS.get(agent_id or "", agent_id or "Agent")
    return f"Adopt the persona: {label}. Follow the instructions in the agents/ folder for this persona.\n\n{user_prompt}"


app = FastAPI(title="Agent Command", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
REPO_URL = os.getenv("GITHUB_REPO_URL", "")
REPO_REF = os.getenv("GITHUB_REPO_REF", "main")
MODEL = os.getenv("CURSOR_MODEL", "claude-4.5-sonnet-thinking")
API_KEY = os.getenv("AGENT_CHAT_API_KEY", "")

_cursor: CursorAgents | None = None
active_agents: dict[str, str] = {}


def get_cursor() -> CursorAgents:
    global _cursor
    if _cursor is None:
        _cursor = CursorAgents()
    return _cursor


# ── Auth ───────────────────────────────────────────────────────────────

def require_auth(request: Request):
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not API_KEY or token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class AuthIn(BaseModel):
    api_key: str


@app.post("/api/auth")
def authenticate(body: AuthIn):
    if not API_KEY or body.api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"ok": True}


# ── Models ─────────────────────────────────────────────────────────────

class PromptIn(BaseModel):
    prompt: str
    agent_id: str | None = None


class AgentOut(BaseModel):
    ok: bool
    agent_cursor_id: str | None = None
    status: str | None = None
    message: str = ""
    url: str | None = None


# ── Launch ─────────────────────────────────────────────────────────────

@app.post("/api/launch", response_model=AgentOut, dependencies=[Depends(require_auth)])
def launch_agent(body: PromptIn):
    persona = body.agent_id or "analyst"
    prompt = build_prompt(persona, body.prompt)

    if not REPO_URL:
        return AgentOut(ok=False, message="GITHUB_REPO_URL not set in .env")

    try:
        c = get_cursor()
        result = c.launch(prompt=prompt, repository=REPO_URL, ref=REPO_REF, model=MODEL)
        active_agents[persona] = result.agent_id
        return AgentOut(
            ok=True,
            agent_cursor_id=result.agent_id,
            status=result.status,
            message=result.agent_id,
            url=result.url,
        )
    except Exception as e:
        log.error("Launch error: %s", e)
        return AgentOut(ok=False, message=str(e))


# ── Follow-up ──────────────────────────────────────────────────────────

@app.post("/api/followup", response_model=AgentOut, dependencies=[Depends(require_auth)])
def followup_agent(body: PromptIn):
    persona = body.agent_id or "analyst"
    cursor_id = active_agents.get(persona)

    if not cursor_id:
        return launch_agent(body)

    prompt = build_prompt(persona, body.prompt)
    try:
        get_cursor().followup(cursor_id, prompt)
        return AgentOut(ok=True, agent_cursor_id=cursor_id, status="RUNNING", message=cursor_id)
    except Exception as e:
        log.error("Follow-up error: %s", e)
        return AgentOut(ok=False, message=str(e))


# ── SSE stream ─────────────────────────────────────────────────────────

@app.get("/api/stream/{persona}")
async def stream_conversation(persona: str, request: Request):
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    key_param = request.query_params.get("key", "")
    if not API_KEY or (token != API_KEY and key_param != API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")

    cursor_id = active_agents.get(persona)
    if not cursor_id:
        async def no_agent():
            yield sse_event("error", {"message": "No active agent"})
        return StreamingResponse(no_agent(), media_type="text/event-stream")

    async def generate():
        seen_ids: set[str] = set()
        last_status = ""
        max_time = 600
        start = time.time()

        while time.time() - start < max_time:
            try:
                c = get_cursor()

                result = c.status(cursor_id)
                if result.status != last_status:
                    last_status = result.status
                    yield sse_event("status", {
                        "status": result.status,
                        "summary": result.summary,
                        "url": result.url,
                        "pr_url": result.pr_url,
                    })

                try:
                    msgs = c.conversation(cursor_id)
                except Exception:
                    msgs = []

                for msg in msgs:
                    msg_id = msg.get("id", "")
                    if msg_id and msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        yield sse_event("message", {
                            "id": msg_id,
                            "type": msg.get("type", ""),
                            "text": msg.get("text", ""),
                        })

                if result.status in ("FINISHED", "STOPPED", "ERRORED"):
                    yield sse_event("done", {
                        "status": result.status,
                        "summary": result.summary,
                    })
                    return

            except Exception as e:
                yield sse_event("error", {"message": str(e)})
                return

            await asyncio.sleep(2)

        yield sse_event("done", {"status": "TIMEOUT", "summary": "Polling timed out"})

    return StreamingResponse(generate(), media_type="text/event-stream")


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Stop / clear ──────────────────────────────────────────────────────

@app.post("/api/stop", dependencies=[Depends(require_auth)])
def stop_agent(body: PromptIn):
    persona = body.agent_id or "analyst"
    cursor_id = active_agents.get(persona)
    if not cursor_id:
        return {"ok": False}
    try:
        get_cursor().stop(cursor_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/clear", dependencies=[Depends(require_auth)])
def clear_agent(body: PromptIn):
    persona = body.agent_id or "analyst"
    active_agents.pop(persona, None)
    return {"ok": True}


# ── Serve React SPA ───────────────────────────────────────────────────

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file = STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
