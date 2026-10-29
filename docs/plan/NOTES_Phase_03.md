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
- Config extended with `hermes_api_port` (env STORY_ARCHITECT_HERMES_API_PORT).
- token module gained `ensure_api_key`/`load_api_key` (0600 in config dir).
- setup enables API server platforms config, writes API_SERVER_KEY to profile .env, sets toolsets=[] (conservative: no built-in terminal/file tools; MCP story tools remain). status checks API reachability/auth/model id.
- Agent cannot run shell/file tools by default; web search disabled (toolsets empty). Owner can change toolsets in profile config.
- Tests: tests/test_hermes_chat_backend.py — 5 passing (text+tool, auth, unreachable, malformed, continuity).

## Phase 3 Task 4 (Chat HTTP routes and request protection)
- Routes added in src/story_architect/app/server.py: conversations list/create/get/delete and messages send (SSE) + cancel.
- Cross-site protection added to host_check middleware for non-GET: Origin (when present) must match app origin; custom header X-Story-Architect: 1 required.
- Backend instantiated from config; 503 if unavailable.
- One reply at a time per conversation via active_replies dict.
- 
## Phase 3 Task 6 (Chat UI)
- Panel: floating drawer (#sa-chat-panel) + toggle button; conversation list/new/delete, message list, input, stop.
- Streaming: fetch() streaming SSE; text deltas appended; tool events shown as quiet indicators; custom header X-Story-Architect: 1 on all requests.
- Safe rendering: persisted messages escaped via esc(); streaming uses textContent. Minimal subset not implemented (plain text only) — XSS-safe.
- DASH.askAgent now opens panel and sends text with project context.
- Persistence/restore: conversations loaded from server; last-open restored on init (first conversation).
- Files: web/js/chat.js, web/css/chat.css; wired into index.html and stats.py JS_ORDER/CSS_ORDER.
- Deviations: no markdown rendering beyond plain text; no agent state UI (start button not added, state check available via /api/agent/state).
- 
## Phase 3 Task 5 (Agent availability)
- Added src/story_architect/adapters/hermes/gateway.py: agent_state() returns not_configured/gateway_stopped/api_unreachable/ready; start_gateway() invokes hermes -p <profile> gateway start and polls API readiness (timeout 15s). App never kills a gateway it did not start (started_by_app tracked in app.state).
- Config gained agent_autostart (env STORY_ARCHITECT_AGENT_AUTOSTART / config.toml), default off.
- Routes: GET /api/agent/state, POST /api/agent/start.
- Shutdown: no process cleanup; gateway persists per Task 1 (systemd/user service). App only cancels its own in-flight replies.

## Phase 3 Task 7 (Docs)
- README updated with Chat section: requirements, starting agent, autostart, status, capabilities, chat storage, refresh banner. Setup/status sections updated for new hermes setup behavior.
- Plan checklist (phase-3-in-app-chat.md Task 7) ticked.
- Deviations carried: no markdown rendering in chat (plain text only, XSS-safe); no agent state UI button beyond /api/agent/state + start endpoint; web search disabled by default (owner call still open).
- Task 1 findings recap: endpoint POST /v1/chat/completions streaming SSE; continuity via /v1/responses previous_response_id; tool-progress events hermes.tool.progress; toolsets=[] (no terminal/file/web). Agent can read/query via MCP story tools and stage/commit via drafts; cannot shell/write files/web by default.
- Phase 4 note: agent and UI both touch story.db via writes.py single path; compare-and-swap/concurrency needed when both active; refresh banner is current reconciliation mechanism.