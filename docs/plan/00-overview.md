# Story Architect: Refactor Plan Overview

> Read this file first, then the phase file you are working on.
> Suggested location in the repo: `docs/plan/`.

## 1. What we are doing

Story Architect is a screenwriting / story-development tool. Today it exists as a **Hermes Agent plugin**: the agent calls 11 `story_*` tools that read and write a per-project SQLite database, and a static HTML dashboard (a temp file opened with `file://`) shows the data read-only.

We are turning it into a **standalone local app that Hermes plugs into**, rather than a plugin that only exists inside Hermes.

North star, in the owner's words: *open the app, work on a project, and talk to the agent from inside the app, without juggling Hermes Desktop windows.* Eventually the user can do manually everything the agent can do.

Why not stay a plugin: a plugin only exists while Hermes runs, is coupled to Hermes' plugin API, and cannot give the UI a backend. The static dashboard cannot write anything; it never made network calls, and its "ask Hermes" buttons (`data-hermes-send`) were verified to be dead in Hermes Desktop's preview pane.

## 2. Decisions already made (do not relitigate)

| Decision | Why |
|---|---|
| The **app owns the data and the logic**; harnesses are adapters | Lets other harnesses be added later by changing setup only |
| **Local web app**: Python server + browser UI, opened in the user's browser (own tab/window) | Works without Hermes; wrapping in a desktop shell later is cheap |
| **No backward compatibility** with the old plugin or the static `file://` dashboard | Never shipped; clean build wanted |
| **Single write path**: everything that mutates the DB goes through `core/writes.py` | Already true today; keep it true for UI, agent, and future features |
| Agent integration is via **MCP over local HTTP** served by the same app process (Phase 2) | One process, one DB writer, live UI. Hermes supports HTTP MCP servers natively |
| Hermes profile/agent/SOUL/skills are created by a **Hermes adapter** in the app (Phase 2) | Setup logic lives in the app; other harnesses get their own adapter |
| Fixed default port, `127.0.0.1` only | Stable MCP config and bookmarkable URL |
| Frontend stays **vanilla JS, no build step** for now | Don't add a toolchain before it earns its place |
| No over-engineering: this is a personal project that should still look professional | See section 6 |

## 3. Target architecture

```
                 +-------------------------------+
 Browser UI ---->|  story-architect app (1 proc) |<---- Hermes (MCP over HTTP)   [Phase 2]
 (own window)    |   HTTP API  +  static UI      |<---- Hermes chat via serve    [Phase 3, UI -> Hermes]
                 |   MCP endpoint (Phase 2)      |
                 +---------------+---------------+
                                 |
                        story_architect.core  (engine, no framework imports)
                                 |
                        SQLite per project  <root>/projects/<slug>/.story/story.db
```

Layering rule (enforce it): `core` imports nothing from outer layers. `app` (HTTP) and `tools`/MCP are thin adapters over `core`. Nothing outside the Hermes adapter module may import or mention Hermes.

## 4. Target repo layout (guidance, not law)

```
pyproject.toml                 # installable package, console script `story-architect`
src/story_architect/
  core/                        # existing engine (db, writes, drafts, entity, fountain_*, ...)
  tools/                       # existing story_* tool modules (kept; wrapped by MCP in Phase 2)
  app/                         # NEW: config, server factory, routes, launcher
  web/                         # UI static files (from today's src/dashboard)
adapters/ or src/.../adapters/ # Phase 2: hermes adapter (setup + MCP registration)
tests/
docs/plan/                     # these files
```

The exact subpackage names can change if the code suggests better ones. The package must be installable and importable without path hacks.

## 5. Roadmap

| Phase | Outcome | File |
|---|---|---|
| **1** | **Standalone app**: launch it with one command, browse projects, view a project with the full dashboard, no Hermes required | `phase-1-standalone-app.md` |
| 2 | **Hermes integration**: app exposes tools via MCP; adapter creates the Hermes agent (profile, SOUL.md, skill, MCP registration). Chat still happens in Hermes Desktop | written after Phase 1 |
| 3 | **In-app chat**: chat panel talks to the Hermes agent from the app | written after Phase 2 |
| 4 | **Manual editing**: project/entity creation, script editor (scene by scene), reorder, field edits; compare-and-swap concurrency between UI and agent | written after Phase 3 |

Phases 2-4 are deliberately outlined only. Their details depend on what Phase 1 reveals.

A standing requirement from the owner: **UI work must be possible without Hermes running.** The app plus a demo project is enough to iterate on the interface.

## 6. Engineering practices

- **Layers and boundaries.** Keep the layering rule above. Adapters translate; they do not contain business logic.
- **Errors.** `core` raises exceptions with actionable messages ("Errors raise; previews return" is the existing convention). Boundaries (HTTP, MCP) translate exceptions into responses. One consistent JSON error shape for the HTTP API.
- **No dead code.** Delete rather than comment out. When something is retained deliberately for a later phase, say so in the phase file or a short comment.
- **Dependencies.** Add only what a task needs. Approved so far: `fastapi`, `uvicorn` (Phase 1); the official `mcp` SDK (Phase 2). Ask before adding anything else.
- **Config.** One module resolves configuration (precedence: CLI flag, then environment variable, then config file, then default). No scattered `os.environ` reads.
- **Logging.** Standard `logging`, no prints outside the CLI's user-facing output.
- **Typing and size.** Type hints on new code. Prefer small, single-purpose functions and modules; split files that grow unwieldy.
- **Tests.** `pytest`. Every task that adds behavior adds tests. The existing suite must stay green; adapt tests to refactors, do not delete them to make things pass.
- **Formatting.** Add `ruff` config (lint + format). Apply formatting in its own commit so diffs stay readable.
- **Git.** Work on a branch off `dev`. Small commits, one concern each, imperative messages. Commit after each task or logical group.
- **Docs move with code.** Update README/docs in the same change as behavior.
- **Security baseline.** Bind to `127.0.0.1` only; reject requests with an unexpected `Host` header (DNS-rebinding defense). Add a per-launch token/CSRF protection before the first endpoint that mutates data.
- **Frontend.** Vanilla JS under the existing `DASH` namespace; no build step, no new framework in Phase 1.

## 7. Hermes facts relevant to Phases 2-3 (from docs research; verify against the installed version before relying on them)

Installed: Hermes Agent v0.22.5, local gateway, Python 3.14.9.

- **MCP registration:** `mcp_servers:` in the profile's `config.yaml`, or `hermes mcp add`. Supports `url` (Streamable HTTP, or `transport: sse`) and stdio. HTTP servers accept `headers`; secrets via `${VAR}` resolved from the profile's `.env`. Per-server `tools.include` / `tools.exclude` act as tool gating.
- **Tool naming:** MCP tools appear as `mcp_<server>_<tool>`. Choose MCP tool names knowing that prefix (e.g. server `story`, tool `load` rather than `story_load`).
- **Profiles:** `hermes profile create <name>`; each profile is `~/.hermes/profiles/<name>/` with `config.yaml`, `.env`, `SOUL.md` (agent identity), `skills/`, sessions, memory. Select with `-p <name>` / `HERMES_HOME`. Config can be set non-interactively with `hermes config set`.
- **Skills:** a directory with `SKILL.md` (YAML frontmatter: `name`, `description`, optional `metadata.hermes.requires_toolsets` etc.). Installing into a profile = placing the directory in that profile's `skills/`.
- **`hermes serve`:** starts the headless backend. **Conflict to resolve in Phase 3:** one research pass says it is a JSON-RPC/WebSocket gateway (same as `hermes dashboard`); an earlier local check reported an OpenAI-compatible HTTP API. Phase 3 begins with a spike to find out which, before any chat UI is designed. `hermes acp` is another candidate.
- **Ports:** `hermes dashboard`/`serve` default to 9119; an API server example uses 8642. This app's default is **8731**, configurable.
- **`mcp` Python SDK:** `pip install mcp` (2.3.0 at time of research) supports Python 3.14.

## 8. How to use these documents (instructions for the implementing agent)

You have access to the real code; the planner did not. The plan was written from reports about the code, so:

1. **The code wins over the plan.** Task descriptions state intent, then give guidance. Items marked **Must** are requirements. Everything else is a suggestion; choose what fits the code.
2. **Verify assumptions first.** Each phase lists the assumptions it relies on. Check them in the first task and note any that are wrong before building on them.
3. **Don't silently deviate.** If a **Must** cannot be met, or you choose a different design, record it in `docs/plan/NOTES.md` (what, why) and continue.
4. **Stay in scope.** Do not start later phases. Do not refactor modules a task does not mention unless required for it. If you find unrelated problems, list them in `NOTES.md` instead of fixing them.
5. **Tick the checklist** in the phase file as you complete items, and keep the test suite green at every commit.

## 9. Known facts about the current code (as reported; verify)

- Plugin entry: `__init__.py` registers 11 tools, a `post_tool_call` hook, and a skills registration that points to a file that does not exist. `plugin.yaml` declares `kind: backend`.
- `core/` has no Hermes imports. `core/writes.py` is the single write path. `core/drafts.py` implements a stage/commit protocol for agent changes.
- `tools/` has 11 modules, each exposing `handler(args, **kwargs) -> str` (JSON string). They resolve the root path via helpers using `kwargs`.
- Imports rely on `sys.path.insert(0, plugin_root)` in `__init__.py` (absolute imports like `from core.constants import ...`).
- Project data: `<root>/projects/<slug>/.story/story.db` (SQLite, WAL). Scene script text lives in `sections.body` where `heading='Content'`.
- The dashboard: `src/dashboard/` (`index.html`, `css/` 9 files, `js/` 16 files) is assembled by `assemble_dashboard()` into one HTML string; concatenation order (`CSS_ORDER`, `JS_ORDER`) is load-bearing and pinned by `tests/test_dashboard_tabs.py`. Data reaches the page via three injected globals: `window.__STORY_DATA__`, `window.__SECTIONS__`, `window.__SCREENPLAY_STATS__`. JS entry: `DASH.initStory(window.__STORY_DATA__)`. The page makes no network calls.
- Dead or stale: `core/screenplay.py` (unused), `core/fountain_validator.py` (no callers, to be used in Phase 4), README (stale), `archieved/`, `plan/`.
- No Fountain writer exists (parser only); needed in Phase 4.
