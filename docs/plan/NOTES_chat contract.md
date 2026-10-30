# Notes — Chat contract

## Section 0 diagnosis (2026-10-30)

1. Context bug: backend already reads `project`/`project_slug`/`slug`; UI sends `{project: slug}`. Stopgap retained; full bootstrap (section 2) not yet implemented.
2. Agent profile: API server on port 8642 (default) serves model id `story-architect` = profile name. `GET /v1/models` returned `story-architect`. Raw `/v1/chat/completions` (no system msg) answered as system-owner persona because profile SOUL.md is foreign (not adapter's). Run `story-architect hermes setup --force` to install adapter SOUL. Model id now sourced from config (`hermes_profile`, default `story-architect`) instead of hard-coded string.
3. SSE captured: `tests/fixtures/sse_tool_reply.txt` (878 lines, includes `hermes.tool.progress`).
4. `previous_response_id` removed from payload; context carried by full message history + system bootstrap.

## Deviations
- Added `hermes_profile` to Config (default `story-architect`) and `STORY_ARCHITECT_HERMES_PROFILE` env override.
- SOUL.md in profile is foreign; not overwritten automatically.

## Section 8a — restrict built-in tools

Working key: `agent.disabled_toolsets` (list of all builtin toolset names). `toolsets: []` means defaults, not empty. Setup now sets `agent.disabled_toolsets` to all builtin toolsets; status fails if `terminal` not in that list.

Deviation: import of hermes toolsets module from /home/davide/.hermes/hermes-agent at setup time; fallback to empty list. Web search stays off.

Scope note: disabled_toolsets is written only to the story-architect profile config; default and other profiles are untouched.

## Section 1 (UI wiring) + Section 2 (context) + persona

Short summary: Wired the new chat UI files into the dashboard (CSS + 4 JS, JS_ORDER updated, old chat.js removed). Created chat/context.py with build_bootstrap. Changed ChatBackend.send signature to (messages, instructions, backend_state), dropping context; adapter sends instructions as system message with no persona text; FakeBackend records instructions; ChatService builds bootstrap from request context + project name. Setup now treats a SOUL.md byte-identical to the default profile's as replaceable (backs up first), still refuses genuinely custom ones without --force. Updated SOUL.md and SKILL.md to describe approval cards.

Diagnosis findings (section 0): unchanged from prior notes — context bug stopgap retained until bootstrap (now implemented); agent profile on port 8642; SSE fixture captured; previous_response_id removed.

Deviations: ChatService computes slug from project_path.name (string or Path). Project name lookup reuses core.drafts._project_name.

Contract change for UI: none new; bootstrap is server-side only and never persisted/shown.

## panelContext follow-up
DASH.panelContext cleared on closePanel. Per-site setting at the 8 entity-panel open sites in panels/entity-panels.js is deferred (optional); UI currently sends only the visible label.

## Section 3 — Reply stream (SSE) backend parse fix

- Summary: `HermesChatBackend` now tracks the SSE `event:` line as `current_event` and treats a `hermes.tool.progress` event whether it arrives via the event line or a nested `event` field. Flat (real) payloads `{tool, status, ...}` and nested `{data:{tool}}` payloads are both parsed. `running` -> ToolStarted, `completed`/`finished`/`done` -> ToolFinished, others -> started. `reasoning_content` is ignored (only `delta.content` emitted).
- Deviation: events module still uses TextDelta/ToolStarted/ToolFinished names; no ToolFailed class added. Contract's new `text`/`tool`/etc SSE types are handled at route layer, not here.

## Section 4 — Tool events from MCP server

Tool events now originate from the MCP server, not Hermes. `app/tool_bus.py` provides an in-process pub/sub (subscribe/unsubscribe/publish); calls with no subscriber (e.g. Hermes Desktop) are dropped, so only the active reply receives events. `mcp_server.on_call_tool` publishes `started` (id, name, args) before the handler and `finished`/`failed` (+ duration_ms, result_preview ~800 chars) after; on a finished `draft` tool whose result parses to a dict containing `draft`, also publishes a `draft` event. The reply route subscribes while a reply is active and forwards bus events as `tool`/`draft` SSE events. Hermes `hermes.tool.progress` events (real format) are mapped in `chat_backend.py` to `tool` events with id=toolCallId, name=tool, label=label, status running->started/completed->finished (failed/error->failed); names starting with `mcp_story_` are ignored (bus is richer). `ToolStarted`/`ToolFinished` now carry optional id and label. Contract change for UI: tool SSE events include `id`, `name`, `status`, `label`, `args`, `result_preview`, `duration_ms`; `draft` events carry the draft snapshot.

## Section 5 — Drafts as approval cards (endpoints)

Short summary: Added approve/reject routes in server.py. approve calls
core.drafts.commit, returns committed/failed snapshot; reject calls discard.
Both update stored snapshot in the conversation message and add a hidden note.
Stale/missing draft returns 409.

Deviations: partial-failure detection uses result.get("failed") or success is
False; commit's already_committed path returns success True.

Contract change for UI: endpoints return {status, draft}; UI already calls them.


Short summary: Added public `describe_ops(project_path, ops) -> list[dict]` in
`core/drafts.py`, the structured sibling of `render_preview_md`, producing the
`changes` list for approval cards. One entry per op with `kind`, `entity_type`,
`entity_id` (where applicable), `summary`, plus `fields` (create/edit) or
`count` (reorder). Edits take `before` from the same `_current_values` lookup
`_render_edit` uses. `warnings` remain the responsibility of `validate_shape`.

Diagnosis findings (section 0): none blocking for this sub-task.

Deviations: none.

Contract change for UI: none new; `describe_ops` is additive and already named
in the contract. Snapshot persistence and approve/reject endpoints remain
follow-up sub-tasks.

## Section 6 — Store changes (chat.db)

Short summary: Migrated `messages` table with additive columns (tools, drafts,
attachments, hidden, error) via ALTER TABLE in connect(). Updated
add_message/update_message/get_conversation signatures. get_conversation now
filters hidden messages by default and accepts include_hidden for backend
history. approve/reject endpoints persist snapshots and hidden notes.

Diagnosis findings: none new.

Deviations: update_message uses opt-in flags (update_tools etc.) to avoid
clobbering columns; simpler than full rewrite.

Contract change for UI: GET conversations/{cid} now returns id, tools, drafts,
attachments, error per message; hidden omitted from response.

## Task 7 Retry

Diagnosis: store had no retry helper; service.send persisted user msg, so retry must skip that. Endpoint must stream like messages.

Deviations: retry SSE events not fully mapped to typed payloads (minimal); follow-up can align.

Contract change: none new; endpoint streams like messages.

## Section 8 — Agent state and settings

Short summary: Added GET /api/agent/settings, PATCH /api/agent/settings (autostart persisted to state.json), POST /api/agent/stop. autostart precedence: CLI/env > config.toml > state.json > defaults. Model options null (spike not resolved). can_stop true (dedicated per-profile gateway).
No non-interactive model list exists (only interactive hermes model picker with --refresh cache). Keep options: null; UI shows current model read-only and hides selector. Setting model non-interactively isn't reliably supported, so no change.

Diagnosis findings: config had no runtime write path; gateway had no settings/stop helpers.

Deviations: "starting" state not tracked; can_stop always true; model current uses profile name.

Contract change for UI: settings endpoint shape as contract; stop returns {ok, detail}.

## Section 9 — Tests (minimum)

Test results: `tests/test_chat_core.py` + `tests/test_hermes_chat_backend.py` collect and pass (11 tests). Coverage: new conversation, multiturn, reload-from-disk, project isolation, backend error path, cancellation midstream, text+tool streaming, auth failure, unreachable backend, malformed SSE ignored, continuity roundtrip. No new tests added; existing suite already covers the minimum.

Deviation: `test_hermes_chat_backend.py` had an unused `import httpx` that failed collection (httpx optional with httpx2 fallback); removed. No functional change.

## 12.1 Repair first — brief

Short summary: Repaired `GET /api/projects/{slug}/events` so it is only the DB-change feed: polls `PRAGMA data_version` ~1s and emits `event: update`. Removed the orphaned chat producer code that referenced undefined `cid`, `service`, `pp`, `text`, `context`. `ruff --select F` on server.py now clean.

Diagnosis findings (section 0): the events route had been corrupted by a bad merge — its body was the chat reply stream (active_replies, tool_bus, service.send), making `/events` unusable and leaving `/messages` unwired. Undefined names would have been caught by `F821`.

Deviations: did not split server.py into APIRouter modules (third bullet of 12.1) — deferred as a mechanical refactor; behavior unchanged. No contract changes to the SSE shape.

Contract change for UI: none; `/events` now only emits `update` after DB changes.

## 12.1 Split — brief

Short summary: Split `server.py` into `APIRouter` modules: `routes/agent.py`, `routes/chat.py`, `routes/drafts.py`, `routes/projects.py`; `create_app` now only assembles routers and middleware. Mechanical move; no behavior change. `ruff --select F` clean.

Diagnosis findings (section 0): none new; routes moved verbatim.

Deviations: none.

Contract change for UI: none.

## Task 12.2 implementation

Implemented `stream_reply` helper in routes/chat.py plus messages/retry/cancel routes. Preflight checks for 404/400/503/409. Backend built per request from token. Cleanup in finally.

### 12.2 update
Added bus forwarder in producer; bus events now forwarded to SSE queue and bus_q unsubscribed in finally. Gap closed.
