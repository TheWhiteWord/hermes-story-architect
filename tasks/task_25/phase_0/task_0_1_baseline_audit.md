# Phase 0 — Baseline audit

**Status:** Audit complete — blocked only on the dashboard payload naming decision.

**Plan source:** `tasks/task_25/memory_implementation_plan.md`, Phase 0.

**Objective:** Verify the current code and the memory spec against each other before changing production code.

## Confirmed findings

### Storage and current runtime

- `tools/story_create.py:256-266` creates `.story/memory.md` with placeholder Markdown sections. This is the current file-first path and must be removed from project creation.
- `core/db.py:100-124` `get_memory_outline()` is the only current memory reader. It parses `.story/memory.md` headings and previews.
- `core/db.py:466-478` embeds that file-derived result in `get_project_summary()` as `memory_outline`.
- `tools/story_load.py:37-52` reads the DB project summary, so replacing the summary field is sufficient to change `story_load`; no separate file read exists there.
- `tools/story_export.py` exports project frontmatter/sections but does not currently write `.story/memory.md`.
- `tools/story_import.py:39-47` clears and rebuilds all entity rows. Therefore a later import would erase DB memory unless memory is supplied in the imported project data or reinitialised deterministically. This is a Phase 2 concern.

### Project `extra` path

- `core/entity.py:223-263` `columns_for_insert()` stores unrecognized project frontmatter fields in the entity `extra` JSON.
- `tools/story_create.py:278-287` inserts the project through `columns_for_insert()`, so adding `memory` to the project data passed to that function can persist it in `extra` without a DB table or schema change.
- `tools/story_import.py:87-96` copies project frontmatter except `name` and `logline` into `extra`; it will preserve a `memory` key if present, but `_clear_all()` makes this a full rebuild rather than preservation of an existing DB value.
- `tools/story_export.py:114-119` flattens project `extra` into exported project frontmatter. The memory key must be deliberately handled so the projection does not accidentally become an unrelated project field or duplicate authority.

### Mutation surface

- `tools/story_edit.py:7-13` publicly advertises `update_story_memory`.
- `tools/story_edit.py:84-94` dispatches that action.
- `tools/story_edit.py:352-372` writes `.story/memory.md` through `python-frontmatter` and section replacement. It is the legacy file-based writer and must be removed or superseded, not preserved as a second authority.

### Dashboard

- `core/db.py:1010-1029` builds a `story_memory` object containing only project title-page fields (`name`, `logline`, `title_page`). It is not the new memory feature.
- `core/db.py:1050-1062` places that object in `story_data`.
- `src/dashboard/js/core.js:99-112` normalises and defaults `d.story_memory`, but no memory-dialog implementation exists.
- `src/dashboard/index.html:131-141` has the existing separator followed by Refresh. The Memory button belongs between the separator and Refresh.
- `tools/story_dashboard.py:338-343` directly reads `project.md` for title-page fields. This is a confirmed pre-DB architecture issue, already recorded in `tasks/task_25/DEFERRED_db_first_architecture_audit.md`; it is not part of the memory feature.
- `tools/story_dashboard.py:345-371` injects DB-derived data, so the dashboard memory dialog can consume a canonical DB payload without reading Markdown.

### Tool registration and skill

- `tools/story_describe.py` lists the old tool set and `story_edit` still describes `update_story_memory`; neither exposes `story_memory`.
- `__init__.py:67-121` registers the current story tools. `story_memory` is absent.
- `__init__.py:126-145` auto-refreshes only `story_dashboard`, `story_edit`, and `story_create`; `story_memory` needs an explicit decision and likely inclusion because it mutates DB data.
- Legacy documentation under `skills/story-loader/`, `skills/story-editor/`, `vault-conventions.md`, and older `plan/` files still describes the file-based memory contract. Only current plugin-facing docs should be changed in Phase 7; historical plan/task records should not be rewritten.

### Tests and baseline

- `tests/test_core.py:542-553` asserts creation of the placeholder memory file and placeholder headings. This is an obsolete expectation for the new design.
- `tests/test_core.py:597-620` asserts `memory_outline` exists and `memory` does not. This must be replaced by the new `memory` contract.
- `tests/test_phase2_db_reads.py:108-113` asserts the old absence of `memory` and presence of `memory_outline`. This must be replaced.
- The first test command without `PYTHONPATH=.` failed at collection because the repository's `conftest.py` was not loaded early enough by the invoked environment. The correct baseline command is:
  ```bash
  PYTHONPATH=. pytest tests/test_core.py tests/test_phase2_db_reads.py -q
  ```
- Baseline result: **105 passed**.

## Corrections to the implementation plan

1. Phase 1 can stay in `core/db.py` or use a small `core/memory.py`; no new DB table or migration is required.
2. Phase 2 must explicitly account for `story_import` clearing all entities. The v1 decision is to treat import as a full rebuild; therefore memory must be supplied in the imported project data or reinitialised deterministically. Do not claim import preserves an existing DB value.
3. Phase 3's `story_load` change is a contract replacement, not an additive alias. Existing tests expecting the placeholder key must be replaced.
4. Phase 4 must remove or supersede `story_edit(update_story_memory)`. Leaving it public would preserve two memory authorities.
5. Phase 6 must distinguish the existing dashboard `story_memory` title-page object from the new memory payload. The new feature needs a distinct, explicit key or a deliberate replacement of that object. This is a **medium-impact naming/shape decision** and is the only design question found in the audit.

## Medium-impact decision requiring user feedback

The dashboard already exposes `DASH.story.story_memory` as title-page metadata:

```json
{
  "name": "...",
  "logline": "...",
  "title_page": { "...": "..." }
}
```

The new memory dialog needs the four memory categories. Recommended low-confusion option: rename the dashboard payload key to `project`/`title_page` ownership where feasible and introduce `memory` for the new feature. A narrower option is to keep the existing key and add `memory`, but that leaves `story_memory` semantically ambiguous.

Please choose:

- **Option A (recommended):** dashboard payload uses `project` for project/title-page data and `memory` for the new memory block; remove or relocate the old `story_memory` name.
- **Option B:** keep the existing `story_memory` title-page key and add a new `memory` key; accept temporary naming ambiguity for compatibility.
- **Option C:** stop implementation and redesign the dashboard payload naming first.

## Phase 0 completion

No other blocking inconsistency was found. Phase 1 may begin after the dashboard naming decision is confirmed.

## Final checklist

- [x] Spec and plan assumptions checked against current code
- [x] All listed callers and tests inspected
- [x] Baseline test result recorded
- [x] Audit result added to this task file
- [x] Naming and legacy-code findings recorded
- [x] Medium-impact naming question raised
- [x] User selected dashboard payload naming Option A
- [x] Phase 0 formally closed after that selection
