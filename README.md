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
   - CLI: `hermes -p story-architect chat`
   - Desktop: select the `story-architect` profile (supported).
4. If the app was not running when Hermes started, start it and run `hermes mcp test` or restart Hermes; tools appear as `mcp_story_*`.
5. Diagnostics: `story-architect hermes status` (exit code non-zero on any failure).

Security: the app binds to 127.0.0.1 only; `/mcp` requires a bearer token (constant-time check) and rejects unexpected Host headers. The token is stored with 0600 permissions in the app config dir and written to the profile `.env` as `STORY_ARCHITECT_TOKEN` (never printed). The browser UI/API are token-free and read-only.

## Layout

- `src/story_architect/core/` engine (no framework imports)
- `src/story_architect/app/` HTTP server, config, routes, launcher
- `src/story_architect/adapters/hermes/` Hermes adapter (setup, status, MCP registration)
- `src/story_architect/tools/` tool modules
- `src/story_architect/web/` static UI
