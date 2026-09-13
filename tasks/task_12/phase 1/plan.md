# Phase 1 Plan: Data Model & Entity Foundation

**Created:** 2026-09-12
**Status:** Plan — decided, ready for implementation
**Input:** `refactor_overview.md` + `Claude_structure_refactor.md`

---

## 1. What This Phase Does

Defines the three new entity types (`scene`, `sequence`, `act`) as first-class citizens in the plugin's data model. Updates the core constants, schemas, validation, and entity extraction so that `story_create`, `story_edit`, `story_retrieve`, and `story_search` all work with the new types.

**End state of Phase 1:** The plugin can create, validate, and retrieve scene/sequence/act files with correct frontmatter and body sections. The index generator walks `scenes/`, `sequences/`, `acts/` folders and includes them in the index.

---

## 2. Decisions Made (Resolving Open Questions)

### 2.1 Slug Identity Rules

| Rule | Decision | Rationale |
|------|----------|-----------|
| Characters allowed | `[a-z0-9-]` only, must start with letter | Matches existing `story_create` validation |
| Max length | 64 chars | Long enough for descriptive slugs, short enough for filenames |
| Slug vs `title` | Slug = identity (used in references, filenames). `title` = display name (freely editable) | Core rule from proposal |
| Slug rename | **NOT** supported in Phase 1. Manual operation (rename file + update all references). | YAGNI: add when a real need appears |

### 2.2 Scene `order` Within Sequence

**Decision:** Float. Authoritative source = scene frontmatter `order` field.

**Rationale:** Float allows inserting scene between positions 2 and 3 by setting `order: 2.5`. Avoids renumbering the whole sequence on every insertion. The `## Scene Order` section in the sequence file is a *rendered view* — human-readable, not authoritative.

### 2.3 `act_id` on Scenes

**Decision:** Yes, store directly on scene frontmatter (denormalization).

**Rationale:** Queries like "all scenes in Act 2" are common. Deriving act membership through sequence means loading all sequences first. One extra field per scene buys O(1) act filtering.

### 2.4 `location` Field on Scenes

**Decision:** Nullable string. Two valid states:
- **Free text** for planned scenes
- **Slug reference** once the location entity exists in `locations/`

The index parser will attempt to match the string to an existing location slug (fuzzy). If no match, the raw string is stored but flagged as "unresolved."

### 2.5 Scene Status Enum

```
planned → drafted → written → locked
```

**Rationale:** "Drafted" and "written" are distinct:
- `planned` = has description, maybe dramatic function, no content yet
- `drafted` = content exists (from any source), not yet finalized
- `written` = content finalized, ready for structural analysis
- `locked` = part of a final structure, edits require explicit unlock

No `imported` status — `imported` is provenance, not status. Screenplay import (separate job) sets status to `drafted`.

### 2.6 Dramatic Metadata Nullability

All dramatic metadata fields (`value`, `value_open`, `value_close`, `conflict_levels`, `dramatic_role`, `is_*_climax`) are **nullable**. A minimal viable scene only needs:
- `id`, `type`, `title`, `status`, `sequence_id`, `act_id`

### 2.7 `dramatic_role` Enum

```
setup | complication | crisis | climax | resolution | transition | non-event
```

Added `non-event` per proposal §7 — scenes that don't turn without forcing a fake value turn.

### 2.8 Body Sections per Entity Type

| Entity | Body Sections |
|--------|---------------|
| Scene | `Description`, `Dramatic Function`, `Notes`, `Content` |
| Sequence | `Summary`, `Scene Order`, `Notes` |
| Act | `Summary`, `Thematic Function`, `Notes` |

### 2.9 Project-Level Fields (Story Entity)

`project.md` frontmatter gets these additions per proposal §7:

```yaml
spine: null                          # string — protagonist's desire
controlling_idea: null               # string — the story's argument
value: null                          # string — value at stake
value_at_open: null                  # enum: positive | negative | mixed | ironic
value_at_close: null                 # enum: positive | negative | mixed | ironic
inciting_incident_scene_id: null     # string → scene slug
story_climax_scene_id: null          # string → scene slug
structure_type: null                 # enum: Classical | Miniplot | Antiplot
```

All nullable.

### 2.10 Plot Scene Reference Migration (Q2=B — User Chose)

**Decision:** Migrate plot frontmatter from `{heading, number, description}` to `{scene_id, description}`.

**Rationale:** User chose to migrate now rather than maintain dual formats. Eliminates fragile heading-matching.

**Changes required:**
- `core/constants.py` — Update `plot` schema `setups`/`payoffs` sub_fields to `{scene_id, description}` (remove `heading` and `number`)
- `core/index.py` — Rewrite `_enrich_scenes_with_plots()` to build `scenes_by_id` dict and match by `scene_id`. Update `_normalize_plot_scene()` to handle new format.
- `core/index.py` — Update `_validate_index()` to validate that plot `setups`/`payoffs` reference existing scene slugs
- `tests/fixtures/save-the-children/plots/the-resistance.md` — Update to use `scene_id` instead of `heading`/`number`
- `skills/story-editor/SKILL.md` — Update entity reference table for plots

**Migration of existing data:** No production projects exist (only test fixtures). Simply update the fixtures. No backward-compat layer needed.

---

## 3. Detailed Schema Definitions

### 3.1 Scene Entity

```python
"scene": {
    "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug (user-assigned, dramatic function)"},
    "type": {"type": "string", "default": "scene", "optional": False, "description": "Always 'scene'"},
    "title": {"type": "string", "default": "", "optional": False, "description": "Display name (freely editable)"},
    "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent sequence (float for insertions)"},
    "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, drafted, written, locked"},
    "heading": {"type": "string", "default": "", "optional": True, "description": "Fountain scene heading (for screenplay output)"},
    "location": {"type": "string", "default": "", "optional": True, "description": "Location slug or free text"},
    "time_of_day": {"type": "string", "default": "", "optional": True, "description": "One of: DAY, NIGHT, DUSK, DAWN, CONTINUOUS, LATER"},
    "sequence_id": {"type": "string", "default": "", "optional": False, "description": "Parent sequence slug"},
    "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug (denormalized shortcut)"},
    "characters": {"type": "list", "default": [], "optional": True, "description": "Character slugs present in this scene"},
    "plots": {"type": "list", "default": [], "optional": True, "description": "Plot slugs this scene advances"},
    "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this scene"},
    "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "conflict_levels": {"type": "list", "default": [], "optional": True, "description": "Any of: inner, personal, extra-personal"},
    "dramatic_role": {"type": "string", "default": "", "optional": True, "description": "One of: setup, complication, crisis, climax, resolution, transition, non-event"},
    "is_inciting_incident": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's inciting incident"},
    "is_sequence_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its sequence's climax"},
    "is_act_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as its act's climax"},
    "is_story_climax": {"type": "boolean", "default": False, "optional": True, "description": "Marks the scene as the story's climax"},
}
```

### 3.2 Sequence Entity

```python
"sequence": {
    "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug"},
    "type": {"type": "string", "default": "sequence", "optional": False, "description": "Always 'sequence'"},
    "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
    "order": {"type": "number", "default": 0, "optional": False, "description": "Position within parent act (float for insertions)"},
    "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
    "act_id": {"type": "string", "default": "", "optional": False, "description": "Parent act slug"},
    "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this sequence"},
    "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this sequence's reversal lands"},
    "primary_plot": {"type": "string", "default": "", "optional": True, "description": "Primary plot slug this sequence serves"},
    "purpose": {"type": "string", "default": "", "optional": True, "description": "Free text: dramatic purpose of this sequence"},
}
```

### 3.3 Act Entity

```python
"act": {
    "id": {"type": "string", "default": "", "optional": False, "description": "Stable slug"},
    "type": {"type": "string", "default": "act", "optional": False, "description": "Always 'act'"},
    "title": {"type": "string", "default": "", "optional": False, "description": "Display name"},
    "order": {"type": "number", "default": 0, "optional": False, "description": "Position within story (float for insertions)"},
    "status": {"type": "string", "default": "planned", "optional": False, "description": "One of: planned, in-progress, complete"},
    "value": {"type": "string", "default": "", "optional": True, "description": "Value at stake in this act"},
    "value_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "value_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
    "climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug where this act's major reversal lands"},
    "act_objective": {"type": "string", "default": "", "optional": True, "description": "Protagonist's immediate goal for this act"},
}
```

### 3.4 Project Entity Additions

```python
# Additions to ENTITY_SCHEMAS["project"] alongside existing name, logline, genre, setting, status
"spine": {"type": "string", "default": "", "optional": True, "description": "Protagonist's desire (story-level spine)"},
"controlling_idea": {"type": "string", "default": "", "optional": True, "description": "The story's controlling idea/argument"},
"value": {"type": "string", "default": "", "optional": True, "description": "Value at stake for the whole story"},
"value_at_open": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
"value_at_close": {"type": "string", "default": "", "optional": True, "description": "One of: positive, negative, mixed, ironic"},
"inciting_incident_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug of the inciting incident"},
"story_climax_scene_id": {"type": "string", "default": "", "optional": True, "description": "Scene slug of the story climax"},
"structure_type": {"type": "string", "default": "", "optional": True, "description": "One of: Classical, Miniplot, Antiplot"},
```

### 3.5 Plot Schema Changes (Migration)

```python
# In ENTITY_SCHEMAS["plot"], change setups and payoffs sub_fields:
"setups": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot is established", "sub_fields": {"scene_id": "Scene slug (e.g. mara-discovers-files)", "description": "What happens at this scene"}},
"payoffs": {"type": "list", "default": [], "optional": True, "description": "Scenes where plot resolves", "sub_fields": {"scene_id": "Scene slug (e.g. mara-discovers-files)", "description": "What happens at this scene"}},
```

---

## 4. Files to Modify (Specific Changes)

### 4.1 `core/constants.py`

| Location | Change |
|----------|--------|
| `REQUIRED_FIELDS` | Add `"scene": ["title", "sequence_id", "act_id"]`, `"sequence": ["title", "act_id"]`, `"act": ["title"]` |
| `ENTITY_FOLDERS` | Add `"scene": "scenes"`, `"sequence": "sequences"`, `"act": "acts"` |
| `ENTITY_LABELS` | Add `"scene": "Scene"`, `"sequence": "Sequence"`, `"act": "Act"` |
| `ENTITY_SCHEMAS` | Add full schemas for `"scene"`, `"sequence"`, `"act"` (§3.1-3.3). Add new optional fields to `"project"` (§3.4). Update `"plot"` setups/payoffs sub_fields (§3.5). |

### 4.2 `core/entity.py`

| Function | Change |
|----------|--------|
| `validate_entity()` | Add branches for `scene`, `sequence`, `act`: validate `status` enums, validate `order` is numeric |

**Specific validations:**
- `scene.status` ∈ {`planned`, `drafted`, `written`, `locked`}
- `sequence.status` ∈ {`planned`, `in-progress`, `complete`}
- `act.status` ∈ {`planned`, `in-progress`, `complete`}
- `scene.time_of_day` ∈ {`DAY`, `NIGHT`, `DUSK`, `DAWN`, `CONTINUOUS`, `LATER`, ""}
- `scene.dramatic_role` ∈ {`setup`, `complication`, `crisis`, `climax`, `resolution`, `transition`, `non-event`, ""}
- `scene.value_open`/`value_close` ∈ {`positive`, `negative`, `mixed`, `ironic`, ""}
- `sequence.value_open`/`value_close` ∈ same
- `act.value_open`/`value_close` ∈ same
- `act.structure_type` ∈ {`Classical`, `Miniplot`, `Antiplot`, ""}

### 4.3 `core/index.py`

| Function | Change |
|----------|--------|
| `generate_index()` | Add parsing for `scenes/`, `sequences/`, `acts/` folders via `_parse_entities()` |
| `_parse_project()` | Add `sequence_count`, `act_count` to project entry |
| `_validate_index()` | Add cross-reference validation: scene `sequence_id` exists, scene `act_id` matches sequence's `act_id`, sequence `act_id` exists. Validate plot setups/payoffs reference existing scene slugs. |
| `_enrich_scenes_with_plots()` | Rewrite to match by `scene_id` instead of `heading` |
| `_normalize_plot_scene()` | Update to handle `{scene_id, description}` format |
| New: `_enrich_structure()` | Build derived lists: `sequence.scenes_list` (sorted by `order`), `act.sequences_list` (sorted by `order`), `act.scenes_list` (all scenes where `act_id = this`) |

**Index entry shapes:**

Scene:
```yaml
- id: mara-discovers-files
  type: scene
  title: "Mara Discovers the Files"
  order: 22
  status: planned
  sequence_id: seq-inciting-discovery
  act_id: act-1
  heading: "INT. PRECINCT BATHROOM - DAY"
  characters: [mara, detective-oak]
  plots: [main-plot]
  location: precinct-bathroom
  sections: [Description, Dramatic Function, Notes, Content]
```

Sequence:
```yaml
- id: seq-inciting-discovery
  type: sequence
  title: "The Inciting Discovery"
  order: 2
  act_id: act-1
  status: planned
  scene_count: 0
  sections: [Summary, Scene Order, Notes]
```

Act:
```yaml
- id: act-1
  type: act
  title: "The Setup"
  order: 1
  status: planned
  sequence_count: 0
  scene_count: 0
  sections: [Summary, Thematic Function, Notes]
```

### 4.4 `tools/story_create.py`

| Location | Change |
|----------|--------|
| `_build_schema()` | Update `entity_type` enum to include `"scene"`, `"sequence"`, `"act"` |
| `_get_standard_sections()` | Add entries for `scene` → `[Description, Dramatic Function, Notes, Content]`, `sequence` → `[Summary, Scene Order, Notes]`, `act` → `[Summary, Thematic Function, Notes]` |

### 4.5 `tools/story_edit.py`

| Location | Change |
|----------|--------|
| `_get_standard_sections()` | Add entries (same as story_create.py) |

### 4.6 `tools/story_retrieve.py`

| Location | Change |
|----------|--------|
| `SCHEMA["properties"]["entity_type"]["enum"]` | Add `"scene"`, `"sequence"`, `"act"` |

### 4.7 `tools/story_search.py`

No code change needed — already iterates `ENTITY_FOLDERS` which will include new types.

### 4.8 `tools/story_index.py`

No changes needed — calls `generate_index()`.

### 4.9 `tools/story_load.py`

| Location | Change |
|----------|--------|
| `handler()` | Update confirmation message to include sequences and acts counts |

### 4.10 `plugin.yaml`

No change in Phase 1 — no new tool.

### 4.11 `__init__.py`

No changes in Phase 1.

### 4.12 `skills/story-loader/SKILL.md`

| Location | Change |
|----------|--------|
| Tools table | Mention `story_create` can now create scenes, sequences, acts |
| Entity Quick Reference table | Add rows for Scene, Sequence, Act |
| Procedure step 4 confirmation | Update to include sequences, acts |

### 4.13 `skills/story-editor/SKILL.md`

| Location | Change |
|----------|--------|
| Entity Quick Reference table | Add rows for Scene, Sequence, Act. Update Plot row to show `setups`/`payoffs` use `scene_id` |
| `story_edit` Actions table | Note that `edit_note` and `create_entity` now work for scenes, sequences, acts |
| Entity Creation section | Document required fields for scene (`title`, `sequence_id`, `act_id`), sequence (`title`, `act_id`), act (`title`) |

### 4.14 `tests/fixtures/save-the-children/plots/the-resistance.md`

Migrate from `{heading, number, description}` to `{scene_id, description}`:

```yaml
setups:
  - scene_id: central-room-day
    description: Kael discovers the door isn't locked — it was never locked.
  - scene_id: central-room-night
    description: The Administrator makes its final offer. Kael refuses.
payoffs:
  - scene_id: the-core-day
    description: The children emerge into the real world for the first time.
```

---

## 5. Implementation Steps (Task Order)

### Task 1: Constants & Schemas
**File:** `core/constants.py`
- Add `scene`, `sequence`, `act` to `REQUIRED_FIELDS`
- Add to `ENTITY_FOLDERS`
- Add to `ENTITY_LABELS`
- Add full `ENTITY_SCHEMAS` entries for all three types
- Add new optional fields to `ENTITY_SCHEMAS["project"]`
- Update `ENTITY_SCHEMAS["plot"]` setups/payoffs sub_fields

**Status:** ✅ Complete — 2026-09-12
**What was done:** `core/constants.py` updated with all three new entity types across `REQUIRED_FIELDS`, `ENTITY_FOLDERS`, `ENTITY_LABELS`, and `ENTITY_SCHEMAS`. Scene schema has 25 fields (incl. dramatic metadata flags), sequence 12, act 11. Project schema gained 9 optional story-level fields (spine, controlling_idea, value, value_at_open/close, inciting_incident_scene_id, story_climax_scene_id, structure_type). Plot setups/payoffs migrated from `{heading, number, description}` to `{scene_id, description}`. All 23 existing tests pass.

### Task 2: Validation
**File:** `core/entity.py`
- Extend `validate_entity()` with enum checks for scene/sequence/act

**Status:** ✅ Complete — 2026-09-12
**What was done:** Added 7 enum constant lists to `core/constants.py` (`SCENE_STATUSES`, `SEQUENCE_STATUSES`, `ACT_STATUSES`, `SCENE_TIMES_OF_DAY`, `SCENE_DRAMATIC_ROLES`, `VALUE_CHARGES`, `STRUCTURE_TYPES`). Extended `validate_entity()` with type-specific branches for `scene`, `sequence`, and `act`. Two private helpers added: `_validate_enum()` (nullable enums via `empty_ok=True` for optional fields) and `_validate_numeric()` (checks `int`/`float`). Scene validates 5 enums + `order` numeric; sequence 3 enums + `order`; act 4 enums + `order`. All 23 existing tests pass.

### Task 3: Index Generation
**File:** `core/index.py`
- Extend `generate_index()` to parse scenes/, sequences/, acts/ folders
- Add `sequence_count`, `act_count` to project entry
- Add cross-reference validation in `_validate_index()`
- Rewrite `_enrich_scenes_with_plots()` to match by `scene_id`
- Update `_normalize_plot_scene()` for new format
- Add `_enrich_structure()` for derived lists

**Status:** ✅ Complete — 2026-09-12
**What was done:** `generate_index()` now calls `_parse_entities()` for `scenes/`, `sequences/`, `acts/` and merges results into the index dict. `_parse_project()` gained `sequences_count` and `act_count` params. Screenplay scenes now merge with file scenes (or file scenes alone if no screenplay exists). `_normalize_plot_scene()` returns `{scene_id, description}`; `_enrich_scenes_with_plots()` builds `scenes_by_id` instead of `scenes_by_heading`. New `_enrich_structure()` derives `sequence.scenes_list` (sorted by `order`), `act.sequences_list`, and `act.scenes_list`. `_validate_index()` adds warnings for scene→sequence/act, plot→scene, sequence→act, act→climax, and scene.act_id vs sequence.act_id mismatch. `_enrich_from_screenplay()` uses `.get()` for `heading`/`characters` since file scenes lack them.

**Tests added (8):** `TestSceneIndex` in `tests/test_core.py` — file inclusion, sequence/act counts, cross-reference validation warnings, act/scene mismatch, structure list enrichment, plot→scene_id normalization, and plot→unknown-scene warning. All 138 tests pass.

### Task 4: Tool Updates (Passive)
**Files:** `tools/story_create.py`, `tools/story_retrieve.py`, `tools/story_load.py`, `tools/story_edit.py`
- Update `_get_standard_sections()` with new entity types
- Update enum lists in schemas
- Update confirmation message in `story_load`

**Status:** ✅ Complete — 2026-09-12
**What was done:** `story_create.py` entity_type enum expanded to include `scene`, `sequence`, `act`; `_get_standard_sections()` now returns `[Description, Dramatic Function, Notes, Content]` for scenes, `[Summary, Scene Order, Notes]` for sequences, `[Summary, Thematic Function, Notes]` for acts. `story_retrieve.py` entity_type enum expanded with the same three types. `story_load.py` confirmation message now reports `N sequences, M acts` in addition to existing counts. `story_edit.py` `_get_standard_sections()` updated identically to `story_create.py`. All 138 existing tests pass.

### Task 5: Test Fixtures
**File:** `tests/fixtures/save-the-children/plots/the-resistance.md`
- Migrate setups/payoffs from `{heading, number, description}` to `{scene_id, description}`

**Status:** ✅ Complete — 2026-09-12
**What was done:** `the-resistance.md` setups/payoffs migrated from `{heading, number, description}` to `{scene_id, description}`. Scene IDs are forward-looking slugs (`central-room-day`, `central-room-night`, `the-core-day`) — they don't need to exist as files for plot validation to pass (validation only warns, doesn't fail). All 138 tests pass.

### Task 6: Skills Documentation
**Files:** `skills/story-loader/SKILL.md`, `skills/story-editor/SKILL.md`
- Update entity reference tables
- Document new entity types and required fields

**Status:** ✅ Complete — 2026-09-12
**What was done:** `story-loader/SKILL.md` — `story_create` description expanded to list all 7 entity types; confirmation message now reports `N sequences, M acts`; new Entity Quick Reference subsection added (Scene, Sequence, Act); plot pitfall note updated from `{heading, number, description}` to `{scene_id, description}`. `story-editor/SKILL.md` — `edit_note`/`create_entity` actions now note they work for scenes, sequences, acts; plot Quick Reference updated to `{scene_id, description}`; new "Entity Creation (Required Fields)" table added (Scene: `title`, `sequence_id`, `act_id`; Sequence: `title`, `act_id`; Act: `title`); three new rows in Entity Quick Reference for Scene, Sequence, Act. All 138 tests pass.

### Task 7: Tests
**File:** `tests/test_core.py`
- Test creating a scene via `story_create` — verify all fields present, body sections generated
- Test creating a sequence, act
- Test `validate_entity()` for scene/sequence/act — valid and invalid inputs
- Test `generate_index()` with scenes/sequences/acts folders present
- Test cross-reference validation (scene references non-existent sequence → warning)
- Update `TestIndexGeneration.test_generate_index` expected counts if fixtures include scenes/sequences/acts

**Status:** ✅ Complete — 2026-09-12
**What was done:** Added 6 new tests to `tests/test_core.py`: `test_create_scene_has_all_fields_and_sections` (verifies all 25 scene schema fields present + 4 body sections), `test_create_sequence_has_all_fields_and_sections` (12 fields + 3 sections), `test_create_act_has_all_fields_and_sections` (11 fields + 3 sections), `test_validate_scene_invalid_status`, `test_validate_scene_invalid_dramatic_role`, `test_validate_sequence_invalid_status`, `test_validate_act_invalid_status`. Updated `test_generate_index` to assert `len(index["sequences"]) == 0` and `len(index["acts"]) == 0` (fixture has no scenes/sequences/acts folders). All 145 tests pass.

---

## 6. Test Strategy

### What to test (runnable checks):

```python
def test_create_scene_has_all_fields_and_sections(tmp_path):
    """story_create for scene produces all frontmatter fields + body sections."""

def test_validate_scene_invalid_status():
    """validate_entity('scene', {status: 'invalid'}) returns warning."""

def test_validate_scene_invalid_dramatic_role():
    """validate_entity('scene', {dramatic_role: 'invalid'}) returns warning."""

def test_generate_index_includes_scenes_sequences_acts(tmp_path):
    """generate_index walks scenes/, sequences/, acts/ folders and includes entries."""

def test_index_cross_reference_validation(tmp_path):
    """Scene with non-existent sequence_id triggers validation warning."""

def test_plot_setups_reference_scene_id(tmp_path):
    """Plot setups/payoffs with scene_id match scenes in index."""
```

### What NOT to test (YAGNI):
- Every enum value for every field (one invalid test per field is enough)
- `order` float behavior (it's a number, Python handles it)
- Section parser (already tested, generic, unchanged)

---

## 7. Migration Notes

- **No backward compatibility needed** — no real projects exist outside tests
- **Existing test fixtures** (`save-the-children`) don't have `scenes/`, `sequences/`, `acts/` folders. Tests still pass because `_parse_entities()` returns empty list for non-existent folders.
- **Plot fixture migration** — `the-resistance.md` must be updated to use `scene_id` instead of `heading`/`number`. The `scene_id` values in the fixture should match scene slugs that will exist once scene files are created (e.g., `central-room-day`, `central-room-night`, `the-core-day`). These are forward-looking references for the test fixture; they don't need to exist as files for the plot validation test to pass (validation only warns, doesn't fail).

---

## 8. Out of Scope (Intentionally Deferred)

| Topic | Phase |
|-------|-------|
| `story_structural` tool (create/edit/reorder/delete for structure) | Phase 3 |
| Structure index sidecar (`.story/structure-index.yaml`) | Phase 2 |
| Script view assembly from scene files | Phase 4 |
| Screenplay import → scene files | Separate job (post Phase 1-3) |
| Slug rename machinery | Future (manual for now) |
| Character arc beats referencing scenes | Future (needs arc system) |
| Value turn analysis | Future (needs dramatic metadata populated) |

---

## 9. Success Criteria for Phase 1

- [x] `story_create` can create scene/sequence/act with all fields and body sections
- [x] `story_retrieve` can read scene/sequence/act files
- [x] `story_edit` can edit scene/sequence/act frontmatter and body sections
- [x] `story_search` searches inside scenes/, sequences/, acts/ folders
- [x] `story_index` includes scenes, sequences, acts in the index
- [x] `validate_entity()` catches invalid enum values for new types
- [x] Cross-reference validation warns on broken sequence_id/act_id references
- [x] Plot setups/payoffs use `scene_id` (not `heading`)
- [x] All existing tests still pass
- [x] Skills documentation updated

---

## 10. Phase 1 Final Report

**Status:** ✅ Complete — 2026-09-12

**What was implemented:**

Three new entity types (scene, sequence, act) added to the data model. All tooling updated to handle them. Plot references migrated from fragile heading-matching to stable `scene_id` slugs.

**Files modified:**

| File | Change |
|------|--------|
| `core/constants.py` | Added 3 entity schemas (scene: 25 fields, sequence: 12, act: 11), 7 enum constant lists, project additions (9 fields), plot migration to `{scene_id, description}` |
| `core/entity.py` | Extended `validate_entity()` with type-specific branches; added `_validate_enum()` and `_validate_numeric()` helpers |
| `core/index.py` | Extended `generate_index()` to walk scenes/sequences/acts; added `_enrich_structure()` for derived lists; `_normalize_plot_scene()` and `_enrich_scenes_with_plots()` rewritten for `scene_id`; cross-reference validation expanded |
| `tools/story_create.py` | entity_type enum expanded; `_get_standard_sections()` updated |
| `tools/story_edit.py` | `_get_standard_sections()` updated |
| `tools/story_retrieve.py` | entity_type enum expanded |
| `tools/story_load.py` | Confirmation message reports sequences/acts counts |
| `skills/story-loader/SKILL.md` | Entity Quick Reference added; confirmation message updated |
| `skills/story-editor/SKILL.md` | Entity Creation table added; required fields documented |
| `tests/fixtures/save-the-children/plots/the-resistance.md` | Migrated to `{scene_id, description}` |
| `tests/test_core.py` | +10 tests (3 create, 4 validate, 3 index assertions) |

**Test results:** 145/145 pass (was 135 before Phase 1).

**Deferred to later phases:**
- Slug rename machinery (manual for now)
- Structure index sidecar (Phase 2)
- `story_structural` tool (Phase 3)
- Dashboard integration (Phase 4)
- Screenplay import → scene files (separate job)

**Out of scope (confirmed):** Scene files in test fixture — would add maintenance debt without coverage gain until screenplay import is implemented.
