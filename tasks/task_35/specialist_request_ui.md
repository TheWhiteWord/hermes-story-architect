# Specialist request — Chat UI (updated)

## Layout CSS (push-inward)
```css
/* base.css */
#app { display:flex; height:100vh; width:100%; overflow:hidden; position:relative; }
#sidebar { width:var(--sidebar-w); flex-shrink:0; ... transition:width .18s; }
#sidebar.expanded { width:var(--sidebar-w-open); }
#main { flex:1; overflow:hidden; display:flex; flex-direction:column; min-width:0; }
/* components.css */
#detail-panel { width:0; flex-shrink:0; ... transition:width .2s; position:relative; z-index:1; }
#detail-panel.open { width:var(--panel-w); border-left:1px solid var(--border); }
#detail-panel.panel-wide { width:var(--panel-w-wide); }
@media (max-width:699px){ #detail-panel { position:absolute; right:0;top:0;bottom:0; width:0; z-index:20; } #detail-panel.open { width:min(var(--panel-w),calc(100vw - var(--sidebar-w))); } }
/* statistics.css */
#stats-panel { width:0; flex-shrink:0; display:flex; flex-direction:column; ... position:relative; z-index:1; }
#stats-panel.open { width:var(--stats-panel-w); border-left:1px solid var(--border); }
@media (max-width:699px){ #stats-panel { position:absolute; right:0;top:0;bottom:0; width:0; z-index:20; } #stats-panel.open { width:min(var(--stats-panel-w),calc(100vw - var(--sidebar-w))); } }
```
#main makes room because #detail-panel/#stats-panel are in-flow flex siblings (width 0→panel-w); on narrow screens they overlay (absolute).

## Panel state
`panel-manager.js`: `DASH.openPanel()`/`closePanel()` toggle `.open` on `#detail-panel`. `navigation.js`: `DASH.switchView(view,btn)` sets `DASH.currentView`, closes panel, fires `_viewOpenedHooks`. Stats group: `DASH.switchStatsGroup(group,btn)` (in statistics.js). Open entity: stored via panel renderers; no global tracker beyond DOM `.open`.

## Tokens + components
Full `:root` block is in base.css lines 3-57:
```css
:root {
  --foreground: #e8e8e8; --muted-foreground: #8a8a8a; --accent: #7b9cf0;
  --border: rgba(255,255,255,0.1); --card: rgba(255,255,255,0.04);
  --background: #111; --panel-bg: #181818;
  --sidebar-w: 44px; --sidebar-w-open: 180px; --panel-w: 320px; --panel-w-wide: 680px;
  --radius: 6px; --gap: 12px;
  --font-size-xs: 10px; --font-size-sm: 11px; --font-size-base: 13px; --font-size-lg: 15px; --tag-gap: 4px;
  --role-protagonist: #7b9cf0; --role-antagonist: #e07070; --role-mentor: #b07be0; --role-rival: #e0a86b; --role-supporting: #6bbfb0; --role-entity: #e06b9b;
  --c-gap: #e0a86b; --c-choice: #e06b9b;
  --status-active: #6bbfb0; --status-building: #e0a86b; --status-resolved: var(--muted-foreground);
}
```
Buttons (components.css): `.btn`, `.btn-primary`, `.btn-hermes` (see components.css lines 58-72). Inputs: no global input style; `#sa-chat-input textarea { width:100%; box-sizing:border-box; resize:none }` in chat.css.

## Chat core
- `chat/service.py`: ChatService wraps backend; send() persists user msg, builds history from store, streams events, accumulates assistant text, sets backend_state on Done.
- `chat/store.py`: schema above (conversations, messages; backend_state TEXT JSON). chat.db per project at `.story/chat.db`.
- `chat/events.py`: TextDelta, ToolStarted, ToolFinished, Done, Error.
- `chat/backend.py`: ChatBackend protocol (send messages/context/backend_state -> AsyncIterator[ChatEvent]).

## Raw captures
- SSE stream: not captured live (no running gateway). Format: `event: TextDelta\ndata: {"type":"text","text":"..."}\n\n`; tool events `event: ToolStarted\ndata: {"type":"tool_started","name":"..."}`. Hermes `hermes.tool.progress` lines arrive as SSE `data:` with `event`/`type == "hermes.tool.progress"` and `data.tool`/`data.name`.
- `GET /v1/models`: not captured live. Expected `{ "data": [ { "id": "story-architect" } ] }`.
- Profile answer test ("who are you?"): not run. Gateway mode: dedicated profile `story-architect` (PROFILE const), started via `hermes -p story-architect gateway start`; API port default 8642. Model set per profile config (not in repo; Hermes profile config). Hermes lists models from its API server `/v1/models`.
- Gateway: dedicated (single profile), not shared.

## Layout and UI (prior)
- index.html: `src/story_architect/web/index.html` (full file, 542 lines) — attach if needed.
- core.js: `src/story_architect/web/js/core.js` (boot, DASH, routing).
- chat.js/chat.css: `src/story_architect/web/js/chat.js`, `src/story_architect/web/css/chat.css`.

## Context bug and backend (prior)
- HermesChatBackend: `src/story_architect/adapters/hermes/chat_backend.py` — URL `http://127.0.0.1:{hermes_api_port}/v1/chat/completions`, model `"story-architect"`, auth `Bearer <api_key>`, continuity via `previous_response_id` (backend_state) + full history resend.
- SOUL.md: `src/story_architect/adapters/hermes/assets/SOUL.md`
- SKILL.md: `src/story_architect/adapters/hermes/assets/skills/story-architect/SKILL.md`
- server.py routes: `/api/agent/state` returns `{state, detail}`; `/api/agent/start`; conversations CRUD; messages SSE; cancel. See `src/story_architect/app/server.py`.
- mcp_server.py dispatch: `src/story_architect/app/mcp_server.py` `on_call_tool` (line ~57-68).

## Drafts and tool calls (prior)
- story_draft stage result: tool `src/story_architect/tools/story_draft.py` returns `{success, draft_id, op_count, preview_md, validation, (restaged, changes)}`.
- drafts table: `drafts(id, ops, prev_ops, summary, created_at, status)` in story.db (project's own DB).
- core/drafts.py public signatures: listed in prior doc; file `src/story_architect/core/drafts.py`.
- Config: `src/story_architect/app/config.py` — fields root, port(8731), open_browser, hermes_api_port(8642), agent_autostart. config.toml at `~/.config/story-architect/config.toml`, table `[story_architect]`.