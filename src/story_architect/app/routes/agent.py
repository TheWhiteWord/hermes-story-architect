from fastapi import APIRouter


def make_router(config, app):
    router = APIRouter()

    @router.get("/api/agent/state")
    def agent_state():
        from story_architect.adapters.hermes.gateway import agent_state as _state
        return _state(config)

    @router.get("/api/agent/settings")
    def agent_settings():
        from story_architect.adapters.hermes.gateway import agent_settings as _settings
        return _settings(config)

    @router.patch("/api/agent/settings")
    def agent_settings_patch(body: dict = {}):
        from story_architect.app.state_store import save_state
        body = body or {}
        if "autostart" in body:
            save_state({"agent_autostart": bool(body["autostart"])})
            config.agent_autostart = bool(body["autostart"])
        return {"ok": True}

    @router.post("/api/agent/start")
    def agent_start():
        from story_architect.adapters.hermes.gateway import start_gateway as _start
        res = _start(config)
        app.state.agent_started_by_app = bool(res.get("started_by_app"))
        return res

    @router.post("/api/agent/stop")
    def agent_stop():
        from story_architect.adapters.hermes.gateway import stop_gateway as _stop
        return _stop(config)

    return router
