# Phase 3: In-App Chat

> Prerequisites: `00-overview.md`, Phases 1, 1b and 2 complete. Same working rules: the code wins over the plan; **Must** = requirement, **Guidance** = adapt freely; log deviations in `docs/plan/NOTES_Phase_03.md`.

## Outcome

The owner opens the app in the browser, opens a project, and chats with the story agent in a panel inside the app. Replies stream in, tool use is visible as compact progress indicators, conversations persist per project and can be resumed, and the dashboard's "ask the agent" buttons now send their prompt straight into the chat. Hermes Desktop is no longer needed for day-to-day work; it still works in parallel with the same agent profile.

## Out of scope

Manual editing/script editor, approval UI for drafts (approval stays conversational), rich markdown/media rendering, attachments, voice, other harness backends (only the interface that will allow them), improving in-place re-rendering of the dashboard.

## Key finding from docs research (verify in Task 1)

The earlier doubt about `hermes serve` is resolved: `hermes serve` is the headless backend for the Desktop app and dashboard, **not** the integration surface. The integration surface for external apps is the gateway's **API Server**: an OpenAI-compatible HTTP endpoint (default `127.0.0.1:8642`, one port per profile) with:

- `POST /v1/chat/completions` (stateless, streaming with an extra `hermes.tool.progress` event for tool starts)
- `POST /v1/responses` (server-side conversation state)
- a runs API and sessions API for long-form control
- `GET /v1/models`, `/v1/capabilities`, `/v1/health`
- a `system` message / `instructions` field is **layered on top** of the profile's own prompt
- the model id advertised equals the profile name
- it exposes the agent's **full toolset, including terminal**, so access and toolsets must be restricted for this profile

Enabling it is done through gateway configuration/env vars of the profile; the exact names are in the Hermes docs ("API Server") and must be verified against v0.22.5.

## Design decisions for this phase

- **Browser never talks to Hermes.** The browser calls the app; the app calls Hermes. The Hermes API key stays server-side. This also keeps the harness swappable.
- **A small harness-agnostic chat interface** in the app (not a framework): a `ChatBackend` protocol with one core operation, roughly "send a user message in a conversation (with context) and yield a stream of events": text delta, tool started/finished (name only), done (with optional backend state to remember), error. Hermes is the first implementation, living in `adapters/hermes/`. Everything else in the chat feature is harness-agnostic.
- **The app stores its own transcripts** per project (so history, display, and resume do not depend on Hermes). Agent-side continuity (Hermes remembering the conversation) uses whatever mechanism Task 1 shows works best (`/v1/responses` chaining or resending history); the backend-specific continuation state is stored opaquely with the conversation.
- **Project context** is sent with each message (at minimum the current project slug; optionally the current view/selected entity) so the agent knows what the owner is looking at. Use the supported "instructions/system" layering, not prompt hacks.
- **First mutating endpoints:** the overview's rule applies now. Non-GET routes must be protected against cross-site requests (see Task 4).
- **The story agent is restricted.** Its profile does not need terminal or file-system tools to do its job. Task 3 configures conservative toolsets.

## Assumptions to verify (Tasks 0-1)

- [ ] C1. API server can be enabled per profile with its own port and an API key, and runs as part of that profile's gateway.
- [ ] C2. MCP tools configured for the profile (our `story` server) are available to the agent when it is driven through the API server.
- [ ] C3. Streaming works as documented and tool-start events (`hermes.tool.progress`) arrive in a form we can show (tool name at least).
- [ ] C4. Conversation continuity: how to continue a conversation (`previous_response_id` or equivalent, or sessions API) and what happens on gateway restart.
- [ ] C5. How to restrict the profile's toolsets (config keys) and that doing so does not break MCP tools.
- [ ] C6. How to start/stop a profile's gateway non-interactively (`hermes -p <name> gateway start|status|stop`, behavior on this machine: systemd/s6 or bare process).
- [ ] C7. Where Hermes puts the final assistant text vs. tool-call chatter in the stream, so the UI can render clean replies.

## Tasks

### Task 0: Baseline and housekeeping

**Must**
- Re-run suite, ruff, and a quick manual check that Phase 2 still works (app + MCP + Hermes). Record in `NOTES_Phase_03.md`; fix regressions first.
- Update `docs/plan/00-overview.md`: mark Phase 2 done; replace the `hermes serve` conflict note with the finding above; note the 8731 app port vs Hermes API ports.

**Checklist**
- [x] Baseline recorded, ruff status included
- [x] Overview updated

---

### Task 1: Spike on the Hermes API server

**Intent:** learn the real behavior behind C1-C7 before designing around it.

**Must**
- Use a **scratch profile** (not the owner's default or the real story profile). Enable the API server on a free port with a key; start its gateway.
- With `curl` or a tiny script, exercise: health/models/capabilities; a non-streaming and a streaming chat call; tool use through our `story` MCP server (app running, scratch profile registered like in Phase 2, tools allowed); conversation continuity with at least the mechanism the docs recommend; the instructions/system layering; a toolset restriction.
- Record in `NOTES_Phase_03.md`: the exact config/env names that worked, port and auth behavior, a sample of the streaming events (including a tool event), how continuity works and survives a gateway restart, how to start/stop/status the gateway, and a recommended backend design (which endpoint, which continuity mechanism).
- Remove all scratch artifacts afterwards.

**Checklist**
- [x] C1-C7 answered in `NOTES_Phase_03.md` with evidence
- [x] Recommended endpoint and continuity mechanism chosen
- [x] Scratch profile and processes removed

---

### Task 2: Chat core (harness-agnostic)

**Intent:** conversations, persistence, and the backend interface, with no web framework and no Hermes.

**Must**
- A `chat` package (name flexible) providing:
  - the `ChatBackend` protocol and a small event model (text delta, tool started/finished, done, error) as plain dataclasses/typed dicts;
  - a conversation store: conversations and messages per project, persisted in SQLite. Keep it **separate from `story.db`** (for example `<project>/.story/chat.db`) so story data and its backups are not affected. Messages store role, text, timestamp, and optional metadata (such as the tool names used). A conversation stores a title, timestamps, and an opaque backend-state field.
  - a service that ties them together: create/list/get conversations, add the user message, stream the backend's events while accumulating the assistant message, persist the final message (and the partial one if the stream is cancelled or fails, marked as such), and save the backend state.
- No imports of FastAPI, Starlette, or Hermes in this package.
- A fake in-memory backend for tests.

**Guidance**
- Keep the schema tiny (two tables). Titles can be derived from the first user message. No search, tags, or branching.
- Streaming is async (async iterator). Store access can be sync behind a thread offload if simpler.

**Checklist**
- [x] Interface, events, store, service
- [x] Tests with the fake backend: new conversation, multi-turn, cancellation mid-stream, backend error, reload from disk, two projects isolated

---

### Task 3: Hermes chat backend and setup extensions

**Must**
- `adapters/hermes/chat_backend.py` implementing `ChatBackend` against the profile's API server using the endpoint and continuity mechanism chosen in Task 1. Streaming parsed with the project's existing HTTP client (`httpx`-family) rather than a new dependency. Map the tool-progress events to the app's tool events, and ignore unknown event types gracefully.
- Project context passed through the layered instructions/system field, built from the context the UI sends (minimum: project slug and display name).
- Extend `hermes setup` (idempotent, dry-run aware, same overwrite protections as before) so that it also: enables the API server for the story profile on a dedicated port; creates the API key (stored 0600 in the app's config dir and written to the profile's `.env`, never printed); applies the conservative toolset configuration (see below).
- **Toolset restriction:** the story profile must not have terminal or file-system write capabilities by default. Decide from Task 1 which config keys do this, apply them in setup, and list in `NOTES_Phase_03.md` what the agent can and cannot do. Web search/fetch is the owner's call: default to disabled and make the setting easy to change; ask the owner in the report.
- Extend `hermes status` with: API server reachable and authenticating, model id matches the profile, gateway running.
- Config: add the API port and key location to the app's config module (same precedence rules as other settings).

**Checklist**
- [x] `HermesChatBackend` implemented
- [x] Setup enables API server, key, restricted toolsets; still idempotent; still never touches other profiles or the default `SOUL.md`
- [x] Status checks extended
- [x] Tests with a fake API server (local test server emitting recorded streaming events from Task 1): text streaming, tool events, continuity state round trip, auth failure, unreachable server, malformed events

---

### Task 4: Chat HTTP routes and request protection

**Must**
- Routes under the project (names flexible):
  - list/create conversations, get a conversation with its messages, delete a conversation;
  - send a message: `POST` that returns a **streamed response** (Server-Sent Events formatted body) carrying the event stream (text deltas, tool events, done/error); the browser reads it with `fetch` streaming, since `EventSource` cannot POST;
  - cancel an in-flight reply (a dedicated route, or closing the connection; make sure the backend request is actually cancelled and the partial message saved).
- **Cross-site protection for all non-GET routes** (applies to the new routes and anything mutating added later): require an `Origin` header matching the app's own origin (when present) **and** a custom request header that cross-site pages cannot send without a CORS preflight (which the app never allows). Respond 403 otherwise. Keep the existing `Host` validation. Implement it once, as middleware or a dependency, with tests.
- Backend selection through app config/state (only Hermes exists; keep the seam small). When the backend is unreachable or not configured, return a clear, structured error that the UI can turn into guidance.
- One reply at a time per conversation; a second send while streaming returns a clear error.

**Checklist**
- [ ] Routes implemented and thin (logic stays in the chat service)
- [ ] Origin + custom header protection with tests (missing/foreign origin, missing header, GET unaffected)
- [ ] Streaming test using the fake backend; cancellation test
- [ ] Error shape consistent with the rest of the API

---

### Task 5: Agent availability

**Intent:** "open the app and it works" as far as is reasonable.

**Must**
- The server can report the agent state (not configured / gateway stopped / API unreachable / ready) from a cheap check.
- An endpoint, and a UI action ("Start agent"), that starts the profile's gateway using the supported command and waits for the API to become ready, with a timeout and a clear failure message. Starting must be a deliberate user action or an explicit opt-in config setting (`agent.autostart`), never silent by default.
- No orphaned processes owned by the app on shutdown unless the gateway was started in a way that is meant to persist (follow what Task 1 learned about how gateways are supervised; do not kill a gateway the app did not start).

**Checklist**
- [ ] State check and start endpoint
- [ ] Optional autostart setting, default off
- [ ] Tests with a fake process wrapper; documented behavior on shutdown

---

### Task 6: Chat UI

**Must**
- A chat panel inside the dashboard page (docked side panel or drawer that can be opened/closed without losing the current view), available whenever a project is open. Contains: conversation list (switch, new, delete), message list, input with Enter-to-send (Shift+Enter for newline), Stop button during a reply.
- Streaming rendering: assistant text appears incrementally; tool use shows as small, quiet indicators (for example "Looking up scene…") that settle when finished.
- Text rendering is **safe**: all content is escaped. Support a minimal, in-house subset (paragraphs, line breaks, bold/italic, lists, inline and fenced code). If you prefer a vendored markdown library, justify it in `NOTES_Phase_03.md` and make sure its output is sanitized.
- States: agent not configured / not running (with the "Start agent" action and the exact CLI command as fallback hint), connection lost, send failed (retry), empty conversation.
- `DASH.askAgent(text)` now opens the panel, starts (or continues) a conversation, and sends the text with the current project context. The 13 buttons need no other change.
- The panel sends the current project context with every message (minimum project slug; include the current tab/view if cheaply available).
- After a reply completes, if the project changed, the existing "Project updated / Refresh" banner is the mechanism for seeing the changes (the reload behavior from Phase 2 is acceptable).
- All requests carry the custom header required by Task 4.
- Conversations persist across page reloads and server restarts; the last-open conversation per project is restored.

**Guidance**
- Follow the existing vanilla/`DASH` conventions and CSS tokens; put the chat code in its own JS and CSS files, added in the load-bearing order in `index.html` (and update the order-pinning test).
- Don't build a design system. A clean, readable panel is enough; visual polish comes later.

**Checklist**
- [ ] Panel, list, input, stop
- [ ] Streaming + tool indicators
- [ ] Safe rendering with tests (an XSS-style string renders as text)
- [ ] State handling (not running, lost, failed)
- [ ] `DASH.askAgent` wired to chat
- [ ] Persistence/restore verified manually
- [ ] No console errors; manual pass of all tabs still fine

---

### Task 7: Docs

**Must**
- README: "Chat" section (how it works, requirements, starting the agent, what the agent can/cannot do, where chats are stored, how to change the agent's permissions), and update the setup section for the new `hermes setup` behavior and the extended `status`.
- Update the layout section and tick checklists in `docs/plan/`.

**Checklist**
- [ ] README updated
- [ ] Plan checklists ticked

---

## Definition of done (acceptance)

1. On a clean state: `story-architect hermes setup` (twice; the second reports no changes), start the app, `story-architect hermes status` all green.
2. Open the demo project in the browser. Open chat. If the agent isn't running, use "Start agent" and see it become ready.
3. Ask a question about the project; the reply streams, tool-use indicators show, and the answer matches the data.
4. Ask the agent to stage and commit a small change (it should ask for approval first, per the skill). After it commits, the "Project updated" banner appears; refreshing shows the change.
5. Click one of the dashboard "ask agent" buttons; the prompt appears in the chat and the agent answers.
6. Reload the page and restart the app: the conversation is still there and can be continued with the agent keeping context.
7. Stop a reply mid-stream: it stops, and the partial text is kept and marked.
8. A request to a chat route from a foreign origin or without the custom header is rejected; a wrong `Host` is rejected.
9. Confirm the story profile cannot run shell commands or write files (ask it to try).
10. Suite green, ruff clean, no Hermes mentions outside the adapter, docs, and plan files.

## Report back

Short summary, final test counts, deviations, the Task 1 findings (especially endpoint, continuity mechanism, event format, toolset keys), the list of what the agent can and cannot do, and the question for the owner about web search. Phase 4 (manual editing) will begin with a design review of the editor and the concurrency approach; note anything learned about how often the agent and the UI may touch the same data.
