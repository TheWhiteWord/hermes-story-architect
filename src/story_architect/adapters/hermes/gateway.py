"""Agent (profile gateway) availability helpers."""
from __future__ import annotations
import time
from typing import Any
from story_architect.adapters.hermes import wrapper as W
from story_architect.app.config import Config

PROFILE = "story-architect"


def _base_url(config: Config, profile: str = PROFILE) -> str:
    return f"http://127.0.0.1:{config.hermes_api_port}/p/{profile}"


def agent_state(config: Config, profile: str = PROFILE) -> dict[str, Any]:
    pd = W.profile_dir(profile)
    if not pd.exists():
        return {"state": "not_configured", "detail": "profile missing"}
    try:
        from story_architect.app import token as token_mod
        key = token_mod.load_api_key()
    except Exception:
        key = None
    if not key:
        return {"state": "not_configured", "detail": "api key missing"}
    try:
        try:
            import httpx
        except ImportError:
            import httpx2 as httpx
        r = httpx.get(f"{_base_url(config, profile)}/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=2.0)
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
    # under the host multiplexer the profile is already served; just check readiness
    st = agent_state(config, profile)
    if st["state"] == "ready":
        return {"ok": True, "started_by_app": False, **st}
    # under the host multiplexer the profile is already served (or will be
    # after the host's periodic rescan). Never spawn a standalone gateway run:
    # that parks the profile and breaks the host multiplexer.
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = agent_state(config, profile)
        if st["state"] == "ready":
            return {"ok": True, "started_by_app": False, **st}
        time.sleep(0.5)
    st = agent_state(config, profile)
    return {"ok": False, "started_by_app": False, "detail": st.get("detail", "timeout")}


def agent_settings(config: Config, profile: str = PROFILE) -> dict[str, Any]:
    st = agent_state(config, profile)
    return {
        "state": st["state"],
        "detail": st["detail"],
        "profile": profile,
        "port": config.hermes_api_port,
        "autostart": bool(config.agent_autostart),
        "can_stop": True,
        "model": {"current": profile, "options": None},
    }


def stop_gateway(config: Config, profile: str = PROFILE) -> dict[str, Any]:
    # do not call `gateway stop`: it creates a gateway.parked marker that makes
    # the host multiplexer skip the profile. Just report current state.
    st = agent_state(config, profile)
    return {"ok": True, "detail": st.get("detail", "ok")}