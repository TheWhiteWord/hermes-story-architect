# Plan: `story_load` Redesign Implementation

Source spec: `tasks/task_20/story_load_redesign_spec.md`

Goal: reduce feature-scale load payload from ~47k to ~8-8.5k tokens via nested structure, embedded cross-refs, hybrid full/stub representation, and inverted `unfilled`.

---

## Phase 1: New Payload Builder — `core/db.py`

Rewrite `get_project_summary()` to produce the spec §2 nested JSON shape.

### Steps
1. **Nested tree build**: Query entities, build `acts[]` with literal `sequences[]` nesting containing `scenes[]`. Sort children by `order_key` (then `id` for stability) before emitting arrays. Drop `sequence_id`, `act_id`, `parent_id`, `order` fields from all entities.
2. **Character/plot/location/world dicts**: Build `characters`, `plots`, `locations`, `worlds` as dicts keyed by slug.
3. **Embedded cross-references**:
   - `scene.chars` from `character_scene` relations (replaces relation rows)
   - `character.rel` from `character_relationship` relations (id + label + feeling)
   - `plot.setups/crisis/climax/payoffs` from `plot_*` relations (ids only, drop description prose)
4. **Sections per entity** *(parallel with steps 1–3 — independent read path)*: Query `sections` table per entity via existing `get_entity_sections()`, emit heading names as string array. Omit key entirely when zero sections.
5. **Stub classification** *(inline during tree build)*:
   - Scene: stub when `status=="planned"` OR no `dramatic_role` (either sufficient). Stub form: `{"id": "slug"}` or `{"id": "slug", "chars": [...]}`. Full form otherwise.
   - Arc beat: stub when `label` empty → bare string in `character.arc[]`. Full form: object with label/scene/shift/y/sections.
   - Derive `scene.climax` single marker from 4 booleans (priority: inciting > story > act > seq).
6. **Unfilled inversion** *(depends on step 5 to skip stubs)*: Call existing `unfilled_fields()` per non-stub entity (merging column-stored fields into extra as today), invert `{entity: [fields]}` → `{field: [entities]}`.
7. **Memory outline** *(parallel with all — independent file read)*: Parse `## ` headings from `.story/memory.md`, emit `{heading, preview}` per section (first non-empty line, truncated ~120 chars).
8. **Confirmation string**: `"Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds."` (M = non-stub scenes)
9. **Drop all "drop" fields** from spec §3 — don't fetch what won't be emitted.
10. **Always emit `status`** even at default (overrides omit-defaults rule).

### Files
- `core/db.py` — `get_project_summary()` body replaced

### Parallel work within phase
- Steps 4 (sections) and 7 (memory outline) are independent of the tree build — can be factored as separate functions and tested in isolation.

### Checklist
- [ ] Nested act→sequence→scene tree with array-position order
- [ ] Characters/plots/locations/worlds as slug-keyed dicts
- [ ] Embedded chars, rel, plot scene-arrays (no flat `relations` key)
- [ ] Sections array per entity (omitted when empty)
- [ ] Scene stub classification (status planned OR no dramatic_role)
- [ ] Arc beat stub classification (label empty → bare string)
- [ ] Scene `climax` single marker derived from 4 booleans
- [ ] Inverted `unfilled` ({field: [entities]}, stubs excluded)
- [ ] Memory outline (headers + preview only)
- [ ] Confirmation string with counts
- [ ] All "drop" fields removed from query/output
- [ ] `status` always emitted

---

## Phase 2: Response Wrapper — `tools/story_load.py`

Simplify `_db_response` to match new payload shape.

### Steps
1. Remove old `entities`/`relations`/`memory` extraction logic from `_db_response`.
2. Pass through the new nested dict from `get_project_summary()` directly.
3. Prepend `loaded: True` and `confirmation` (already computed in builder).
4. Remove row-column counting logic (confirmation now comes from builder, not recomputed).

### Files
- `tools/story_load.py` — `handler` and `_db_response`

### Checklist
- [ ] `_db_response` no longer references `entities`, `relations`, `memory` keys
- [ ] Confirmation from builder, not recomputed from rows
- [ ] Memory outline passed through (not full text)
- [ ] Nested structure preserved in JSON output

---

## Phase 3: Tests — Replace Old Load Tests

All existing load tests assert the old column/relations format. Replace with new-shape assertions.

### Files & steps
- **`tests/test_core.py`**
  - Update `test_story_load_works_after_create` → assert nested `acts`, `characters` keys
  - Update `test_get_project_summary_includes_unfilled` → assert `{field: [entities]}` shape
  - Update `test_created_character_has_unfilled_fields` → assert inverted unfilled shape
- **`tests/test_phase2_db_reads.py`** (heaviest rewrite)
  - Remove: `test_load_returns_column_format`, `test_load_no_derived_arrays`, `test_load_no_sections_list`, `test_load_relations_completeness`
  - Replace with: nested structure assertions, sections presence, stub detection, embedded cross-refs, token budget (<8.5k for fixture), confirmation format
  - Update `TestTokenBudget` threshold from 5k → 8.5k
  - Update `TestNavigationalQueries` → navigate via nested tree (not relations.rows)
- **`tests/test_field_coverage.py`**
  - Update `test_create_load_retrieve` → find entity in nested dict (not `entities.rows`)
  - Update edit verification → check nested dict after edit
- **`tests/test_phase3_scenario.py`**
  - Update load assertions → check nested structure after edit/delete/reorder
- **`tests/test_arcs.py`**
  - Update confirmation assertion → new format ("N arc beats" → count from nested structure)

### Parallel work
- Each test file is independent — can be edited in parallel.

### Checklist
- [ ] test_core.py: 3 load tests updated for nested shape
- [ ] test_phase2_db_reads.py: column/relations tests removed, nested + sections + stub + budget tests added
- [ ] test_field_coverage.py: load assertions target nested dict
- [ ] test_phase3_scenario.py: load assertions target nested dict
- [ ] test_arcs.py: confirmation assertion matches new format
- [ ] No test references `result["entities"]["rows"]` or `result["relations"]["rows"]`
- [ ] No test references `result["memory"]` (now `result["memory_outline"]`)

---

## Phase 4: Cleanup & Naming Verification

Remove dead code and verify naming consistency with new state.

### Steps
1. **Remove dead code in load path**:
   - Old `scene_chars`/`plot_beats` merge blocks from `get_project_summary` (now handled by nested builder)
   - Unused relation queries that fed old `relations` key
2. **Naming convention sweep** (grep-based verification):
   - `core/db.py` load path: no `sequence_id`, `act_id`, `parent_id`, `order_key`, `location_id` references in the summary builder
   - `tools/story_load.py`: no `entities`, `relations`, `memory` references
   - Variable names in builder: use nested terminology (not flat relation terms)
3. **Remove legacy test patterns**:
   - `test_load_no_derived_arrays` (derived arrays are now the point)
   - `test_load_relations_completeness` (relations key gone)
   - Any assertion checking `"cols" in result["entities"]` or `"rows" in result["relations"]`
4. **Verify dashboard is unaffected** (`get_dashboard_data` is separate — keep its column-oriented logic intact).

### Parallel work
- Naming sweep can start as soon as Phase 1 lands (independent of tests).

### Checklist
- [ ] `core/db.py` load path: zero `sequence_id`/`act_id`/`parent_id`/`order_key`/`location_id` references
- [ ] `tools/story_load.py`: zero `entities`/`relations`/`memory` references
- [ ] Builder variable names use nested terminology (not flat relation terms)
- [ ] `get_dashboard_data()` untouched (still uses columns/relations for dashboard)
- [ ] No dead code from old builder remaining
- [ ] Old test assertions (column format, relations.rows, entities.cols) fully removed

---

## Phase 5: Final Verification

### Steps
1. Run `pytest tests/test_core.py tests/test_phase2_db_reads.py tests/test_arcs.py tests/test_phase3_scenario.py tests/test_field_coverage.py` — confirm all pass.
2. Load `save-the-children` fixture, measure JSON payload size: assert < 8,500 tokens (~34k chars).
3. Confirm confirmation message format matches spec §2.
4. Confirm stub scenes/arc beats render correctly in fixture (mix of full and stub).

### Checklist
- [ ] Full test suite passes
- [ ] Fixture payload < 8,500 tokens
- [ ] Confirmation message matches spec format
- [ ] Stub classification visible in fixture output
- [ ] `unfilled` inverted shape verified against fixture
- [ ] `memory_outline` present (not full memory text)
