# Task 13: Unify Project Index — Single Source of Truth

**Created:** 2026-09-14
**Status:** Plan — ready for task decomposition
**Input:** `ISSUE.md` + senior developer consultation

---

## 1. Principle

**Storage boundaries must follow production boundaries, not conceptual ones.**

The "navigation vs. structural" split is a conceptual distinction that exists in the developer's model but has no production expression:
- Same writer (one `refresh_index()` call)
- Same volatility (both files regenerated on the same trigger)
- Same consumer process (all tools run in the same Python process)
- No access control requirements
- Same lifecycle (both files belong to the same project)

When two artifacts are always written together, always read together, and have the same lifecycle, they are not two artifacts — they are one.

**Filter at the consumer, not at the source.** The index is the source of truth — complete and unified. Each consumer (LLM tool, dashboard, stats panel) takes what it needs via projection. Storage splitting is a subset of what filtering can do — so filtering is the more general solution and the right default.

**Artificial splits produce silent bugs.** Classification cost isn't just at write time — it's at read time too. `story_dashboard.py` reads `dramatic_role` from `index.yaml`, but that field was stripped because it's "structural." The dashboard's role-count panel is silently broken: every scene counts as `"unset"`.

---

## 2. Current State Map

### 2.1 Files that generate the split

| File | Role | What it does today |
|------|------|--------------------|
| `core/index.py` | Generator | `generate_index()` produces navigation-only dict; stashes `_full_scenes`/`_full_project` as internal keys. `generate_structure_index()` reads those stashes to build the sidecar. `refresh_index()` calls both. `update_structure_index_scene()` does O(1) writes to `structure-index.yaml`. |
| `tools/story_index.py` | Tool entry | Calls `generate_index()` then `generate_structure_index()`, writes both files. Returns both in response. |
| `tools/story_load.py` | Consumer | `structure_only=true` reads `structure-index.yaml` separately. Default reads `index.yaml`. |
| `tools/story_edit.py` | Consumer | After editing a scene, calls `update_structure_index_scene()` to O(1)-update `structure-index.yaml`. |
| `tools/story_dashboard.py` | Consumer | Reads `index.yaml` only. Calls `compute_structural_stats(index)` which reads `dramatic_role` from `index.yaml` — **but that field was stripped**, so stats are silently wrong. |

### 2.2 Classification constants

| Constant | Location | Purpose |
|----------|----------|---------|
| `PROJECT_STRUCTURAL_FIELDS` | `core/constants.py` | Fields stripped from `index["project"]` and sent to `structure-index.yaml` |
| `NAVIGATION_SCENE_FIELDS` | `core/index.py` | Fields kept in `index["scenes"]`; everything else stripped |

### 2.3 Test surface

| Test | Location | What it tests |
|------|----------|---------------|
| `TestStructureIndex` (5 tests) | `tests/test_core.py` | `generate_structure_index()` output structure |
| `test_update_structure_index_scene` | `tests/test_core.py` | `update_structure_index_scene()` O(1) update |
| `_make_project_with_structure` helper | `tests/test_core.py` | Creates project with `structure-index.yaml` for tests |
| `test_story_dashboard_stats.py` | `tests/test_story_dashboard_stats.py` | Fountain stats (not directly affected) |

### 2.4 Fixture files

| File | Status |
|------|--------|
| `tests/fixtures/save-the-children/.story/index.yaml` | Navigation-only (missing structural fields). Must be regenerated. |
| `tests/fixtures/save-the-children/.story/structure-index.yaml` | Exists. Must be removed (no longer generated). |

### 2.5 Skill / doc surface

| File | What it references |
|------|-------------------|
| `skills/story-loader/SKILL.md` | `structure_only` param, lazy structure loading, `structure-index-format.md` |
| `skills/story-loader/references/index-format.md` | "Structure Index" section pointing to sidecar |
| `skills/story-loader/references/structure-index-format.md` | Full sidecar schema doc |
| `skills/story-editor/SKILL.md` | Same as story-loader |
| `skills/story-editor/references/index-format.md` | Same as story-loader |
| `skills/story-editor/references/structure-index-format.md` | Same as story-loader |
| `vault-conventions.md` | `.story/index.yaml` description |

---

## 3. End State

### 3.1 After this refactor

- **One file:** `.story/index.yaml` contains everything — navigation + dramatic metadata + structural fields.
- **One generator:** `generate_index()` produces the complete dict. No `_full_scenes`/`_full_project` stashes. No stripping.
- **One writer:** `write_index()` writes one file. `write_structure_index()` is deleted.
- **One reader:** `story_load` reads `index.yaml`. `structure_only` is replaced by field projection — the tool returns a filtered view based on task context.
- **One consumer path:** Dashboard reads one file. `compute_structural_stats()` sees `dramatic_role` because it's present.
- **No classification constants:** `PROJECT_STRUCTURAL_FIELDS` and `NAVIGATION_SCENE_FIELDS` are deleted.
- **No sidecar functions:** `generate_structure_index()`, `write_structure_index()`, `update_structure_index_scene()` are deleted.
- **No sidecar fixture:** `structure-index.yaml` is removed from fixtures.
- **No sidecar docs:** `structure-index-format.md` is removed from skills. Its content is merged into `index-format.md`.

### 3.2 What stays the same

- The index is still regenerated on every `story_index` call (no O(1) path — YAGNI, rebuild is fast for story-scale projects).
- `story_load` still supports lazy loading — but via projection, not file selection.
- The dashboard still injects `window.__STORY_DATA__` as one global.
- `story_edit` still writes scene frontmatter and triggers index refresh (just calls `refresh_index()` instead of `update_structure_index_scene()`).

---

## 4. Decomposition Guide for Task Creation

This section defines the work units. Each should become a separate task with full spec.

### Phase A: Core Generator (prerequisite for everything else)

**A1. Unify `generate_index()`**
- Remove `_full_scenes` / `_full_project` stashing
- Remove `_strip_scene_for_navigation()` and `NAVIGATION_SCENE_FIELDS`
- Remove `PROJECT_STRUCTURAL_FIELDS` stripping from project
- Result: `generate_index()` produces the complete dict with all fields

**A2. Delete sidecar functions**
- Delete `generate_structure_index()`
- Delete `write_structure_index()`
- Delete `update_structure_index_scene()`

**A3. Simplify `refresh_index()`**
- Remove `generate_structure_index()` call
- Remove `write_structure_index()` call
- Remove `index.pop("_full_scenes")` / `index.pop("_full_project")`
- Single `write_index(index, index_path)` call

### Phase B: Tool Surface

**B1. Simplify `story_index.py` tool**
- Remove `generate_structure_index` / `write_structure_index` imports
- Remove structure index generation and writing
- Remove `structure_index` from response dict

**B2. Replace `story_load.py` `structure_only` with projection**
- Remove `structure_only` param from schema
- Add projection/filtering logic based on task context (or remove the param entirely if the caller can filter)
- Return the full index by default (the LLM gets what it needs, caller decides)

**B3. Simplify `story_edit.py`**
- Remove `update_structure_index_scene` import and call
- Either call `refresh_index()` after edit (full rebuild) or do nothing (LLM will call `story_index` when needed)

**B4. Fix `story_dashboard.py`**
- `compute_structural_stats()` will now find `dramatic_role` in `index.yaml` — verify it works correctly
- Remove any remaining references to `structure-index.yaml`

### Phase C: Constants & Schemas

**C1. Clean up `core/constants.py`**
- Delete `PROJECT_STRUCTURAL_FIELDS` constant

**C2. Update `core/constants.py` field schemas**
- Verify `ENTITY_SCHEMAS["project"]` includes structural fields (spine, controlling_idea, value, etc.) — they should already be present since they're frontmatter fields

### Phase D: Test Surface

**D1. Remove `TestStructureIndex` tests**
- 5 tests that test `generate_structure_index()` output — delete or rewrite to test that `generate_index()` includes structural fields

**D2. Remove `test_update_structure_index_scene`**
- Tests `update_structure_index_scene()` — delete (function no longer exists)

**D3. Simplify `_make_project_with_structure` helper**
- Remove `with_structure_index` param and `refresh_index()` call

**D4. Update fixture files**
- Regenerate `tests/fixtures/save-the-children/.story/index.yaml` with all fields
- Delete `tests/fixtures/save-the-children/.story/structure-index.yaml`

**D5. Add regression test for dashboard structural stats**
- Verify `compute_structural_stats()` returns correct `sceneRoles` counts (not all `"unset"`)

### Phase E: Skills & Documentation

**E1. Update `skills/story-loader/SKILL.md`**
- Remove `structure_only` param from tool description
- Remove "Load structure (when needed)" section
- Update references: `structure-index-format.md` → merged into `index-format.md`

**E2. Update `skills/story-editor/SKILL.md`**
- Same as E1

**E3. Merge `skills/story-loader/references/structure-index-format.md` into `index-format.md`**
- Add structural fields to Project, Scene, Sequence, Act tables
- Remove the "Structure Index" section pointing to sidecar
- Delete `structure-index-format.md`

**E4. Merge `skills/story-editor/references/structure-index-format.md` into `index-format.md`**
- Same as E3

**E5. Update `vault-conventions.md`**
- Update `.story/index.yaml` description to reflect unified content

### Phase F: Old Task Docs (optional, historical record)

**F1. Add deprecation note to `tasks/task_12/phase 2/plan.md`**
- Note that the two-file approach was reverted in favor of unified index
- Preserve history for context

**F2. Add deprecation note to `tasks/task_12/phase 3/plan.md`**
- Same as F1

---

## 5. Task Creation Guidelines

When creating the actual implementation tasks from this plan:

1. **Each task should be independently verifiable.** Prefer tasks that each leave the codebase in a passing state (all existing tests still pass after each task).

2. **Order matters.** Phase A must complete before B. Phase B before D (tests). Phase D before E (docs describe working code).

3. **Don't mix deletion and addition in the same task.** One task deletes the sidecar function; another updates the consumer. This makes rollbacks atomic.

4. **Test changes should accompany or immediately follow the code changes they validate.** Don't defer all test work to the end.

5. **The dashboard bug fix (B4+D5) is the proof that the refactor was necessary.** Make sure this is explicitly called out — it's not just cleanup, it's a correctness fix.

---

## 6. Risks & Open Questions

| # | Question | Impact | Resolution |
|---|----------|--------|------------|
| 1 | Does removing `structure_only` from `story_load` break any existing LLM skill that relies on it? | Skills may send `structure_only: true` expecting a lean response | Check all skill docs and tool callers. If skills use it, the projection logic must preserve the same lean response shape. |
| 2 | Is the O(1) `update_structure_index_scene()` actually needed for performance? | Editing a scene currently does O(1) instead of O(N) rebuild | Story projects have ~50 scenes. O(N) rebuild is sub-millisecond. YAGNI — remove O(1) path unless rebuild becomes measurably slow. |
| 3 | Does the `save-the-children` fixture's `index.yaml` need manual regeneration or can `refresh_index()` regenerate it? | Tests depend on fixture state | Must regenerate via `refresh_index()` after code changes, then commit the new fixture. |
| 4 | Does `story_index` tool's response shape change break any caller? | `structure_index` key disappears from response | Check if any skill or consumer reads `structure_index` from the response. If so, update them or keep the key (populated from the unified index). |
