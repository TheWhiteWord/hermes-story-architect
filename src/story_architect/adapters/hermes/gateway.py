"""Agent (profile gateway) availability helpers."""
from __future__ import annotations

import time
from typing import Any

from story_architect.adapters.hermes import wrapper as W
from story_architect.app.config import Config

PROFILE = "story-architect"


def _base_url(config: Config) -> str:
    return f"http://127.0.0.1:{config.hermes_api_port}"


def agent_state(config: Config, profile: str = PROFILE) -> dict[str, Any]:
    pd = W.profile_dir(profile)
    if not pd.exists():
        return {"state": "not_configured", "detail": "profile missing"}
    # api key
    try:
        from story_architect.app import token as token_mod
        key = token_mod.load_api_key()
    except Exception:
        key = None
    if not key:
        return {"state": "not_configured", "detail": "api key missing"}
    # reachability
    try:
        try:
            import httpx
        except ImportError:
            import httpx2 as httpx
        r = httpx.get(f"{_base_url(config)}/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=2.0)
    except Exception as e:
        return {"state": "gateway_stopped", "detail": str(e)}
    if r.status_code == 401:
        return {"state": "api_unreachable", "detail": "auth failed"}
    if r.status_code >= 400:
        return {"state": "api_unreachable", "detail": f"http {r.status_code}"}
    try:
        data = r.json()
        ids = [m.get("id") for m in data.get("data", [])]
    except Exception:
        ids = []
    if profile not in ids and ids:
        return {"state": "api_unreachable", "detail": f"model mismatch: {ids}"}
    return {"state": "ready", "detail": "ok"}


def start_gateway(config: Config, profile: str = PROFILE, timeout: float = 15.0) -> dict[str, Any]:
    rc, out, err = W.run_hermes("-p", profile, "gateway", "start")
    # best effort: ignore rc, poll
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = agent_state(config, profile)
        if st["state"] == "ready":
            return {"ok": True, "started_by_app": True, **st}
        time.sleep(0.5)
    return {"ok": False, "started_by_app": True, "detail": (err or out).strip() or "timeout"}