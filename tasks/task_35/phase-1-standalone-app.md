# Phase 1: Standalone App

> Prerequisite: read `00-overview.md` (goal, decisions, practices, how to treat this plan).

## Outcome

From a clean terminal, with **Hermes not installed or running**:

```
pip install -e .
story-architect --root <projects root>
```

opens the app in the browser. The user sees a list of their projects, opens one, and gets the full existing dashboard (all tabs, same data as today), served live from the database. Reloading the page shows fresh data. A demo project lets the UI be developed with no Hermes at all.

**Read-only in this phase.** No write endpoints, no MCP, no chat, no editor.

## Out of scope (do not start)

MCP endpoint, Hermes adapter, skills, chat, editing, Fountain writer, deleting `core/screenplay.py` or touching `core/fountain_validator.py`, rewriting the frontend, adding a JS build step. Do not refactor `tools/` beyond what Task 2 and Task 1 require; Phase 2 will wrap them.

## Assumptions to verify in Task 0

Check each against the code and record the answer in `docs/plan/NOTES.md`.

- [ ] A1. `core/config.py` resolves the projects root from Hermes-provided kwargs/config. Find out exactly how, and what the `root_path` contract is (what directory holds `projects/`?).
- [ ] A2. `get_dashboard_data(project_path)` returns a dict with `story_data` and `sections`; the screenplay stats are computed separately in `tools/story_dashboard.py` from the scenes' text.
- [ ] A3. Projects are discoverable as `<root>/projects/<slug>/.story/story.db`; `resolve_project` maps slug to path.
- [ ] A4. `_render_dashboard` reads little from its `project` argument (check which keys).
- [ ] A5. The test suite runs green today. Record the baseline (count passing/failing/skipped).
- [ ] A6. Tools import `core` through absolute imports made possible only by the `sys.path` insert.
- [ ] A7. No other module besides `__init__.py` and the plugin-only code imports Hermes.

## Tasks

Each task: **Intent**, **Must** (strict), **Guidance** (adapt freely), **Checklist**. Commit after each.

### Task 0: Recon and baseline

**Intent:** know the real code before changing it.

**Must**
- Create a branch off `dev`.
- Run the full test suite and record the baseline.
- Create `docs/plan/NOTES.md` with the A1-A7 findings and a running list of deviations and unrelated problems found.

**Guidance:** read `__init__.py`, `core/config.py`, `core/db.py`, `tools/story_dashboard.py`, `tools/story_resolve.py`, `src/dashboard/index.html`, `js/core.js`, and `tests/test_dashboard_tabs.py`. Read whatever the existing `plan/` and `archieved/` folders contain, but do **not** delete them (see Task 9).

**Checklist**
- [x] Branch created
- [x] Baseline test results recorded
- [x] A1-A7 verified and noted
- [x] `NOTES.md` created

---

### Task 1: Make it an installable Python package

**Intent:** replace the `sys.path` hack with a proper package so the app, tests, and (later) MCP server all import the engine the same way.

**Must**
- `pip install -e .` works and exposes an importable package (proposed name `story_architect`) containing `core` and `tools`.
- No `sys.path` manipulation anywhere in the codebase.
- Declared dependencies in `pyproject.toml`: existing ones plus `fastapi` and `uvicorn`. Set a sensible `requires-python` (the owner runs 3.14; 3.11+ is fine).
- Web assets are included as package data (verify with an actual non-editable build or `pip install .` in a temp venv, since editable installs hide missing package data).
- The whole test suite is green again after import updates.

**Guidance**
- Use the `src/` layout. Move `core/`, `tools/`, and the dashboard files (to `web/`, see Task 6) under `src/story_architect/`.
- Update imports mechanically (`from core.x` becomes `from story_architect.core.x` or relative imports; pick one style and apply it consistently).
- Do the move with `git mv` so history is preserved. Keep this task a pure move/rename; no behavior changes.
- The repo folder name contains hyphens; that no longer matters once the package has its own name.

**Checklist**
- [ ] Package layout created, history preserved
- [ ] Imports updated, no `sys.path` hacks left
- [ ] `pyproject.toml` has package config, dependencies, console-script entry (can point to a stub until Task 7)
- [ ] Clean-venv `pip install .` succeeds and `import story_architect.core` works
- [ ] Test suite green

---

### Task 2: Remove the Hermes plugin layer

**Intent:** the repo is no longer a Hermes plugin.

**Must**
- Remove the plugin entry point and everything Hermes-specific in it: `register()`, tool registration, the `post_tool_call` hook, skills registration, `plugin.yaml`.
- Remove the `story_dashboard` tool and its temp-file / `file://` code path (the dashboard is now served by the app; its reusable logic moves in Task 4).
- No remaining imports of Hermes modules. A test should enforce this (see Task 8).

**Guidance**
- The other 10 tool modules stay as they are, unregistered, so Phase 2 can wrap them. Do not rework their `handler(args, **kwargs)` signatures now. Make sure their tests still pass; if their root-path resolution depended on the plugin entry, keep it working through the existing helpers and note it in `NOTES.md` for Phase 2.
- If something in `tools/` only existed to support the dashboard tool or the hook, remove it. If you are unsure whether it is used by something else, leave it and note it.

**Checklist**
- [x] Plugin entry, hook, skills registration, `plugin.yaml` removed
- [x] `story_dashboard` tool removed; reusable logic identified for Task 4
- [x] No Hermes imports remain
- [x] Tests green (remove or adapt only tests of deleted code)

---

### Task 3: Application configuration

**Intent:** the app finds the projects root without Hermes.

**Must**
- One config module in the app layer resolves settings with precedence: **CLI flag, then environment variable, then user config file, then default**.
- Settings in scope: projects root, port (default **8731**), and open-browser behavior.
- The host is always `127.0.0.1` and is not configurable.
- The Hermes-dependent parts of root resolution (A1) are replaced or bypassed for the app. Pass the resolved root explicitly into core functions that need it.
- If the root does not exist or has no `projects/` directory, produce a clear, actionable error (and offer to create the directory in the launcher, Task 7).

**Guidance**
- Env var prefix like `STORY_ARCHITECT_`. Config file in the platform's standard config dir (a small TOML via stdlib `tomllib` is enough; reading only, no writing in this phase).
- Keep it a small dataclass plus one `load_config()` function; no config framework.
- Choose a default root that makes sense for first-time use (for example a folder in the user's home) and document it.

**Checklist**
- [x] Config module with documented precedence
- [x] Unit tests for precedence and error cases
- [x] No Hermes config dependency left in the app path

---

### Task 4: Read services (framework-free)

**Intent:** the data the dashboard needs is produced by plain functions that the HTTP layer (and later MCP) can call.

**Must**
- A function that lists projects under the root with minimal metadata (slug, name if available, maybe modified time or counts if cheap).
- A function that returns the dashboard payload for a project: `story_data`, `sections`, and `screenplay_stats` (the three things previously injected into the HTML). Use the existing `get_dashboard_data` and the stats logic from the removed tool; move that logic rather than rewriting it.
- These functions take explicit arguments (root, slug), raise clear exceptions for unknown/missing projects, import no web framework, and never write to the DB.

**Guidance**
- Put them in a module of the app layer or a small `services` module; keep it small. If the stats helper currently lives in a tool module, move it to where `core` or the service layer fits best.
- Open the database read-only where the existing helpers allow it; do not alter connection setup in `core/db.py` unless necessary.

**Checklist**
- [x] `list_projects` and `get_project_dashboard` (names flexible) implemented
- [x] Output shape matches what the frontend currently consumes (compare against the old injected values on a real project)
- [x] Tests with a fixture project: happy path, unknown slug, project without a DB

---

### Task 5: HTTP server

**Intent:** a small, well-structured FastAPI app serving the API and static UI.

**Must**
- An **app factory** (`create_app(config)` or similar) so tests can build isolated apps.
- Routes:
  - `GET /healthz`
  - `GET /api/projects`
  - `GET /api/projects/{slug}/dashboard`
  - static UI at `/` (see Task 6)
- Read-only: no POST/PUT/PATCH/DELETE routes in this phase.
- API responses are `Cache-Control: no-store`.
- `Host` header validation allowing only `127.0.0.1` (plus `localhost` and the configured port form) to defend against DNS rebinding.
- Consistent JSON error shape (for example `{"error": {"code": "...", "message": "..."}}`); unknown project is a 404; domain exceptions are translated in one place, not per route.
- Slug path parameters are validated so they cannot traverse outside the projects root.

**Guidance**
- Routes stay thin: parse input, call a service, return the result. Keep route modules separate from the factory if it helps readability.
- No docs UI exposure is required (`/docs`) unless you find it useful in development; if enabled, make it dev-only.
- Use standard logging; avoid noisy per-request logs at default level.

**Checklist**
- [x] App factory
- [x] The four routes working
- [x] Host validation, traversal protection, consistent errors
- [x] API tests (FastAPI `TestClient`): health, list, dashboard, 404, bad host, traversal attempt

---

### Task 6: Frontend served live

**Intent:** the existing dashboard UI runs as a normal web page, fed by the API.

**Must**
- The UI lives in `web/` inside the package and is served as static files. **No more concatenation/inlining step** (`assemble_dashboard`, placeholders, injected `window.__*` globals are removed).
- `index.html` loads CSS and JS files individually in the **same order the old `CSS_ORDER`/`JS_ORDER` defined**. That order is load-bearing; preserve it, and keep a test pinning it (adapt `tests/test_dashboard_tabs.py`).
- On load, the page shows a **project picker** (from `/api/projects`). Choosing a project shows the existing dashboard, loaded from `/api/projects/{slug}/dashboard` and booted with the existing entry point (`DASH.initStory(...)` with the data previously supplied by the injected globals, including sections and screenplay stats).
- The selected project is reflected in the URL hash (`#/p/<slug>`) so reload and bookmarks work; opening the root URL with no hash shows the picker. Provide a way back to the picker.
- Loading and error states are visible (project not found, server error, empty projects list with a hint on how to create/seed one).
- Cache headers for static files must not hamper development (no stale JS while iterating).
- The 13 `data-hermes-send` buttons: route them through **one function** `DASH.askAgent(text)` that, for now, copies the prompt to the clipboard and shows a short confirmation. (Phase 2 users chat in Hermes Desktop and can paste; Phase 3 replaces this function's implementation with the in-app chat.) Keep the `data-hermes-send` attribute name only if renaming would cause churn; a neutral name such as `data-ask-agent` is preferred if cheap.

**Guidance**
- Existing code may assume the data exists synchronously at load. Wrap boot in an async function that fetches first, then calls the existing init. Fix only what breaks.
- Don't restructure the 16 JS files or introduce modules/bundlers. Do not restyle.
- The picker can be simple, using existing CSS tokens/classes.

**Checklist**
- [x] Assets moved to `web/`, served statically, inlining pipeline deleted
- [x] Script/CSS order preserved and test-pinned
- [x] Picker + hash routing + loading/error/empty states
- [x] Dashboard renders from API for a real project: all tabs verified manually
- [x] `DASH.askAgent` implemented, all send-buttons routed through it
- [x] No JS console errors on load or on navigating all tabs

---

### Task 7: Launcher CLI

**Intent:** one command starts the app and opens it.

**Must**
- Console script `story-architect` (entry point in `pyproject.toml`).
- Options: `--root`, `--port`, `--no-open`, and a dev flag (auto-reload). Standard library `argparse` is fine; do not add a CLI framework.
- Prints the URL it serves.
- Opens the default browser to the app unless `--no-open`.
- If the port is already serving **this app** (check `/healthz`), do not start a second server: just open the browser to the existing one and say so. If the port is occupied by something else, fail with a clear message suggesting `--port`.
- If the root does not exist, say so clearly and offer to create it (interactive prompt is fine; also a non-interactive flag).
- Clean shutdown on Ctrl+C.

**Guidance**
- Run uvicorn programmatically from the launcher; keep the launcher module small and the logic (port check, open browser) in separate testable functions.
- Wait for the server to be ready before opening the browser.

**Checklist**
- [ ] `story-architect` command works in a fresh venv
- [ ] Reuse-existing-instance and port-conflict behavior
- [ ] Missing-root handling
- [ ] Tests for the testable helpers (port/health check, config wiring)

---

### Task 8: Demo project and quality gates

**Intent:** the UI can be developed and reviewed with no Hermes and no real data; the codebase has a tidy baseline.

**Must**
- A way to create a **demo project** with representative content (a few scenes with Fountain text, characters, locations, sequences, relationships) using the existing write functions in `core/writes.py`. Delivery form is flexible: a subcommand (`story-architect seed-demo --root ...`) or a script under `scripts/`. It must be idempotent or refuse safely if the project exists.
- A test that fails if any module under the package imports Hermes (a simple import-graph/grep check is fine).
- `ruff` configured in `pyproject.toml` (lint + format). Apply formatting in **its own commit** after all functional work is done.
- Test suite green; report final counts against the baseline.

**Guidance**
- Reuse any existing test fixtures that already build realistic projects (browser-verification-test); the demo can share code with them.
- Don't let the demo become a maintenance burden: keep it small but varied enough to exercise every dashboard tab.

**Checklist**
- [ ] Demo project command/script
- [ ] "No Hermes imports" test
- [ ] Ruff configured, lint clean, formatting commit separate
- [ ] Final test counts recorded in `NOTES.md`

---

### Task 9: Docs and cleanup

**Intent:** a newcomer (or the owner in 3 months) can run and understand the project.

**Must**
- Rewrite `README.md` to describe the app as it now is: what it is, install, run, configuration (root, port, env vars, config file), demo data, running tests, project layout in a few lines. Remove stale content.
- Place this plan (`00-overview.md`, this file) under `docs/plan/` and tick the checklists.
- Do **not** delete `plan/`, `archieved/`, `docs/`, or `vault-conventions.md` on your own. List each stale-looking item in `NOTES.md` with a one-line recommendation (keep/archive/delete) for the owner to decide.

**Checklist**
- [ ] README rewritten
- [ ] Plan files in `docs/plan/`, checklists ticked
- [ ] Stale-items list with recommendations in `NOTES.md`

---

## Definition of done (acceptance test)

Run these yourself and record results in `NOTES.md`:

1. In a fresh virtualenv with no Hermes on the PATH: `pip install .`, then `story-architect seed-demo --root /tmp/sa-demo` (or equivalent), then `story-architect --root /tmp/sa-demo`.
2. The browser opens to the project picker; the demo project is listed; opening it renders every dashboard tab with no console errors.
3. Reloading the page and loading the `#/p/<slug>` URL directly both work.
4. Changing data in the DB (for example through a test helper or an existing write function) and reloading shows the new data.
5. Running the command a second time reuses the running instance.
6. On the owner's real project root, the dashboard shows the same counts and content as the old static dashboard did (spot-check scenes, characters, stats).
7. `grep -ri hermes` over the package source finds nothing functional (comments/docs mentioning the planned integration are fine).
8. Full test suite green; `ruff` clean.

## Report back when done

Send the owner a short summary: what was built, test counts before/after, any deviations from this plan (with reasons), the stale-items list, and anything Phase 2 should know (especially: how tool root-path resolution works now, and what the tool handlers still expect from their `kwargs`).
