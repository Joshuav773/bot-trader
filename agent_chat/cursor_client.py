"""
Cursor Cloud Agents API client.
Docs: https://cursor.com/docs/cloud-agent/api/endpoints
"""
import os
import time
import logging
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

BASE = "https://api.cursor.com"
POLL_INTERVAL = 3  # seconds between status checks
MAX_POLL_TIME = 300  # 5 min max wait


@dataclass
class AgentResult:
    agent_id: str
    status: str
    summary: str | None = None
    messages: list[dict] | None = None
    branch: str | None = None
    pr_url: str | None = None
    url: str | None = None


class CursorAgents:
    def __init__(self):
        self.api_key = os.getenv("CURSOR_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("CURSOR_API_KEY not set in .env")
        self.auth = (self.api_key, "")

    def _get(self, path: str, **kwargs) -> dict:
        r = requests.get(f"{BASE}{path}", auth=self.auth, **kwargs)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict | None = None) -> dict:
        r = requests.post(f"{BASE}{path}", auth=self.auth, json=json)
        r.raise_for_status()
        return r.json()

    def _delete(self, path: str) -> dict:
        r = requests.delete(f"{BASE}{path}", auth=self.auth)
        r.raise_for_status()
        return r.json()

    def list_models(self) -> list[str]:
        return self._get("/v0/models").get("models", [])

    def list_agents(self, limit: int = 20) -> list[dict]:
        return self._get("/v0/agents", params={"limit": limit}).get("agents", [])

    def launch(
        self,
        prompt: str,
        repository: str,
        ref: str = "main",
        model: str = "claude-4.5-sonnet-thinking",
        auto_create_pr: bool = False,
        branch_name: str | None = None,
    ) -> AgentResult:
        body: dict = {
            "prompt": {"text": prompt},
            "model": model,
            "source": {"repository": repository, "ref": ref},
        }
        if auto_create_pr or branch_name:
            body["target"] = {}
            if auto_create_pr:
                body["target"]["autoCreatePr"] = True
            if branch_name:
                body["target"]["branchName"] = branch_name

        data = self._post("/v0/agents", json=body)
        target = data.get("target", {})
        return AgentResult(
            agent_id=data["id"],
            status=data.get("status", "CREATING"),
            summary=data.get("summary"),
            branch=target.get("branchName"),
            pr_url=target.get("prUrl"),
            url=target.get("url"),
        )

    def status(self, agent_id: str) -> AgentResult:
        data = self._get(f"/v0/agents/{agent_id}")
        target = data.get("target", {})
        return AgentResult(
            agent_id=data["id"],
            status=data.get("status", "UNKNOWN"),
            summary=data.get("summary"),
            branch=target.get("branchName"),
            pr_url=target.get("prUrl"),
            url=target.get("url"),
        )

    def conversation(self, agent_id: str) -> list[dict]:
        data = self._get(f"/v0/agents/{agent_id}/conversation")
        return data.get("messages", [])

    def followup(self, agent_id: str, prompt: str) -> dict:
        return self._post(
            f"/v0/agents/{agent_id}/followup",
            json={"prompt": {"text": prompt}},
        )

    def stop(self, agent_id: str) -> dict:
        return self._post(f"/v0/agents/{agent_id}/stop")

    def delete(self, agent_id: str) -> dict:
        return self._delete(f"/v0/agents/{agent_id}")

    def poll_until_done(self, agent_id: str) -> AgentResult:
        """Poll agent status until FINISHED, STOPPED, or timeout."""
        start = time.time()
        while time.time() - start < MAX_POLL_TIME:
            result = self.status(agent_id)
            if result.status in ("FINISHED", "STOPPED", "ERRORED"):
                return result
            time.sleep(POLL_INTERVAL)
        return self.status(agent_id)

    def get_last_assistant_message(self, agent_id: str) -> str:
        msgs = self.conversation(agent_id)
        for msg in reversed(msgs):
            if msg.get("type") == "assistant_message":
                return msg.get("text", "")
        return ""
