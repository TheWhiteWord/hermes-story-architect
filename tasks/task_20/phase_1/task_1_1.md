# Task 1.1: Rewrite `get_project_summary()` — Nested Payload Builder

## Goal
Replace the flat column/relation output of `get_project_summary()` (`core/db.py:84`) with the nested JSON shape from spec §2, including embedded cross-references, stub classification, and the new confirmation string.

**Scope:** `core/db.py` — full rewrite of `get_project_summary()` body. No other files touched.

---

## Current State (verified against code)

`get_project_summary()` at `core/db.py:84-167` currently:
- Returns `{project, entities: {cols, rows}, relations: {cols, rows}, unfilled}`
- Queries all entities flat (`ORDER BY type, id`), all relations flat (`ORDER BY kind, from_id, to_id`)
- Builds `scene_chars` and `plot_beats` dicts from relations but only uses them for the unfilled merge
- Merges `location_id` column into `extra["location"]` for scenes — column is always NULL (import writes the `location_scene` relation, not this column)
- Merges `one_sentence` and `status` columns into `extra` for unfilled detection
- Does NOT sort entities by `order_key` or build any nested structure
- Returns `unfilled` as `{entity_id: [field_names]}` (spec inverts this)

### Entry-point flow
```
tools/story_load.py:handler() → core.db.get_project_summary(project_path) → _db_response(summary)
```

Only consumer of `get_project_summary`: `tools/story_load.py:50`. Safe to rewrite.

---

## Target State (spec §2)

Return dict with keys:
```json
{
  "loaded": true,
  "confirmation": "Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds.",
  "project": { ... },
  "acts": [ { "sequences": [ { "scenes": [...] } ] } ],
  "characters": { "<slug>": {...} },
  "plots": { "<slug>": {...} },
  "locations": { "<slug>": {...} },
  "worlds": { "<slug>": {...} },
  "unfilled": { "<field>": ["<slug>", ...] },
  "memory_outline": { "status": "...", "sections": [...] }
}
```

---

## Implementation Plan

### Step 1: Nested tree build
- Query all entities (same columns as today, minus none — we still need all for cross-refs)
- Build `act → sequence → scene` nesting using `parent_id` (scene.parent_id → sequence.id, sequence.parent_id → act.id)
- Sort children by `(order_key, id)` before emitting (order_key alone is unstable when 0)
- Drop `sequence_id`, `act_id`, `parent_id`, `order_key`, `location_id` from emitted output
- Acts keep: `id`, `title`, `status`, `value`, `value_open`, `value_close`, `sections`
- Sequences keep: `id`, `title`, `status`, `value`, `value_open`, `value_close`, `sections`
- Full scenes keep: `id`, `title`, `status`, `dramatic_role`, `chars`, `loc`, `climax`, `sections`

### Step 2: Character/plot/location/world dicts
- Keyed by slug (entity `id`)
- Characters: `name`, `one_sentence`, `story_role`, `arc_type`, `arc_complete`, `rel`, `sections`, `arc`
- Plots: `name`, `one_sentence`, `status`, `plot_type`, `plot_scope`, `value_arc`, `characters`, `setups`, `crisis`, `climax`, `payoffs`, `sections`
- Locations: `name`, `one_sentence`, `sections`
- Worlds: `name`, `one_sentence`, `sections`

### Step 3: Embedded cross-references
- `scene.chars` from `character_scene` relations (from_id=character, to_id=scene → append from_id to scene's chars list)
- `scene.loc` from `location_scene` relations (to_id=scene → from_id is location slug)
- `character.rel` from `character_relationship` relations — parse `note` JSON for `{label, feeling}`
- `plot.setups/crisis/climax/payoffs` from `plot_*` relations (ids only, drop note)

### Step 4: Stub classification (inline during tree build)
- **Scene stub:** `status == "planned"` OR no `dramatic_role` (either condition sufficient)
  - Stub form: `{"id": "<slug>"}` or `{"id": "<slug>", "chars": [...]}` when characters present
  - Full form: object with all kept fields
- **Arc beat stub:** `label` empty (unnamed skeleton)
  - Stub form: bare string `"<beat-id>"`
  - Full form: object with `label`, `scene`, `shift`, `y`, `is_crisis`, `is_climax`, `sections`

### Step 5: `climax` single marker
- Derive from 4 booleans in extra JSON: `is_inciting_incident`, `is_story_climax`, `is_act_climax`
- Priority: `inciting > story > act > seq`
- Note: constants.py has all 4 booleans: `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`. Priority: `inciting > story > act > seq`. If none present, emit `null`.

### Step 6: Inverted `unfilled`
- Call existing `unfilled_fields(entity_type, extra)` per non-stub entity
- Invert: `{entity_id: [fields]}` → `{field_name: [entity_ids]}`
- Skip stub entities (they're maximally unfilled by definition)
- Merge `status` column into extra before calling `unfilled_fields` (preserve current behavior)
- Merge relation-sourced fields (`characters`, `location`) into extra for accurate scene unfilled detection

### Step 7: Confirmation string
```
Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds.
```
- N = total scenes, M = non-stub (developed) scenes

### Step 8: Drop "drop" fields (spec §3)
Do NOT emit these in any entity type:
- Project: `screenplay_title`, `credit`, `author`, `contact`, `draft_date`, `draft`
- Character: `arc_value`, `arc_value_at_open/close`, `goals_short`, `goals_long`, `knowledge`
- Scene: `order`, `sequence_id`, `act_id`, `parent_id`, `heading`, `time_of_day`, `value`, `value_open`, `value_close`, `conflict_levels`
- Sequence/Act: `climax_scene_id`, `purpose`/`act_objective`, `primary_plot`
- Arc: `action`, `gap`, `choice`
- World: `rules`

### Step 9: Always emit `status`
Override the omit-defaults rule for `status` — always include even when empty/default.

---

## Code anchors

| What | Where |
|---|---|
| Current `get_project_summary()` | `core/db.py:84-167` |
| `unfilled_fields()` | `core/entity.py:151-159` |
| `ENTITY_SCHEMAS` | `core/constants.py` |
| Scene schema (climax booleans) | `core/constants.py:123-126` |
| `get_entity_sections()` (for sections task) | `core/db.py:170-180` |
| Only caller of `get_project_summary` | `tools/story_load.py:50` |

---

## Corrections to plan.md

| Plan says | Reality | Resolution |
|---|---|---|
| Step 1: "Sort children by `order_key`" | Fixture arcs have `order_key=0` (TEXT→REAL coercion on insert) | Sort by `(order_key, id)` tuple for stability |
| Step 5: "Derive from 4 booleans incl. `is_seq_climax`" | All 4 booleans exist: `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax` | Priority: `inciting > story > act > seq`. All 4 used. |
| Step 3: "`scene.loc` from `location_scene` relations" | Current merge uses `location_id` column (always NULL) | Switch to relation-based (spec is correct, current code has a latent gap) |

---

## Test impact

This is Phase 1 — **no tests updated in this task**. Tests are Phase 3.
After this task: all load tests will fail (expected). That's the red baseline.

---

## Legacy code removal

This task deletes:
- Old `ent_cols`/`ent_rows` flat-entity query and output
- Old `rel_cols`/`rel_rows` flat-relation query and output
- Old `scene_chars` merge into `extra["characters"]` (only used for unfilled)
- Old `plot_beats` merge into extra (only used for unfilled)
- Old `confirmation` logic (counts_arc, counts_scene, etc.) — replaced by builder
- Old `unfilled_map` keyed by entity_id — replaced by inverted unfilled

---

## Checklist

- [x] `get_project_summary()` returns nested `acts[]` with `sequences[]` → `scenes[]`
- [x] Children sorted by `(order_key, id)` — stable even when order_key is 0
- [x] `sequence_id`, `act_id`, `parent_id`, `order_key`, `location_id` fields absent from output
- [x] `characters`, `plots`, `locations`, `worlds` are slug-keyed dicts (not arrays)
- [x] `scene.chars` populated from `character_scene` relations
- [x] `scene.loc` populated from `location_scene` relation (not `location_id` column)
- [x] `character.rel` populated from `character_relationship` relations with `{id, label, feeling}`
- [x] `plot.setups/crisis/climax/payoffs` populated from `plot_*` relations (ids only)
- [x] Scene stubs: `status=="planned"` OR no `dramatic_role` → `{"id": "slug"}` form
- [x] Scene stubs with chars: `{"id": "slug", "chars": [...]}`
- [x] Arc beat stubs: `label` empty → bare string in `character.arc[]`
- [x] `climax` single marker: derived from booleans, priority inciting > story > act > seq
- [x] `status` always emitted (even at default)
- [x] All spec §3 "drop" fields absent from output
- [x] `unfilled` inverted: `{field: [entity_ids]}`, stubs excluded
- [x] Confirmation string matches new format with `(M developed)`
- [x] Project fields emitted per spec §2 (name, logline, genre, setting, status, spine, etc.)

---

## Final Brief

### Changes Made
- **`core/db.py`**: Complete rewrite of `get_project_summary()` body
  - New top-level shape: `{loaded, confirmation, project, acts[], characters{}, plots{}, locations{}, worlds{}, unfilled, memory_outline}`
  - `acts` → `sequences` → `scenes` nested via `parent_id`
  - Characters, plots, locations, worlds as slug-keyed dicts
  - Embedded cross-refs: `scene.chars` (from `character_scene`), `scene.loc` (from `location_scene`), `character.rel` (from `character_relationship`), `plot.setups/crisis/climax/payoffs` (from `plot_*` relations)
  - Scene stub classification: `status=="planned"` OR no `dramatic_role` → compact `{"id": "slug"}` or `{"id": "slug", "chars": [...]}`
  - Arc beat stub classification: `label` empty → bare string in `character.arc[]`
  - `climax` single marker from 4 booleans: `is_inciting_incident` > `is_story_climax` > `is_act_climax` > `is_sequence_climax`
  - `status` always emitted (overrides omit-defaults)
  - Drop fields from spec §3 excluded from output
  - Unfilled inverted: `{field: [entity_ids]}`, stubs excluded
  - `memory_outline` parsed from `## ` headings in `.story/memory.md`
  - Confirmation string: `"Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds."`
- **`core/db.py`**: Added helper `_build_memory_outline(project_path)` for memory header parsing
- **`core/db.py`**: Added `_PROJECT_DEFAULTS` dict for project field filtering

### Bug fixes during implementation
- **Children sort stability**: Fixed tuple sorting where `order_key=0` causes instability — now sorts by `(order_key, id)`
- **Sequence/scene ID passing**: Fixed `TypeError: unhashable type: 'dict'` — build functions now accept IDs, not dicts
- **Act `value` defaults**: Fixed `value` field default from `""` to `"Value not set"` to match schema default (so omit-defaults works correctly)
- **Relation-sourced unfilled**: Added `scene_chars`/`scene_loc` merge into extra before unfilled check (scenes now correctly show as not-unfilled for `characters`/`location` when they have them)

### Deferred Items
None.

### Test Impact
Expected red baseline — `test_get_project_summary_includes_unfilled` now fails because it asserts the old `{entity_id: [fields]}` format. Will be fixed in Phase 3 (tests).

### Files Modified
- `core/db.py` — `get_project_summary()` body rewritten (lines 84-515 approx)
- `core/db.py` — Added `_build_memory_outline()` helper (lines 84-117 approx)
- `core/db.py` — Added `_PROJECT_DEFAULTS` dict (lines 84-97 approx)

### Files NOT Modified (per task scope)
- `tools/story_load.py` — handled in Phase 2
- `tests/*` — handled in Phase 3
- `core/constants.py` — untouched
- `core/entity.py` — untouched (only used `unfilled_fields()` from it)
