# Story Memory Implementation Plan

**Source spec:** `tasks/task_25/memory_design_spec.md`

**Goal:** Implement the settled Hermes-lite story memory as DB-authoritative, with a dedicated `story_memory` tool, a bounded `story_load` payload, a frontmatter-only export, and a read-only dashboard dialog.

**Architecture:** The project DB stores the four memory arrays in `project.extra.memory`. `.story/memory.md` is a user-facing export/projection only. Runtime reads (`story_load`, `story_dashboard`) read the DB. `story_memory` mutates the DB. The dashboard receives memory in its existing injected payload and renders it in a small About-style dialog.

**Process rule:** Each phase follows the same loop:

1. Implement the smallest phase scope.
2. Verify the phase against the current code and the spec.
3. Look for wrong assumptions, missed paths, stale callers, and contract drift.
4. Resolve low-impact issues directly.
5. Stop and ask the user for medium/high-impact design changes.
6. Run the phase tests and the existing relevant suite before advancing.

Do not advance past a phase with unresolved issues.

---

## Phase 0 — Baseline audit before edits

**Objective:** Establish the current implementation and convert known code/spec differences into an implementation checklist.

**Files to inspect:**

- `tasks/task_25/memory_design_spec.md`
- `tasks/task_25/DEFERRED_db_first_architecture_audit.md`
- `tools/story_create.py`
- `core/db.py`
- `tools/story_load.py`
- `tools/story_edit.py`
- `tools/story_export.py`
- `tools/story_dashboard.py`
- `tools/story_describe.py`
- `__init__.py`
- `src/dashboard/index.html`
- `src/dashboard/js/core.js`
- `src/dashboard/js/navigation.js`
- `src/dashboard/css/components.css`
- `src/dashboard/css/base.css`
- `skills/hermes-story-architect/SKILL.md`
- relevant tests: `tests/test_core.py`, `tests/test_phase2_db_reads.py`, dashboard tests, integration tests

**Current confirmed inconsistencies to validate:**

- `tools/story_create.py:248-266` creates `.story/memory.md` directly with placeholder Markdown sections; the v1 DB-first design must initialize `project.extra.memory` instead.
- `core/db.py:100-124` `get_memory_outline()` reads and parses `.story/memory.md`; it must be replaced by a DB-backed memory projection.
- `core/db.py:127+` and `get_project_summary()` still expose `memory_outline`; the v1 contract requires full bounded `memory`.
- `tools/story_load.py` delegates to `get_project_summary()`, so the load contract changes in the DB/core phase.
- `tools/story_export.py:97-98` exports `project.md` but does not project memory to `.story/memory.md`.
- `tools/story_dashboard.py:345-370` injects DB-derived dashboard data, which is the correct place to add memory; do not make the dashboard read Markdown.
- `tools/story_dashboard.py:338-343` also reads `project.md` directly for title-page fields; this is the deferred architectural issue, not part of memory implementation.
- `tools/story_edit.py:352-372` has the old `update_story_memory` file path; the new tool should supersede it. Do not leave two competing memory mutation surfaces.
- `tools/story_describe.py` currently enumerates the old tool set and has no `story_memory` schema.
- `__init__.py:127-145` auto-refreshes after `story_edit`, `story_create`, and `story_dashboard`; decide during this audit whether `story_memory` must be included.
- `src/dashboard/index.html:131-141` has the existing sidebar separator and Refresh action; the Memory action belongs immediately above this block.
- `src/dashboard/js/core.js:100-112` already normalises `d.story_memory`, which is useful but must be verified against the actual dashboard payload.
- Existing tests assert the placeholder `memory_outline` and placeholder `memory.md`; these expectations will need to be replaced by the new contract, not preserved as compatibility requirements.

**Verification:**

- Run a focused read-only test subset before editing:
  ```bash
  pytest tests/test_core.py tests/test_phase2_db_reads.py -q
  ```
- Record any pre-existing failures separately. Do not attribute them to the memory implementation.
- Produce a short audit result at the end of the phase, listing any medium/high-impact design questions before implementation continues.

**Gate:** If the audit finds that `project.extra.memory` is not preserved by the existing project insert/export path, or that the current DB shape cannot represent it without a schema change, stop and ask the user before Phase 1.

---

## Phase 1 — DB memory model and bounded serialization

**Objective:** Add one canonical in-memory memory shape and its validation/budget helpers to the DB layer.

**Files:**

- Modify: `core/db.py`
- Create if useful: `core/memory.py` only if `core/db.py` would otherwise become the place for both DB access and memory policy; prefer the existing module if it can hold the small helpers cleanly
- Test: `tests/test_memory.py` (new focused test module)

**Implementation shape:**

```python
MEMORY_CATEGORIES = ("decisions", "directions", "open_questions", "continuity_warnings")
MEMORY_CHAR_LIMIT = 3000
MEMORY_ENTRY_LIMIT = 300
```

Add small helpers for:

- returning a complete four-category memory structure with empty arrays;
- reading/writing `project.extra.memory` through the project entity;
- validating category names and entry strings;
- rejecting empty entries, overlong entries, and exact duplicates;
- computing the deterministic serialized frontmatter length used for the 3,000-character budget;
- returning per-category counts and total usage.

Do not add a new DB table. Do not add entry IDs, timestamps, confidence, or status fields.

**Important implementation detail:** The budget is over serialized frontmatter for the four categories, not the whole Markdown wrapper. The serializer must be deterministic so the same DB payload always produces the same count.

**Tests:**

- empty project memory returns all four keys;
- valid entries are preserved in order;
- unknown categories are rejected;
- empty entries are rejected;
- an entry over 300 characters is rejected;
- exact duplicates are rejected;
- total serialized frontmatter over 3,000 is rejected;
- per-category counts and usage are correct;
- a project without `extra.memory` is treated as empty memory, not as a file read.

**Verification:**

```bash
pytest tests/test_memory.py -q
pytest tests/test_core.py -q
```

**Audit after implementation:**

- Search for every caller of `get_memory_outline()` and every `memory_outline` reference.
- Confirm no new helper reads `.story/memory.md`.
- Confirm no caller assumes memory is an entity row or `sections` row.

**Gate:** Any need for a new table, migration, or new entry record structure is a design escalation. Stop and ask.

---

## Phase 2 — Project creation and import/export data ownership

**Objective:** Make DB memory the operational source and remove the placeholder memory file as a creation dependency.

**Files:**

- Modify: `tools/story_create.py`
- Modify: `tools/story_export.py`
- Modify: `tools/story_import.py` only if it currently overwrites project `extra` and would erase memory
- Modify: `core/db.py` if project creation needs a shared initializer
- Test: `tests/test_core.py` and new memory tests

**Implementation:**

- On project creation, insert `project.extra.memory` with the four empty arrays during the same DB transaction as the project entity.
- Do not create `.story/memory.md` as part of normal project creation. The export phase owns that projection.
- Preserve the existing `project.md` creation path for now; its broader file-first cleanup is deferred.
- On import, preserve `project.extra.memory` when merging project frontmatter. Do not let an old `memory.md` be the authority.
- No compatibility fallback that reads memory from `.story/memory.md`.

**Tests:**

- new project has `project.extra.memory` with four empty arrays;
- project creation does not treat memory as a required file;
- import does not erase existing DB memory;
- export produces `.story/memory.md` with frontmatter only and no Markdown body;
- exported memory preserves category order and entry order;
- exported memory is absent or ignored as an operational source.

**Verification:**

```bash
pytest tests/test_core.py tests/test_memory.py -q
```

**Audit after implementation:**

- Inspect `_create_project()` end to end.
- Inspect `story_import` project handling and `story_export._export_all()`.
- Search for `.story/memory.md` reads and writes. Only the export writer should remain.

**Gate:** If removing the creation-time file breaks project resolution or an existing contract that is not a placeholder, stop and ask before changing it.

---

## Phase 3 — `story_load` contract

**Objective:** Replace `memory_outline` with the full bounded DB-backed memory block.

**Files:**

- Modify: `core/db.py`
- Modify: `tools/story_load.py`
- Modify: `tools/story_describe.py` description/schema text
- Modify: `skills/hermes-story-architect/SKILL.md` project-entry guidance
- Test: `tests/test_phase2_db_reads.py`, `tests/test_core.py`, memory tests

**Implementation:**

- `get_project_summary()` returns:
  ```json
  {
    "memory": {
      "status": "ready",
      "content": "...",
      "usage": "1842/3000",
      "counts": {
        "decisions": 4,
        "directions": 3,
        "open_questions": 2,
        "continuity_warnings": 3
      },
      "categories": {
        "decisions": ["..."],
        "directions": ["..."],
        "open_questions": ["..."],
        "continuity_warnings": ["..."]
      }
    }
  }
  ```
  The final response shape should stay consistent with the existing nested `story_load` design and should not be broadened without need.
- `story_load` must not read `.story/memory.md`.
- The skill must state that `story_load` is the project-entry point and exposes memory once at project start.
- The tool description must stop calling memory an “index” or “outline”.

**Tests:**

- `story_load` returns the new `memory` key;
- it returns all four categories, including empty ones;
- it returns the full entries, not previews;
- it never returns `memory_outline`;
- it works when `.story/memory.md` is absent;
- it works when `.story/memory.md` is stale or contains unrelated text;
- existing structural load behavior remains unchanged.

**Verification:**

```bash
pytest tests/test_phase2_db_reads.py tests/test_core.py tests/test_memory.py -q
```

**Audit after implementation:**

- Search all load consumers and tests for `memory_outline`.
- Search skill/reference docs for the old “memory outline” contract.
- Confirm the load payload does not duplicate memory inside the project/entity payload.

**Gate:** If a structural load consumer requires the old key, classify that as a contract change and ask before preserving a compatibility alias.

---

## Phase 4 — Dedicated `story_memory` tool

**Objective:** Add the sole v1 memory mutation surface.

**Files:**

- Create: `tools/story_memory.py`
- Modify: `__init__.py`
- Modify: `tools/story_describe.py`
- Modify: `skills/hermes-story-architect/SKILL.md`
- Test: new `tests/test_memory.py` or `tests/test_story_memory.py`

**Tool contract:**

```text
story_memory(
  action: "add" | "remove" | "replace",
  project: str,
  category: "decisions" | "directions" | "open_questions" | "continuity_warnings",
  entry: str,                    # add
  old_entry: str,                # replace/remove
  new_entry: str                 # replace
)
```

- `add(category, entry)` appends to the category.
- `remove(category, old_entry)` removes the full matching entry.
- `replace(category, old_entry, new_entry)` replaces the full matching entry.
- No entry number, ID, or substring-only mutation.
- Exact duplicate add is a no-op.
- Overlong entries and total-budget overflow return the compact error contract from the spec.
- Successful responses return operation, category, changed entry where applicable, usage, and counts.
- Errors return reason, usage, affected-category entries, and `action_required` where the model must decide what to do.
- No confirmation workflow in the tool. The agent policy handles critical operations.
- Update the old `story_edit(action="update_story_memory")` documentation and path so it cannot remain a competing memory writer. Remove it if it is purely obsolete; do not leave two mutation authorities.

**Tests:**

- schema exposes exactly the three actions and four categories;
- add persists to DB;
- add rejects unknown category, empty entry, overlong entry, duplicate, and over-budget payload;
- remove targets the complete entry and reports the right category count;
- replace targets the complete entry and enforces the new entry limit;
- failed operations do not mutate DB;
- success response is compact and has the agreed shape;
- auto-refresh decision for `story_memory` is covered if the hook includes it.

**Verification:**

```bash
pytest tests/test_memory.py tests/test_story_memory.py tests/test_core.py -q
```

**Audit after implementation:**

- Search for every `update_story_memory` caller, reference, and test.
- Search for direct `.story/memory.md` writes.
- Confirm the tool reads/writes DB only.
- Confirm the tool does not depend on the Markdown export existing.

**Gate:** If removing the old `update_story_memory` path would break a user-facing contract beyond this project’s planned feature, stop and ask before removal.

---

## Phase 5 — Export projection

**Objective:** Project DB memory into the human-facing `.story/memory.md` file.

**Files:**

- Modify: `tools/story_export.py`
- Test: memory/export tests and round-trip tests

**Implementation:**

- Export the project entity’s `project.extra.memory` to frontmatter-only `.story/memory.md`.
- Emit the four categories in fixed order.
- Emit no Markdown body.
- Do not read the file as an operational source.
- Keep the export deterministic and human-readable.
- Do not add timestamps, IDs, or migration metadata.

**Tests:**

- export with empty memory creates/overwrites a valid frontmatter-only file;
- export with entries preserves all categories and order;
- export does not add a Markdown body;
- changing the file does not change DB memory;
- subsequent DB memory change overwrites the projection on export.

**Verification:**

```bash
pytest tests/test_memory.py tests/test_round_trip.py -q
```

**Audit after implementation:**

- Confirm export is the only remaining writer of `.story/memory.md`.
- Confirm no read path in core/tools/dashboard depends on the export file.

---

## Phase 6 — Dashboard payload and read-only dialog

**Objective:** Expose DB-backed memory in the existing dashboard through the settled small About-style dialog.

**Files:**

- Modify: `core/db.py` `get_dashboard_data()`
- Modify: `tools/story_dashboard.py` injection only if required by the verified payload shape
- Modify: `src/dashboard/index.html`
- Modify: `src/dashboard/js/core.js` only if normalise needs a real fix
- Create: `src/dashboard/js/panels/memory-dialog.js` or add a small memory module in the existing panel structure
- Modify: `src/dashboard/css/components.css` or create a narrowly scoped dialog style section
- Modify: `src/dashboard/css/base.css` only if a shared overlay token is missing
- Modify: `tools/story_dashboard.py` `JS_ORDER` if a new JS module is added
- Test: dashboard assembly/integration tests; add focused DOM/payload assertions where the existing test style supports them

**Implementation:**

- Add `story_memory` to the DB-derived dashboard payload.
- Add the sidebar **Memory** button immediately above the existing Refresh action.
- Do not add a navigation view or change the active view.
- Render the dialog from `DASH.story.story_memory` only.
- Reuse existing theme tokens, button styles, radius, type scale, and spacing.
- Show total usage `x/3000`, one total bar, four fixed categories, counts, entries, empty states, and read-only notice.
- Keep the dialog compact, scrollable, and closable via button, Escape, and backdrop.
- Use a restrained existing-style accent for `continuity_warnings`; no new design system.
- Do not add editing controls.

**Tests:**

- dashboard payload contains DB memory;
- payload does not require `.story/memory.md`;
- dashboard HTML contains the Memory action and dialog hooks;
- dialog renders all four categories, empty state, usage, and read-only notice;
- dialog closes through the agreed paths;
- no memory file fetch/parse code appears in dashboard JS;
- existing dashboard assembly and data injection tests remain green.

**Verification:**

```bash
pytest tests/test_story_dashboard_integration.py tests/test_story_dashboard_stats.py -q
```

Use the project’s established browser/UI verification method if the dashboard tests do not cover rendered interaction.

**Audit after implementation:**

- Compare the dialog against the spec’s settled visual contract.
- Check narrow-screen behavior and scroll behavior.
- Check that the existing detail panel and sidebar toggle are unaffected.
- Confirm the Memory button is above Refresh and not inside the navigation view list.

**Gate:** If the existing dashboard has no reusable modal convention and adding one would require a broad UI framework or refactor, stop and ask; do not overbuild a new modal system.

---

## Phase 7 — Tool registration, documentation, and cleanup

**Objective:** Make the new memory surface discoverable and remove obsolete memory wording/paths.

**Files:**

- Modify: `__init__.py`
- Modify: `tools/story_describe.py`
- Modify: `skills/hermes-story-architect/SKILL.md`
- Modify: any Story Architect reference files that still describe `memory_outline`, `update_story_memory`, or placeholder memory sections
- Modify tests that assert the old placeholder contract
- Do not modify: `tasks/task_25/DEFERRED_db_first_architecture_audit.md` except to add discovered audit items if needed

**Implementation:**

- Register `story_memory` with the plugin.
- Add it to `story_describe` tool enumeration and schema output.
- Add the project-entry and memory-use rules from the spec to the skill.
- Remove the old `update_story_memory` action from the public schema and implementation if no compatibility path is approved.
- Remove `memory_outline` documentation and placeholder memory-section guidance.
- Ensure `story_memory` is included in the post-tool auto-refresh decision if the hook is intended to refresh the dashboard after DB mutations.

**Tests:**

- plugin registration exposes `story_memory`;
- `story_describe` returns the new tool schema;
- skill text contains the project-entry rule and the no-automatic-canon rule;
- no public tool description still advertises `update_story_memory` or `memory_outline`.

**Verification:**

```bash
pytest -q
```

Run the project’s standard test command from `pyproject.toml` if it differs.

**Audit after implementation:**

- Search the entire repository for:
  - `memory_outline`
  - `update_story_memory`
  - `get_memory_outline`
  - `.story/memory.md` reads
  - placeholder `Continuity notes`, `World events`, or `Character knowledge` memory scaffolding
- Every remaining occurrence must be either an intentional export boundary, a test for the new contract, or a documented deferred issue.

---

## Phase 8 — End-to-end verification and handoff

**Objective:** Prove the whole memory loop works and is DB-authoritative.

**Files:** no new production files unless a test reveals a real defect.

**End-to-end flow:**

1. Create a project.
2. Confirm DB project memory has four empty categories.
3. Confirm `.story/memory.md` is not required for runtime operation.
4. Use `story_memory` to add one entry in each category.
5. Confirm `story_load` returns all entries and correct usage.
6. Confirm the dashboard payload and dialog show the same entries.
7. Confirm `story_export` writes the frontmatter-only projection.
8. Manually modify or delete `.story/memory.md`.
9. Confirm `story_load`, `story_memory`, and the dashboard still use DB state.
10. Exercise budget overflow, per-entry limit, duplicate, remove, and replace failures.
11. Confirm the full test suite passes.

**Final checks:**

```bash
git status --short
git diff --check
pytest -q
```

**Handoff note:** Report exactly what was implemented, what was intentionally left out, and any remaining deferred audit items. Do not claim the DB-first architecture is fully repaired outside the memory scope; the separate audit note records the broader cleanup.

---

## Verification policy for every phase

Before advancing:

- inspect the actual diff for the phase;
- run the focused tests;
- run the nearest existing regression tests;
- search for stale callers of replaced contracts;
- compare implementation against the source spec, not against the previous plan;
- record issues as either:
  - resolved low-impact implementation detail;
  - medium/high-impact design question requiring user feedback;
  - deferred architecture issue.

A phase is complete only when its code, tests, documentation, and call sites agree.
