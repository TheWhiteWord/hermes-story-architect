# Story Architect

Standalone local app for story/screenplay development.

## Install

pip install -e .

## Run

story-architect --root <projects root>

## Demo data

story-architect seed-demo --root /tmp/sa-demo

## Tests

pytest

## Using with Hermes

Prerequisites: Hermes Agent v0.22.5+ installed and on PATH; a working model/provider in the default profile (so cloning produces a usable profile).

1. Start the app: `story-architect --root <projects root>` (default port 8731, 127.0.0.1 only).
2. Run `story-architect hermes setup` (idempotent; `--dry-run` to preview, `--profile NAME` to change profile). This creates the `story-architect` profile, writes SOUL.md and the skill, distributes the token, and registers the MCP server `story`.
3. Start Hermes with the profile:
4. **Host gateway must be running as a service** (so the app's agent API is reachable even when the Hermes desktop is closed): `hermes gateway install` (user-level) or `sudo hermes gateway install --system`. The app never manages the gateway lifecycle.
   - CLI: `hermes -p story-architect chat`
   - Desktop: select the `story-architect` profile (supported).
4. If the app was not running when Hermes started, start it and run `hermes mcp test` or restart Hermes; tools appear as `mcp_story_*`.
5. Diagnostics: `story-architect hermes status` (exit code non-zero on any failure).

Security: the app binds to 127.0.0.1 only; `/mcp` requires a bearer token (constant-time check) and rejects unexpected Host headers. The token is stored with 0600 permissions in the app config dir and written to the profile `.env` as `STORY_ARCHITECT_TOKEN` (never printed). The browser UI/API are token-free and read-only.

## Chat

The dashboard has an in-app chat panel (drawer) that talks to the story agent through the app, so Hermes Desktop is not required for day-to-day work. The browser never talks to Hermes directly; the app holds the API key server-side and forwards requests.

Requirements: run `story-architect hermes setup` (idempotent). Setup now also enables the API server for the `story-architect` profile on a dedicated port (default 8642, override via `STORY_ARCHITECT_HERMES_API_PORT`), creates an API key stored 0600 in the app config dir and written to the profile `.env` as `API_SERVER_KEY` (never printed), and applies a conservative toolset: the agent has no terminal/file-system write tools by default and web search/fetch is disabled. The owner can change toolsets in the profile config.

Starting the agent: use the "Start agent" button in the chat panel (or the fallback CLI command `hermes -p story-architect gateway start`), which waits up to 15s for the API to become ready. Autostart is off by default (`STORY_ARCHITECT_AGENT_AUTOSTART=1` to enable). `story-architect hermes status` now also reports API server reachability/auth and that the model id matches the profile. The app never kills a gateway it did not start.

What the agent can do: read/query project data via the `story` MCP tools (load, search, get entity, etc.) and stage/commit changes through the drafts protocol (it asks for approval before committing). What it cannot do by default: run shell commands, write files, or search/fetch the web. Chats are stored per project in `<root>/projects/<slug>/.story/chat.db` (separate from `story.db`); conversations and the last-open conversation per project are restored across reloads and app restarts. Partial replies cancelled mid-stream are kept and marked. A "Project updated / Refresh" banner appears after a committed change.

## Layout

- `src/story_architect/core/` engine (no framework imports)
- `src/story_architect/app/` HTTP server, config, routes, launcher
- `src/story_architect/adapters/hermes/` Hermes adapter (setup, status, MCP registration)
- `src/story_architect/tools/` tool modules
- `src/story_architect/web/` static UI
