# Chat Upgrade: Backend Contract and Integration Steps

> For the implementing agent. The UI side is written (see `chat-ui/`) and works end to end in mock mode.
> Your job: make the real backend speak the contract below, fix the context bug, and wire the UI in.
> Same working rules as before: the code wins over this document; **Must** = requirement; log deviations in `docs/plan/NOTES.md`.

## Findings from the real SSE capture (2026-10-30), take these into account

1. **The agent ran shell commands.** The capture shows 12 `terminal` tool calls (`pwd`, `ls`, `find …`) exploring the filesystem. So the story profile is **not** restricted: `toolsets: []` did not remove the built-in tools (empty most likely means "defaults"). This contradicts the Phase 3 claim that the agent cannot run shell/file tools. It is a **security issue** (a browser chat on this app can drive a shell on the owner's machine) and the first thing to fix, see section 8a.
2. **It never used the story tools.** It had no persona (the profile's `SOUL.md` is a copy of the default profile's) and no bootstrap, so it went looking for the project on disk. Both are covered by sections 0 and 2.
3. **Real Hermes tool-progress format:** `event: hermes.tool.progress` with data `{"tool", "emoji", "label", "toolCallId", "status": "running"|"completed"}`. There are no arguments, results or timings, and the current parser (which looks for `event`/`type` inside the JSON) never matched, so no tool events were ever emitted.
4. **Reasoning stream:** chunks carry `delta.reasoning_content` before the answer; the answer is in `delta.content`. Ignore `reasoning_content` (do not show it as reply text).
5. **Size:** usage reports about 300k prompt tokens for one reply (24 tool round trips with a large context). Keep an eye on it once the agent uses the story tools directly; it should drop sharply.

## 0. Do these first (they unblock testing)

- [x]  **Context bug.** `chat.js` sends `context: {project: slug}`, but `HermesChatBackend` reads `project_slug` / `slug` / `project_name`, so the agent never learns the project. Replace this whole mechanism with section 2 (bootstrap). Until then a one-line stopgap is fine.
- [x]  **Which agent answers?** `hermes_api_port` defaults to 8642, which is Hermes' default-profile port. Verify that the port the app calls is the **story profile's** API server. Capture and paste into `NOTES.md`: `GET /v1/models` output (key redacted), and the reply to a raw `/v1/chat/completions` call with *no* system message asking "Who are you and what do you do?" (it should answer as the Story Architect persona from `SOUL.md`; if not, we are talking to the wrong profile or the persona isn't loaded). Make the model id come from config (profile name), not a hard-coded string.
- [x]  **Capture one real SSE stream** for a reply that uses a tool (raw lines, including `hermes.tool.progress`). The current tool-event parsing in `chat_backend.py` is guesswork. Save the capture as a test fixture.
- [x]  `previous_response_id` is a `/v1/responses` field; on `/v1/chat/completions` it is probably ignored. Since the full history is resent anyway, confirm which mechanism actually carries context and remove the dead one. The bootstrap in section 2 must be sent on **every** request (it is not stored in the history).

## 1. Wire the UI in

Files are in `chat-ui/`: `css/chat.css`, `js/chat-api.js`, `js/chat-md.js`, `js/chat-render.js`, `js/chat-app.js`.

- [x] Replace `web/css/chat.css` with the new one. Put the four JS files in `web/js/` (or `web/js/chat/`; adjust paths).
- [x] Delete the old `web/js/chat.js`. In `index.html` replace its `<script>` with the four new ones **in this order**, after `script-view.js` and before `DASH.boot()`: `chat-api.js`, `chat-md.js`, `chat-render.js`, `chat-app.js`. Update the script/CSS order pin (the test and `JS_ORDER`).
- [ ] The UI builds its own DOM inside `#app` after the last panel and wraps `DASH.initStory`; no other HTML changes. It also overrides `DASH.askAgent`.
- [x]  **Mock mode:** open `http://127.0.0.1:8731/?mock=1#/p/<slug>` (query string before the hash). Everything works without a gateway. Use it to check the layout against the real dashboard first.
- [ ] Optional, small: set `DASH.panelContext = {type, id, name}` wherever an entity panel opens (and clear it in `DASH.closePanel`). The "attach" menu uses it to give the agent the entity id; without it the UI sends only the visible label.

## 2. Context for the agent

- [x] Create `chat/context.py` (harness-agnostic, no Hermes import):

`build_bootstrap(project_slug, project_name, attachments) -> str`, sent as the system/instructions message on every request, never persisted, never shown. Starting text (refine freely):

> You are working inside **Story Architect**, a local screenwriting and story-development app. The user has the project "{name}" ({slug}) open in the app and is talking to you in its side panel. Read and change the project only through the story tools (MCP server "story"); don't guess project facts. Propose changes by staging a draft: the app shows each draft to the user as a card with Approve and Reject buttons. Commit only after the user approves (you will be told), unless they explicitly ask you to apply changes directly. Never claim a change was made unless a tool confirmed it. Use `dashboard_link` when pointing the user at a place in the app.
> {if attachments:} The user attached these parts of the app to their message: {labels with kind/id}. Use the tools to read them if relevant.

- [x] `ChatService` builds it from the request `context` (`project`, `attachments`) plus the project name lookup, and passes the final string to the backend as a separate `instructions` argument. The backend adds no persona text of its own.
- [x]  **Persona install:** `hermes setup` refuses to overwrite a `SOUL.md` it did not write, but `hermes profile create --clone` copies the default profile's `SOUL.md`, so the story profile always looks "foreign". Make setup treat a `SOUL.md` that is byte-identical to the default profile's as replaceable (back it up first), and still refuse genuinely custom ones without `--force`. For the owner's current profile, running `story-architect hermes setup --force` (it backs up the old file) is fine.
- [x]  Update `SOUL.md` and `SKILL.md` to match: the app shows drafts as approval cards; the agent is told when a draft is approved or rejected; the agent may still commit by itself when asked.

## 3. Reply stream (SSE) from `POST .../messages` and `POST .../retry`

- [x] Each event is `event: <type>` + `data: <json>` where the JSON always has `type`. The UI also still understands the old `TextDelta` / `ToolStarted` / `ToolFinished` events, but move to these:

| type | payload |
|---|---|
| `text` | `{text}` delta |
| `tool` | `{id, name, status: "started"\|"finished"\|"failed", args?, result_preview?, duration_ms?}`; the same `id` is sent again to update it |
| `draft` | `{draft: <draft snapshot, see 5>}`; sent when a draft is staged, re-staged, committed or discarded during the reply |
| `done` | `{message_id}` |
| `error` | `{code, message, retryable}` (`agent_not_configured` / `agent_unavailable` make the UI re-check the agent) |
| `cancelled` | `{}` |

## 4. Tool events come from the MCP server, not from Hermes

- [x]  In `mcp_server.on_call_tool`, publish `started` (id, name, args) before the handler and `finished`/`failed` (+ duration, `result_preview` truncated to about 800 chars) after it, to a small in-process bus.
- [x] The reply route subscribes while a reply is active and forwards bus events as `tool` events. MCP calls carry no conversation id, so attribute them to the **single active reply**; calls made while no reply is active (for example from Hermes Desktop) are ignored.
- [x]  Hermes' own `hermes.tool.progress` events (real format above) are the source for tools that are **not** story tools: map them to `tool` events with `id = toolCallId`, `name = tool`, `label = label`, `status: running -> started, completed -> finished` (treat `failed`/`error` as `failed`). For names starting with `mcp_story_` ignore them (the bus is richer). The UI shows `label` as the hint when there are no args.
- [x] When the finished tool is `draft` and its result contains a staged/re-staged/committed/discarded draft, also emit a `draft` event (section 5).

## 5. Drafts as approval cards

- [x] **Snapshot** (JSON the UI renders; also what is stored in the message):
`{id, status: "open"|"committed"|"discarded"|"failed", summary, created_at, changes: [...], warnings: [str], error?}`
where each change is `{kind: "create"|"edit"|"delete"|"reorder", entity_type, entity_id?, label?, summary, fields?: [{field, before, after}], count?}`.

- [x]  Add a public, structured sibling of `render_preview_md` in `core/drafts.py` (for example `describe_ops(project_path, ops) -> list[dict]`) producing `changes`. Edits take `before` from the same lookup `_render_edit` uses (`writes.current_values`); every op already carries a `summary`. `warnings` come from `validate_shape`.
- [ ]  **Discarding deletes the draft row**, so card state cannot live in `drafts`. Persist the snapshot **inside the chat message** (section 6) and update it there on every status change.

**Endpoints**
- [x]  `POST /api/projects/{slug}/drafts/{id}/approve` `{conversation_id}`: `core.drafts.commit`. Success returns `{status: "committed", draft: <snapshot>}`. A partial failure (`success: false`, `draft_kept`) returns `{status: "failed", draft: <snapshot with error and what landed>}` with HTTP 200. A missing/changed draft returns 409 with a clear message (the agent may have re-staged or discarded it).
- [x]  `POST .../drafts/{id}/reject` `{conversation_id}`: `core.drafts.discard`; returns `{status: "discarded", draft: <snapshot>}`.
- [x]  Both update the stored snapshot in that conversation's message and add a **hidden** note to the conversation ("Draft d-… was approved by the user and committed" / "…rejected") that is included in the history sent to the agent on the next turn. No extra LLM call. The agent keeps its ability to commit by itself; nothing here removes it.

## 6. Store changes (`chat.db`, additive only)

- [x] `messages` gains: `status` (`complete|partial|cancelled|error`, default `complete`), `tools` (JSON list of tool entries), `drafts` (JSON list of snapshots), `attachments` (JSON), `hidden` (0/1), `error` (text). Migrate with `ALTER TABLE … ADD COLUMN` if missing.

- [ ] The assistant message is persisted at the end of the reply **and also when cancelled or failed** (partial text kept, status set).
- [x] `GET .../conversations/{cid}` returns visible messages `{id, role, text, status, created_at, tools, drafts, attachments, error}`; hidden ones are omitted from the response but included when building the backend history.
- [x] `GET .../conversations` returns `{id, title, updated_at}` (title derived from the first user message).

## 7. Retry

- [x] `POST .../conversations/{cid}/retry`: delete the last assistant message (and hidden notes after the last user message), then run the last user message again, streaming exactly like `messages`, without adding a new user message. 409 if a reply is in progress; 400 if there is no user message.

## 8. Agent state and settings

- [x]  `GET /api/agent/state` keeps `{state, detail}`; add `starting` while a start is in progress.
- [x] `GET /api/agent/settings` → `{state, detail, profile, port, autostart, can_stop, model: {current, options|null}}`.
- [x] `PATCH /api/agent/settings` accepts `autostart` (bool) and `model` (string).
- [x] `POST /api/agent/stop` (and `start` as today). **Safety:** stopping must only ever stop a gateway dedicated to the story profile. If the profile is served by a shared/multiplexed gateway that also serves other profiles, set `can_stop: false` and make `stop` return 409. Do not stop a gateway you cannot prove is dedicated. Never touch other profiles.
- [x] `autostart` must be writable at runtime, but `config.toml` is read-only today. Prefer a small `state.json` next to it for UI-writable settings (no new dependency); precedence: CLI/env, then `state.json`, then `config.toml`, then defaults. Your call if you see a better way; note it.
- [x] **Model list (spike, optional):** find the supported way to list models available to the profile and to set the profile's model non-interactively (`hermes -p <profile> config set model.model …`, then whatever restart is needed). If it cannot be done reliably, return `options: null` (the UI then shows the current model read-only and hides the selector).

### 8a. Restrict the story agent's built-in tools (security, do this early)

**Must:** through the story profile's API server the agent can use **only** the story MCP tools (plus whatever the owner explicitly enables later). It must have no terminal, no file read/write/patch, no code execution and no browser/web tools by default.
- [x] `toolsets: []` does not do this (see the capture). Find the configuration that actually does: for example an explicit allow-list containing only the MCP toolset (`mcp-story`), and/or `agent.disabled_toolsets` for the built-ins. Verify by experiment, not by reading config: through `/v1/chat/completions`, ask the agent to run `pwd` and to read a file; it must have no such tool. Record the working keys and the test in `NOTES.md`.
- [x] Apply it in `hermes setup` (idempotent, same protections as before) and make `hermes status` **fail** when the profile still exposes built-in tools. If Hermes can list the effective toolset for a profile, use that for the check.
- [x] Tell the owner what changed; web search stays off until they decide.

## 9. Tests (minimum)

- [x] Bootstrap contents (with and without attachments); stream events end to end with a fake backend (`text`, `tool` update by id, `draft`, `done`, `error`, `cancelled`); persisted tools/drafts/status including a cancelled partial; approve success / partial failure / stale draft; reject; hidden note reaches the next backend request but not the conversation response; retry replaces the last reply; the MCP tool bus attributes calls only while a reply is active; `can_stop` false path; request protection (origin + custom header) on all new POST/PATCH routes.

## 10. Acceptance

- [x]  In mock mode (`?mock=1`) the panel opens/collapses, pushes the dashboard inward, and doesn't overlap any panel.
- [ ]  Real mode: ask "What is this project about?"; the agent answers as the Story Architect for the open project, using tools, and the tool cards show real names, arguments, results and timings.
- [ ]  Ask for a change: a draft card appears; **Approve** commits it (the dashboard shows it after "Project updated → Refresh"); the card flips to Approved; the next message shows the agent knows.
- [ ]  **Reject** discards; the card flips to Rejected; the agent is told.
- [ ]  Attach the open entity or view with "+", ask a question about it, and the agent's bootstrap/instructions include it (verify in the captured request).
- [ ]  Stop mid-reply keeps the partial text marked "Stopped"; Retry reruns it.
- [ ]  Settings: status, start/stop (with the shared-gateway safety), autostart toggle persists across app restarts; model selector works or is hidden.
- [ ]  A request to any new POST/PATCH route from a foreign origin or without the custom header is rejected.
- [ ]  Asking the story agent through the app to run a shell command or read a file is impossible (no such tool), and `hermes status` fails if that ever regresses.
- [ ]  Suite green, ruff clean, no Hermes mentions outside the adapter, docs, and plan files.

## 11. Report back

Short summary, the diagnosis findings from section 0, deviations, and any contract change you made (tell the owner so the UI can follow).

Your assistant is right to ask for details instead of guessing. What it describes looks like a bad merge in `server.py`: the body of the messages route ended up inside the project-events generator, which would also explain why the `/messages` route "isn't wired". Below is a new section to paste into the contract file as **Section 12**. It's written so the agent can implement and test the route without further input from me.


## 12. Server wiring: repair `server.py` and implement the reply routes

**Context.** `server.py` is in a broken state (see "Repair" below). The reply stream routes (`messages`, `retry`) and `cancel` must be rebuilt against the contract, sharing one streaming helper. Everything the UI calls is defined in sections 3 to 8; this section says how to wire it.

### 12.1 Repair first

- [x] `GET /api/projects/{slug}/events` must be **only** the DB-change feed: poll `PRAGMA data_version` (about 1 s) and emit `event: update`. Nothing chat-related belongs in it. It currently references `cid`, `service`, `pp`, `text`, `context`, which are undefined there.
Do not patch blind. Use git history (`git log -p -- src/story_architect/app/server.py`, or diff against the last commit before the chat work) to see what each route looked like when it was correct, restore each one, and re-apply only the intended changes.
- [x] `ruff check --select F` on `server.py` and fix **every** finding. `F821` (undefined name) would have caught this. Keep `--select F` clean from now on, even though the repo's other ruff findings are pre-existing.
- [x] `server.py` has grown large. While rebuilding, split it into `APIRouter` modules (suggested: `routes/projects.py`, `routes/chat.py`, `routes/drafts.py`, `routes/agent.py`), with `create_app` only assembling them and the middleware. Keep this a mechanical move; do not change behavior in the same commit.

### 12.2 One streaming helper for `messages` and `retry`

Both routes call the same helper, `stream_reply(...)`, which returns a `StreamingResponse` (`text/event-stream`). Required behavior:

- [x] **Preflight (plain JSON errors, no stream):** unknown project 404; empty text 400; backend not configured (no API key) 503 `agent_not_configured`; a reply already active anywhere in the app 409 `reply_in_progress`. One active reply app-wide is intentional: tool-bus attribution depends on it.
- [x] **Backend per request, not at startup.** Build `HermesChatBackend` from current config each time (`token.load_api_key()`, `hermes_api_port`, `hermes_profile`). A key created after the app started must work, and a missing key must produce the 503 above rather than a failure at app start.
- [x] **Producer task plus queue.** Run the reply in its own `asyncio` task that puts contract-shaped events on an `asyncio.Queue`; the response generator only reads the queue and yields SSE. Two producers feed the queue: the backend stream (mapped, see 12.3) and the tool bus (`app/tool_bus`, subscribed for the duration of the reply, unsubscribed in `finally`). If the bus can publish from a non-loop thread, use `loop.call_soon_threadsafe`.
- [x] **Cancellation.** `POST .../cancel` cancels the producer task. The producer's `CancelledError` handler enqueues `{"type": "cancelled"}` with `put_nowait` and re-raises. A client disconnect (the UI's Stop aborts the fetch) must also cancel the task (do it in the generator's `finally`). **Never `yield` inside an `except CancelledError` / `GeneratorExit` handler** (the current code does; it raises "async generator ignored GeneratorExit").
- [x] **Persistence must survive cancellation and failure.** The assistant message is saved with `text`, `tools`, `drafts` and `status` (`complete` / `cancelled` / `error`, plus `error` text) in every outcome. Use synchronous store calls in `finally` (no awaits after cancellation). The route collects `tool` and `draft` events from the bus as they pass and hands them to the service/store for persisting (their final state, deduplicated by `id`).
- [x] **Cleanup:** always remove the reply from `active_replies` and unsubscribe from the bus in `finally`.

### 12.3 Event mapping (route layer), the UI contract

Each SSE message is `event: <type>` + `data: <json including "type">`:

| Source | SSE `type` and payload |
|---|---|
| `TextDelta` | `text` `{text}` |
| backend `ToolStarted/ToolFinished` (non-story tools only) | `tool` `{id, name, status: started\|finished\|failed, label}` |
| tool bus `started/finished/failed` | `tool` `{id, name, status, args, result_preview, duration_ms}` (same `id` reused for updates) |
| tool bus draft event | `draft` `{draft: <snapshot>}` |
| `Done` | `done` `{message_id}` (message already persisted) |
| `Error` | `error` `{code, message, retryable}`: `agent_unavailable` + retryable when the gateway is unreachable, `agent_error` otherwise |
| cancellation | `cancelled` `{}` |

`retry` uses the **same** helper and mapping (the earlier "minimal" mapping must go). Its only difference is the preflight and the start: delete the last assistant message and hidden notes after the last user message, then run the last user message again without adding a new one.

### 12.4 Routes the UI calls (confirm each exists and matches)

`GET/POST /api/projects/{slug}/conversations` (list returns `{conversations:[{id,title,updated_at}]}`, create returns `{id}`); `GET/DELETE .../conversations/{cid}` (get returns `{id,title,messages:[{id,role,text,status,created_at,tools,drafts,attachments,error}]}`, hidden omitted); `POST .../messages` body `{text, context:{project, attachments:[{kind,id,label}]}}`; `POST .../retry`; `POST .../cancel`; `POST .../drafts/{id}/approve|reject` body `{conversation_id}` returning `{status, draft}`; `GET .../events`; `GET /api/agent/state`, `GET|PATCH /api/agent/settings`, `POST /api/agent/start|stop`. All POST/PATCH/DELETE go through the existing origin + `X-Story-Architect` header check.

### 12.5 Tests (required for this section)

The broken wiring went unnoticed because nothing exercised the real routes, so this section needs a small route-level suite using `TestClient` and `FakeBackend`, not unit tests of the pieces:

- `messages` streams `text` → `done`, and the conversation afterwards contains the user and assistant messages with `status: complete`.
- A tool-bus `started`/`finished` pair and a `draft` event published during the reply arrive as `tool` / `draft` events and are persisted in the assistant message.
- Cancelling mid-stream (via the cancel route, and via closing the stream) ends with `cancelled` and persists the partial text with `status: cancelled`; the app accepts a new reply afterwards.
- A backend error yields an `error` event and persists `status: error`.
- A second reply while one is active returns 409; missing key returns 503.
- `retry` replaces the last assistant message and does not add a user message.
- `approve` and `reject` update the stored snapshot, add a hidden note, and the next backend request includes that note; a stale draft returns 409.
- `/events` emits `update` after a DB change and does not touch chat state.
- POST without the custom header, or from a foreign origin, is rejected on the new routes.

### 12.6 Things to confirm while you're in there (report, don't redo)

- [ ] `can_stop: true` was set because the gateway is "dedicated per profile". Confirm that with evidence (`hermes -p story-architect gateway status`, and whether the gateway process also serves other profiles). If it's shared, `can_stop` must be false.
- [ ] `hermes status` fails when built-in tools are exposed. Confirm with the real `pwd` test from section 8a that it can't be done through the chat.