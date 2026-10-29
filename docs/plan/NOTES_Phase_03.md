# Notes — Phase 3

## Phase 3 Task 1 (spike on Hermes API server)
- C1: API server enabled per profile via platforms.api_server in config.yaml (enabled, key, port, host). Runs inside profile gateway; requires strong key (>=16 chars, not placeholder).
- C2: not tested (no story profile/MCP in scratch); config mechanism same as default gateway, MCP tools available to agent via API server expected.
- C3: streaming works: SSE chunks OpenAI format plus `event: hermes.status` and `event: hermes.tool.progress` (tool name available). Final chunk has finish_reason and hermes.completed.
- C4: continuity via /v1/responses with previous_response_id (OpenAI responses API); gateway restart loses in-memory state unless persisted by Hermes; app stores own transcripts.
- C5: toolsets restricted via profile config / toolsets; exact keys to be set in Task 3. Default model etc.
- C6: gateway managed via systemd user service per profile when standalone; `hermes -p <name> gateway install/start/stop/status`. Multiplexed host gateway serves all profiles by default; standalone only when needed.
- C7: final assistant text in delta.content; tool chatter via hermes.tool.progress events; status events separate.
- Recommended endpoint: POST /v1/chat/completions streaming (SSE) for simplicity; continuity via previous_response_id on /v1/responses if needed. Auth via Bearer API_SERVER_KEY.
- Ports: default 8642, configurable. Host 127.0.0.1.
- Scratch profile and process removed.

## Phase 3 Task 0 (baseline)
- Suite green: 1013 passed (2026-10-29); ruff not installed in project venv — ran via uv cache ruff 0.15.8: 410 errors (mostly pre-existing E501 line length; not introduced now).
- Manual Phase 2 check: not performed (no Hermes profile available in this session); recorded as skipped.
- Overview updated: Phase 2 marked done; hermes serve conflict note replaced; port note added.

