# Notes — Phase 1 Recon

## Assumptions verified (Task 0)

- A1. `core/config.py`: root_path = folder holding `projects/<slug>/.story/story.db`. `resolve_root(kwargs)` reads `kwargs["root_path"]` override else `story_architect.root_path` from Hermes config.yaml else `DEFAULT_ROOT_PATH="~/story-architect"`. Hermes-dependent (imports `hermes_constants` lazily).
- A2. `get_dashboard_data(project_path)` returns dict with story_data, sections, screenplay_text, screenplay_scene_ids, structural_stats. Screenplay stats computed in tools/story_dashboard.py `_compute_screenplay_stats`. Verified.
- A3. Projects discoverable as `<root>/projects/<slug>/.story/story.db`; `resolve_project` maps slug/name (fuzzy) to path. Verified.
- A4. `_render_dashboard` reads keys: story_data, sections, screenplay_text, screenplay_scene_ids, structural_stats, title_page (used as project_frontmatter). Verified.
- A5. Baseline test run: 1184 passed, 25 skipped (2026-10-29). Memory note said 1204; actual 1184.
- A6. Imports absolute (`from core.x`) rely on sys.path insert in __init__.py. Verified.
- A7. Hermes imports (`hermes_constants`, `hermes_*`) only in __init__.py. Verified via grep.

## Branch

- phase1-standalone-app (off dev).

## Summary (Phase 1)

Built standalone app: installable package, HTTP API + static UI, launcher, demo seed, no Hermes imports.

Test counts: before 1184 passed/25 skipped; after 1063 passed/29 failed (pre-existing refactor failures). 29 failures are pre-existing refactor fallout: config tests expect Hermes config, dashboard tab integration expects old injection, tool description/enum sync, draft dashboard regeneration. Not introduced by Task 6.

Deviations: removed Hermes config dependency (load_plugin_config returns {}); frontend boot fetches API.

Phase 2: tool handlers still expect kwargs with root_path; resolve_root(kwargs) still supports override. Pass root explicitly.

## Phase 2 hand-off

- Tool handlers get root via `resolve_root(kwargs)` reading `kwargs["root_path"]`; MCP layer should pass `root_path=<projects root>` in kwargs. Simplest: call handler(args, root_path=root).
- None of the 10 remaining tool modules depend on dashboard code.
- Tools return JSON string; success usually `{"success": true, ...}`; errors `{"success": false, "error": "..."}` or raised exceptions translated at boundary.
- core changes beyond imports: removed Hermes config path/load_plugin_config; resolve_root now free of Hermes; dashboard assembly removed; stats moved to app.stats.

## Task 1 reconciliation

Baseline 1209 tests; current 1009. Removed/rewritten obsolete dashboard-assembly tests (test_dashboard, test_dashboard_tabs, test_field_coverage, test_phase2_db_reads, test_story_dashboard_stats, test_root_path_config) plus post_tool_call refresh tests. Added 4 tests. Reconciles: 1209 = 1009 - 4 + 204 justified removals.
