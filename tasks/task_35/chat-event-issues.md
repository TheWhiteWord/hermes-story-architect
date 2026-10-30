# Chat event handling issues (debug notes)

## 1. "No reply was received" on first send, works on Retry

Symptom: first message yields thinking then "No reply was received.";
Retry on the same conversation returns the answer.
Hermes desktop shows the same conversation completed successfully (no failure).

Likely area: src/story_architect/app/routes/chat.py stream_reply queue draining
(lines ~96-127) and src/story_architect/adapters/hermes/chat_backend.py.
The first send adds a user + assistant message via service.send; retry uses
service.retry + prepare_retry. Difference in persistence/state may cause the
stream to close early on first send.

Unverified: whether TextDelta events are actually yielded on first send
(add server-side logging to confirm).

## 2. Duplicate tool entries

For one tool call (e.g. story_load), the UI shows two entries:
- "mcp_story_load" with no details
- "load" with full details

Likely area: chat_backend.py yields ToolStarted for both
delta.hermes.tool and top-level tool events; route maps both to SSE "tool"
events. Need dedup by tool call id.

## 3. Draft card mismatch with mockup

The draft card rendered in-app differs from the mockup demo. Likely a
rendering/CSS issue in chat-render.js / chat-app.js, not event handling.

## 4. 422 on /api/projects/demo/events

"GET /api/projects/demo/events HTTP/1.1 422 Unprocessable Entity" and
"can't establish a connection". Likely an events endpoint expecting params
not provided. Unverified which route.
