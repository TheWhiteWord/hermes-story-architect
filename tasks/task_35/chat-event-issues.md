# Chat event handling issues (debug notes)

## 1. "No reply was received" on first send, works on Retry — RESOLVED

Root cause: not the stream-draining code. The agent API was unreachable
because the host gateway was not serving the `story-architect` profile
(stale `gateway.parked` marker + no host gateway service + missing default
`API_SERVER_KEY`). First send's stream closed early with no deltas; Retry
succeeded only once the profile got served.

What was done: cleared the parked marker in setup, removed the standalone
`gateway run` spawn that was re-parking the profile, installed the host
gateway as a user systemd service, re-added a default `API_SERVER_KEY`.

Result: agent ready on first send; reply streams normally. No change to
chat.py or chat_backend.py.

## 2. Duplicate tool entries

For one tool call (e.g. story_load), the UI shows two entries:
- "mcp_story_load" with no details
- "load" with full details

Likely area: chat_backend.py yields ToolStarted for both
delta.hermes.tool and top-level tool events; route maps both to SSE "tool"
events. Need dedup by tool call id.

## 3. Draft card mismatch with mockup

The draft card rendered in-app differs from the mockup demo. THey appear to be agent self made reports, and are identical to the ones in hermas desktop.
Likely a rendering/CSS issue in chat-render.js / chat-app.js, not event handling.

## 4. 422 on /api/projects/demo/events

"GET /api/projects/demo/events HTTP/1.1 422 Unprocessable Entity" and
"can't establish a connection". Likely an events endpoint expecting params
not provided. Unverified which route.
