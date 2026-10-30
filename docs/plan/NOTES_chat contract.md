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
