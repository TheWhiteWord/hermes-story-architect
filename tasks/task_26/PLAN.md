# DB-First Runtime Architecture Cleanup Implementation Plan

> **For Hermes:** Execute this plan task-by-task. Do not start a later task until the preceding task's verification passes.

**Goal:** Remove remaining operational dependencies on Markdown files so runtime tools and the dashboard use the project DB as their single source of truth, while preserving `story_import` and `story_export` as explicit Markdown boundaries.

**Architecture:** `story.db` owns runtime project state. `project.md`, entity Markdown files, `.story/memory.md`, and any legacy dashboard index files are projections or explicit import inputs only. No runtime compatibility fallback from Markdown to the DB may be added.

**Tech Stack:** Python 3.10+, SQLite, `python-frontmatter`, pytest, existing Hermes plugin tool handlers, classic dashboard JavaScript assembled into a `file://` HTML document.

**Source brief:** `tasks/task_26/DEFERRED_db_first_architecture_audit.md`

---

## Authority and scope

### Authoritative store

- Entity metadata: `entities` table.
- Entity relationships: `relations` table.
- Entity prose sections: `sections` table.
- Project story memory: project entity `extra` JSON, specifically `extra.memory`.
- Dashboard data: `core.db.get_dashboard_data()`.

### Allowed Markdown surfaces

- `story_import`: explicit import/rebuild operation. It may read `project.md`, entity folders, and `.story/memory.md`.
- `story_export`: explicit projection operation. It may write the Markdown files.
- Project creation writes only the DB and its `.story` directory. Markdown files and entity folders are created only by `story_export`, never by project creation.

### Forbidden runtime behavior

- No runtime tool may load `project.md` or entity `.md` files to obtain authoritative values.
- No runtime tool may fall back to Markdown when the DB is absent, stale, or incomplete.
- Do not add a new compatibility layer or a second operational authority.
- Do not redesign or add `structure.md`; it is explicitly future work.

## Current verified findings

1. `tools/story_dashboard.py:338-343` loads `project.md` directly even though `core/db.py:1221-1238` already builds DB-backed `title_page` data and returns it from `get_dashboard_data()`.
2. `tools/story_resolve.py:37-43` reads `project.md` metadata for fuzzy project-name resolution. Project names are already stored in `entities.name`.
3. `tools/story_create.py:231-256` checks and writes `project.md` before completing DB project initialization. This is a legacy bootstrap authority.
4. `src/dashboard/js/core.js:17-32` has a legacy `.DASH.story/index.yaml` fetch fallback. The generated dashboard normally receives DB-derived `window.__STORY_DATA__` injection.
5. `tools/story_load.py`, `tools/story_retrieve.py`, `tools/story_search.py`, `tools/story_edit.py`, and `tools/story_memory.py` already use DB operational paths.
6. `core/entity.py:15-30` and `core/entity.py:124-129` contain dormant Markdown helper functions. Production callers were not found in the current source search; do not expand their role during this cleanup.

---

# Execution tasks

## Task 1: Make dashboard title-page data DB-backed

**Status:** COMPLETE — verified and implemented. Focused check: `36 passed` in `tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py`. Removed the dashboard `project.md` read and added stale-Markdown regression coverage.
**Depends on:** None
**Blocks:** Task 2, Task 4

### Objective

Remove the dashboard's direct `project.md` read and use the already-existing DB-backed `title_page` payload from `get_dashboard_data()`.

### Files to touch

| File | Action |
|------|--------|
| `tools/story_dashboard.py:327-360` | Remove direct `frontmatter` import/read; use `data.get("title_page", {})`. |
| `tests/test_story_dashboard_integration.py` or focused dashboard test file | Add a regression test proving stale/missing `project.md` does not change injected title-page data. |
| `core/db.py` | No implementation change expected; verify `title_page` fields are complete and DB-backed first. |

### Step-by-step implementation

1. Confirm `get_dashboard_data()` returns:

   ```python
   {
       "name": ...,
       "logline": ...,
       "screenplay_title": ...,
       "credit": ...,
       "author": ...,
       "contact": ...,
       "draft_date": ...,
       "draft": ...,
   }
   ```

2. Add a test fixture with a valid DB containing a non-empty screenplay title and a deliberately stale or absent `project.md`.

3. Render the dashboard and assert the generated HTML contains the DB title value, not the Markdown value.

4. Replace the `project.md` load in `_render_dashboard()` with:

   ```python
   project_frontmatter = data.get("title_page", {})
   ```

5. Remove the now-unused `frontmatter` import from `story_dashboard.py`.

6. Run the focused dashboard tests.

### Legacy code to remove

| Code | Location | Reason |
|------|----------|--------|
| `import frontmatter as fm` | `tools/story_dashboard.py:330` | No longer needed after the direct file read is removed. |
| `fm.load(project_path / "project.md")` | `tools/story_dashboard.py:340` | Runtime Markdown source dependency. |

### Test impact

- Add one regression test for DB title-page authority.
- Do not rewrite or remove the existing test suite.
- The test must cover both absent and stale `project.md` if the fixture setup makes that cheap; otherwise use one stale-file case plus one missing-file case.

### Verification

```bash
pytest tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py -q
```

Expected: focused dashboard tests pass, including the new stale/missing-Markdown regression.

### Checklist

- [x] Confirm DB title-page payload is complete.
- [x] Add stale/missing-Markdown regression coverage.
- [x] Replace direct file read with DB payload.
- [x] Remove unused import.
- [x] Focused dashboard tests pass.

### Notes for subsequent tasks

- Task 2 can now remove the dashboard's remaining direct project metadata dependency.
- Task 4 can treat the dashboard as DB-injected-only.

---

## Task 2: Make project resolution DB-backed

**Status:** COMPLETE — verified and implemented. Focused check: `39 passed` in `tests/test_phase2_db_reads.py`. Project fuzzy resolution now reads project names from `.story/story.db`; stale or missing `project.md` does not affect resolution.
**Depends on:** Task 1 — dashboard title-page data
**Blocks:** Task 3, Task 4

### Objective

Make `resolve_project()` resolve project names from DB metadata, not `project.md`, while preserving direct-path and exact-slug resolution.

### Files to touch

| File | Action |
|------|--------|
| `tools/story_resolve.py:30-55` | Replace Markdown candidate loading with DB-backed project-name candidates. |
| `tools/story_resolve.py` | Add a small DB read helper only if the existing `core.db` API does not already provide the required query. |
| `tests/test_phase2_db_reads.py` or focused resolution test file | Add stale/missing-Markdown project-name resolution coverage. |

### Step-by-step implementation

1. Preserve the existing resolution order:
   - direct existing directory;
   - exact project-directory slug;
   - fuzzy slug/name matching.

2. For fuzzy matching, enumerate project directories and read the project name from the project DB:

   ```sql
   SELECT name FROM entities WHERE type = 'project'
   ```

3. Add the directory slug as a candidate and the DB project name as a separate candidate.

4. Keep the same `FUZZY_THRESHOLD` and error contract.

5. Remove `frontmatter` loading from `story_resolve.py`.

6. Add a test where `project.md` is stale or missing but the DB name still resolves successfully.

7. Add a negative test only if needed to ensure a Markdown-only name does not become authoritative.

### Legacy code to remove

| Code | Location | Reason |
|------|----------|--------|
| `project_md = project_dir / "project.md"` | `tools/story_resolve.py:38` | Runtime Markdown source dependency. |
| `frontmatter.load(project_md)` | `tools/story_resolve.py:41` | Runtime Markdown source dependency. |

### Data-flow impact

`resolve_project()` is called by create, load, retrieve, search, edit, memory, import, export, backup, and dashboard handlers. This task changes shared resolution behavior, so the focused regression test must cover a normal DB-backed project lookup, not only `story_load`.

### Verification

```bash
pytest tests/test_phase2_db_reads.py -q
```

Expected: DB-backed load/search/dashboard tests pass, and the new resolution regression passes.

### Checklist

- [x] Preserve direct-path and exact-slug behavior.
- [x] Add DB-backed project-name candidates.
- [x] Remove Markdown metadata reads.
- [x] Add stale/missing-Markdown resolution regression.
- [x] Focused Phase 2 tests pass.

### Notes for subsequent tasks

- Task 3 can stop using `project.md` as the project existence authority.
- Task 4 can remove the dashboard file fallback without changing project lookup.

---

## Task 3: Make project creation DB-authoritative

**Status:** COMPLETE — verified and implemented. Focused check: `7 passed` in `tests/test_core.py::TestProjectCreation`. Project creation is now DB-only, uses an explicit transaction, initializes canonical empty memory, and creates no Markdown/entity-folder scaffold.
**Depends on:** Task 2 — DB-backed project resolution
**Blocks:** Task 4

### Objective

Create the project DB record and initialize its canonical empty memory shape. Project creation must not create `project.md` or entity folders; those are export outputs only. A stale or missing `project.md` must not determine whether a DB project exists.

### Files to touch

| File | Action |
|------|--------|
| `tools/story_create.py:225-295` | Make project creation DB-only and change duplicate detection to inspect the DB. |
| `tools/story_create.py` | Remove Markdown and entity-folder creation from project creation. |
| `tools/story_create.py` | Preserve `empty_memory()` in the project entity's `extra.memory`. |
| `tests/test_core.py` or focused create test file | Add DB-only project creation, memory initialization, and duplicate-detection coverage. |

### Step-by-step implementation

1. Keep validation of required project fields before writing any state.

2. Open the project DB and create the schema if needed.

3. Check for an existing project entity in the DB:

   ```sql
   SELECT id FROM entities WHERE type = 'project'
   ```

4. If a project entity exists, return the existing project-already-exists error.

5. Insert the project entity and standard sections in one transaction, with `extra.memory` initialized from `empty_memory()`.

6. Verify after commit that `get_project_memory(project_path)` returns the canonical empty memory shape.

7. Commit successfully. Project creation does not create `project.md` or entity folders.

8. Add tests for:
   - DB project and `.story/story.db` created without `project.md` or entity folders;
   - project memory initialized as the canonical four empty categories;
   - duplicate DB project rejected even if `project.md` is missing;
   - stale `project.md` does not make a new DB project appear duplicated.

### Legacy code to remove

| Code | Location | Reason |
|------|----------|--------|
| `(project_path / "project.md").exists()` as duplicate check | `tools/story_create.py:231-232` | Markdown is not the project authority. |
| `frontmatter` import and `project.md` write in project creation | `tools/story_create.py:227,250-256` | Markdown is an export output, not a creation artifact. |
| Entity-folder creation in project creation | `tools/story_create.py:258-260` | Folders are export scaffolding and should not be created by DB project creation. |

### Data-flow impact

Project creation is the producer of the project entity consumed by every runtime tool. Preserve the existing project ID (`slug`) and the existing DB schema. Do not add a new project table or a migration.

### Verification

```bash
pytest tests/test_core.py -q
```

Expected: existing project/entity tests pass, plus the new DB-first project creation tests.

### Checklist

- [x] Validate project input first.
- [x] Create and commit the project DB record with canonical empty memory.
- [x] Use DB state for duplicate detection.
- [x] Do not create `project.md` or entity folders.
- [x] Add DB-only creation, stale-Markdown, and memory-initialization tests.
- [x] Focused core tests pass.

### Notes for subsequent tasks

- Task 4 should verify no runtime dashboard path depends on project Markdown.
- Keep the existing export format unchanged; Markdown files and entity folders are generated only by `story_export`.

---

## Task 4: Remove the legacy dashboard file fallback

**Status:** COMPLETE — verified and implemented. Focused check: `37 passed` in `tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py`. Removed the `.DASH.story/index.yaml` fetch/YAML fallback; dashboard boot now requires injected DB data and shows the error state otherwise.
**Depends on:** Tasks 1–3 — dashboard DB title data, DB resolution, DB-first project creation
**Blocks:** Final verification

### Objective

Make the generated dashboard consume only DB-derived injected data and remove the legacy `.DASH.story/index.yaml` fetch path if no live caller requires it.

### Files to touch

| File | Action |
|------|--------|
| `src/dashboard/js/core.js:9-35` | Remove the file-fetch fallback or reduce boot to injected data only. |
| `tools/story_dashboard.py` | Verify the generated HTML always injects `window.__STORY_DATA__` before boot. |
| Dashboard tests | Add a regression that missing injected data produces the normal error state without fetching a file. |

### Step-by-step implementation

1. Confirm `story_dashboard.handler()` always calls `get_dashboard_data()` and injects `window.__STORY_DATA__` for a valid project.

2. Confirm no active production path still generates `.DASH.story/index.yaml` or relies on the URL project query parameter for the normal tool flow.

3. Remove the fallback fetch and YAML initialization path from `src/dashboard/js/core.js`.

4. Keep the existing injected-data initialization and error display.

5. Add a focused test for missing `window.__STORY_DATA__`: boot should show the error state without attempting a Markdown/YAML file read.

### Legacy code to remove

| Code | Location | Reason |
|------|----------|--------|
| `fetch('file://' + indexPath)` | `src/dashboard/js/core.js:28` | File-based runtime fallback. |
| `jsyaml.load(text)` | `src/dashboard/js/core.js:31` | Legacy file projection path. |
| URL-derived `.DASH.story/index.yaml` lookup | `src/dashboard/js/core.js:17-26` | Obsolete operational dashboard path after DB injection is enforced. |

### Constraints

- The dashboard is loaded from a generated `file://` HTML document. Do not introduce ES modules, a bundler, or a server.
- Do not change dashboard rendering or visual behavior.
- Do not remove dashboard data fields that are already DB-derived.

### Verification

```bash
pytest tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py -q
```

Expected: dashboard tests pass and the generated dashboard remains DB-injected.

### Checklist

- [x] Confirm all normal dashboard launches inject DB data.
- [x] Confirm no active caller needs the YAML fallback.
- [x] Remove file fetch/YAML initialization.
- [x] Add missing-injection regression.
- [x] Focused dashboard tests pass.

---

## Task 5: Final audit and focused regression verification

**Status:** COMPLETE — verified and implemented. Focused checks: dashboard `37 passed`, Phase 2 `39 passed`, core `67 passed`, memory import/export `5 passed`; full suite `308 passed`. Final audit found and fixed the DB-only project/memory import regression; the import boundary now preserves an existing DB when `project.md` is absent and imports valid memory only.
**Depends on:** Tasks 1–4
**Blocks:** None — final gate

### Objective

Prove that runtime tools no longer use Markdown as an operational source, while import/export remain explicit boundaries.

### Files to touch

| File | Action |
|------|--------|
| `tools/story_dashboard.py` | No further implementation expected; verify all direct project.md reads are gone. |
| `tools/story_resolve.py` | No further implementation expected; verify all project.md reads are gone. |
| `tools/story_create.py` | No further implementation expected; verify project.md is projection-only. |
| `tools/story_import.py` | Preserve unchanged unless audit finds an accidental runtime caller. |
| `tools/story_export.py` | Preserve unchanged as the projection boundary. |
| `core/entity.py` | Do not expand legacy helper scope; record any remaining dormant Markdown helpers as deferred cleanup if still unused. |
| Focused tests | Add only missing stale/absent-Markdown regressions. |

### Audit commands

Search all source and tests for direct runtime file reads:

```bash
rg -n "frontmatter\.load|frontmatter\.dump|project\.md|\.DASH\.story|index\.yaml|\.story.*memory\.md" \
  tools core src
```

Classify every hit as one of:

- intentional `story_import` read;
- intentional `story_export` write;
- project-creation DB-only initialization;
- test fixture/test assertion;
- remaining operational defect.

### Runtime authority checks

Verify each tool's primary data path:

| Tool | Required authority |
|------|--------------------|
| `story_load` | `core.db.get_project_summary()` |
| `story_retrieve` | `core.db.get_entity_sections()` |
| `story_search` | `core.db.search_sections()` |
| `story_edit` | DB transaction |
| `story_memory` | `get_project_memory()` / `set_project_memory()` |
| `story_dashboard` | `core.db.get_dashboard_data()` plus injected data |
| `story_import` | Markdown → DB, explicit boundary |
| `story_export` | DB → Markdown, explicit boundary |

### Final verification

Run narrowly scoped tests first:

```bash
pytest tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py -q
pytest tests/test_phase2_db_reads.py -q
pytest tests/test_core.py -q
pytest tests/test_memory_export.py tests/test_memory_e2e.py -q
```

Then run the broader suite only after the focused checks pass:

```bash
pytest -q
```

If the broader suite has unrelated pre-existing failures, record the exact failing tests and do not modify tests or unrelated code as part of this task.

### Final acceptance criteria

- [x] No runtime dashboard read of `project.md`.
- [x] No runtime project-resolution read of `project.md`.
- [x] Project duplicate detection uses DB state.
- [x] Project creation is DB-only and initializes canonical empty memory.
- [x] Project creation does not create `project.md` or entity folders.
- [x] Dashboard normal boot uses injected DB data.
- [x] `story_import` remains an explicit Markdown-to-DB operation.
- [x] `story_export` remains an explicit DB-to-Markdown operation.
- [x] Stale or missing Markdown projections do not change runtime results.
- [x] Focused tests pass.
- [x] Broader suite result recorded.

### Legacy code to remove or defer

| Code | Location | Action |
|------|----------|--------|
| Dashboard `project.md` title-page read | `tools/story_dashboard.py` | Remove in Task 1. |
| Resolver `project.md` name read | `tools/story_resolve.py` | Remove in Task 2. |
| Project creation MD-first order | `tools/story_create.py` | Remove Markdown/folder creation and make DB-only in Task 3. |
| Dashboard `.DASH.story/index.yaml` fallback | `src/dashboard/js/core.js` | Remove in Task 4 if unused. |
| `core.entity.extract_entity()` and `update_sections()` | `core/entity.py` | Keep untouched for now; record as separate deferred cleanup if no callers exist. |

---

## Out of scope

- `structure.md` design or implementation.
- New Markdown compatibility fallbacks.
- Changes to `story_import` or `story_export` formats.
- Refactoring the dashboard data model or visual design.
- Removing dormant `core.entity` helpers without a separate decision.
- Committing, pushing, installing, or syncing the plugin.

## Notes

- The final audit found one integration issue caused by making project creation DB-only: `story_import` previously cleared the DB and then had no project row to receive `.story/memory.md` when `project.md` was absent. `story_import` now preserves an existing DB in that case and imports only a valid memory file.
- Remaining `frontmatter` reads in `tools/story_import.py` and writes in `tools/story_export.py` are intentional import/export boundaries.
- `core.entity.extract_entity()` and `update_sections()` remain deferred dormant helpers; no production callers were found.
- `story_export` remains the only creator of Markdown files and entity folders.

## Final brief

All five tasks are complete. Runtime project resolution, project creation, dashboard title-page data, and dashboard boot now use the DB as authority. Markdown remains limited to explicit import/export projections. Verification passed: dashboard 37, Phase 2 39, core 67, memory import/export 5, full suite 308.

## Execution rule

Implement one task at a time in the order above. If code inspection finds a medium/high-impact mismatch between this plan and the current code, stop at that task, record the mismatch, and ask for a decision before proceeding.
