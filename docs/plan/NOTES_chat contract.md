# Notes — Chat contract

## Section 0 diagnosis (2026-10-30)

1. Context bug: backend already reads `project`/`project_slug`/`slug`; UI sends `{project: slug}`. Stopgap retained; full bootstrap (section 2) not yet implemented.
2. Agent profile: API server on port 8642 (default) serves model id `story-architect` = profile name. `GET /v1/models` returned `story-architect`. Raw `/v1/chat/completions` (no system msg) answered as system-owner persona because profile SOUL.md is foreign (not adapter's). Run `story-architect hermes setup --force` to install adapter SOUL. Model id now sourced from config (`hermes_profile`, default `story-architect`) instead of hard-coded string.
3. SSE captured: `tests/fixtures/sse_tool_reply.txt` (878 lines, includes `hermes.tool.progress`).
4. `previous_response_id` removed from payload; context carried by full message history + system bootstrap.

## Deviations
- Added `hermes_profile` to Config (default `story-architect`) and `STORY_ARCHITECT_HERMES_PROFILE` env override.
- SOUL.md in profile is foreign; not overwritten automatically.