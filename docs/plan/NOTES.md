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

## Stale items (recommendations)

- plan/ — keep (historical)
- archieved/ — archive
- vault-conventions.md — keep
- docs/ — keep
