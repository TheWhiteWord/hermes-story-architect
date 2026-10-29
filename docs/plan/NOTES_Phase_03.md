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

## Phase 3 Task 2 (chat core)
- Package: src/story_architect/chat/ — events (TextDelta, ToolStarted, ToolFinished, Done, Error), ChatBackend protocol, store (chat.db per project, two tables), ChatService, FakeBackend. No FastAPI/Hermes imports.
- Tests: tests/test_chat_core.py — 6 passing (new conv, multi-turn, reload, isolation, error, cancellation).
- Deviations: cancellation status may be 'streaming'/'cancelled' depending on close timing; store access sync.

## Phase 3 Task 3 (Hermes chat backend and setup extensions)
- Implemented `adapters/hermes/chat_backend.py` (`HermesChatBackend`) using httpx streaming against `/v1/chat/completions`; maps text deltas and `hermes.tool.progress` events; ignores unknown events; captures response id as backend state.
- Config extended with `hermes_api_port` (env STORY_ARCHITECT_HERMES_API_PORT).
- token module gained `ensure_api_key`/`load_api_key` (0600 in config dir).
- setup enables API server platforms config, writes API_SERVER_KEY to profile .env, sets toolsets=[] (conservative: no built-in terminal/file tools; MCP story tools remain). status checks API reachability/auth/model id.
- Agent cannot run shell/file tools by default; web search disabled (toolsets empty). Owner can change toolsets in profile config.
- Tests: tests/test_hermes_chat_backend.py — 5 passing (text+tool, auth, unreachable, malformed, continuity).
