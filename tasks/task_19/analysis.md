
# Field-by-Field Audit: `dev` → `sqlite-migration`

## Audit Overview & Methodology

This audit is a field-level comparison of two branches of the `hermes-story-architect` plugin's story storage systems.

**`dev`** is the pre-refactor branch — the **original design** that works correctly. It comprises:
- Markdown+frontmatter note-based storage
- A Python "index generator" (`core/index.py`) that builds a `.story/index.yaml` derived view
- `core/constants.py` — the canonical field schema (`ENTITY_SCHEMAS`, `REQUIRED_FIELDS`)
- `tools/story_index.py` — triggers the index generator (which becomes the dashboard's data)

**`sqlite-migration`** is the **new implementation being evaluated** — the refactor that ended up replacing the original. It comprises:
- A SQLite database (`.story/story.db`) with `entities`, `relations`, and `sections` tables
- A column/relation mapping layer (`core/entity.py` → `ENTITY_COLUMN_MAP`, `_RELATION_FIELDS`)
- An import pipeline (`tools/story_import.py`) that reads markdown → writes to SQLite
- A dashboard query layer (`core/db.py` → `get_dashboard_data()`) that derives the shapes the frontend reads

The storage contract of the original: frontmatter columns + relation lists → parsed → enriched → rendered, with several important **derived fields** (cross-references, reverse lookups, counters) computed at query time inside the index generator. E.g., dashboard UI depends heavily on fields like `sequence.scenes_list`, `scene.arc_beats`, `project.plot_count` that are never *stored* in frontmatter — they are computed at read time from other entities and relations.

The refactor replaced all that code with a SQLite layer and a single `core/db.py` denormalizer that emits these derived fields. The denormalizer's output was then compared against the original to detect regressions.

**What was read to perform this audit:**

- `git show dev:core/index.py` — the original enrichment pipeline: `_enrich_characters_with_arcs()`, `_enrich_scenes_with_arcs()`, `_enrich_structure()`, `_enrich_scenes_with_plots()`, `_enrich_sequences_with_plots()`, `_enrich_acts_with_plots()`, `compute_structural_stats()`, `_parse_project()`
- `git show dev:core/constants.py` — `ENTITY_SCHEMAS` and `REQUIRED_FIELDS` — the canonical field definitions
- `git show dev:tools/story_index.py` — entry point into the original index generator
- `git show dev:tools/story_create.py`, `tools/story_edit.py` — CRUD operations for the original
- `core/entity.py`, `core/db.py` — the new SQLite mapper + denormalizer
- `tools/story_import.py`, `tools/story_export.py` — write/read pipelines
- `tools/story_load.py`, `tools/story_dashboard.py` — consumers of the derived data
- `src/dashboard/story-dashboard.html` — the upstream consumer that reads these fields as JavaScript globals (`__STORY_DATA__`, `__STRUCTURAL_STATS__`, etc.)

**Rules of comparison:**

1. **Stored fields** — must be found in both branches under the same name, same value, and same type.
2. **Derived fields** — match only if the computation logic, input data, and output shape are the same. A field present in both branches is still a bug if the value differs at runtime.
3. **Relation fields** — a relation listed in the old branch must have the same source, target, and cardinality in the new.
4. **Dashboard-facing fields** — anything read by the dashboard HTML/JS must exist on the new branch with the same name and compatible type.

**Statuses:**

Meaning
✓ Match — same semantics, same storage, same derivation
⚠ Semantic mismatch — field exists but behaves differently in a way that breaks behavior
✗ Missing — field is present in `dev` but entirely absent from the new branch
🔀 Storage reshuffle — same data, different location, same value (no behavior change)

Field Legend

| Marker | Meaning |
|--------|---------|
| ✓ | Match — same semantics, same storage, same derivation |
| ⚠ | Semantic mismatch — field exists but behaves differently |
| ✗ | Missing — field exists in old system, absent in new |
| 🔀 | Storage reshuffle — same data, different location (but correct) |

---

## character

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `name` | FM `name` | entities.name | — | — | ✓ |
| `one_sentence` | FM `one_sentence` | entities.one_sentence | — | — | ✓ |
| `story_role` | FM `story_role` | entities.extra | — | — | ✓ |
| `relationships` | FM `relationships[]` | relations.character_relationship | — | — | ⚠ |
| `goals_short` | FM `goals_short` | entities.extra | — | — | ✓ |
| `goals_long` | FM `goals_long` | entities.extra | — | — | ✓ |
| `knowledge` | FM `knowledge[]` | entities.extra | — | — | ✓ |
| `arc_type` | FM `arc_type` | entities.extra | — | — | ✓ |
| `arc_value` | FM `arc_value` | entities.extra | — | — | ✓ |
| `arc_value_at_open` | FM `arc_value_at_open` | entities.extra | — | — | ✓ |
| `arc_value_at_close` | FM `arc_value_at_close` | entities.extra | — | — | ✓ |
| `arc_complete` | FM `arc_complete` | entities.extra | — | — | ✓ |
| `scenes` | — | — | Reverse: scene Frontmatter `characters[]` contains char.id → list of `{id, title, heading}` objects | Reverse: `character_scene` relations where to_id=char → list of `{to_id, note}` dicts | ⚠ |
| `arc_beats_list` | — | — | Built from `index["arcs"]` where beat.character == char.id → list of `{id, label, scene, shift, y, order, is_crisis, is_climax}` | Grouped from arcs array by `character` or `parent_id` → list of arc entity dicts | ⚠ |
| `arc_beat_count` | — | — | `len(arc_beats_list)` | `len(arc_beats_list)` | ✓ |

**Issues:**

- **`relationships`**: Old: frontmatter had full `{id, label, feeling}` dicts. New: relation note is `"{label} — {feeling}"` single string; on read-back, `feeling` = note, `label` = target character's ID (not the label text). **Data corruption on round-trip**. The label text is lost; the target character's name (from entity lookup) is used as label instead.
- **`scenes`**: Old shape: `[{id, title, heading}]` objects. New shape: `[{to_id, note}]` dicts (from `character_scene` relation rows). Dashboard normalizer handles both but the shape is incompatible — `_scene_objs` (old format which carried heading info) is lost.
- **`arc_beats_list`**: Old: lean objects `{id, label, scene, shift, y, order, is_crisis, is_climax}` extracted specifically for the dashboard. New: full arc entity dicts with all extra fields merged — bloated, different field set.

---

## location

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `name` | FM `name` | entities.name | — | — | ✓ |
| `one_sentence` | FM `one_sentence` | entities.one_sentence | — | — | ✓ |
| `scenes` | — | — | Reverse: scene Frontmatter `location` == loc.id → `[{id, title, heading}]` | Reverse: `location_scene` relations → list of scene IDs | ⚠ |

**Issues:**

- **`scenes`**: Same shape mismatch as character.scenes. Old: `[{id, title, heading}]`. New: `[scene_id_strings]`. Heading info lost.

---

## world

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `name` | FM `name` | entities.name | — | — | ✓ |
| `one_sentence` | FM `one_sentence` | entities.one_sentence | — | — | ✓ |
| `rules` | FM `rules[]` | entities.extra | — | — | ✓ |

**Issues:** None.

---

## plot

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `name` | FM `name` | entities.name | — | — | ✓ |
| `one_sentence` | FM `one_sentence` | entities.one_sentence | — | — | ✓ |
| `plot_type` | FM `plot_type` | entities.extra | — | — | ✓ |
| `plot_scope` | FM `plot_scope` | entities.extra | — | — | ✓ |
| `value_arc` | FM `value_arc` | entities.extra | — | — | ✓ |
| `status` | FM `status` | entities.status | — | — | 🔀 |
| `characters` | FM `characters[]` | entities.extra | — | — | ✓ |
| `setups` | FM `setups[{scene_id, description}]` | relations.plot_setup | — | — | ⚠ |
| `payoffs` | FM `payoffs[{scene_id, description}]` | relations.plot_payoff | — | — | ⚠ |
| `crisis` | — | — | NOT stored in old system | relations.plot_crisis | ⚠ |
| `climax` | — | — | NOT stored in old system | relations.plot_climax | ⚠ |

**Issues:**

- **`setups`/`payoffs`**: Old: frontmatter list of `{scene_id, description}`. New: relation rows with `note` = description. On read-back, `_normalize_beats()` converts relation dicts to `{scene_id, description}`, but the `description` field comes from `note` populated from `beat.get("description", "")`. If old data had descriptions stored differently, they'd be lost.
- **`crisis`/`climax`**: Old: these fields did NOT exist in the `ENTITY_SCHEMAS["plot"]` or the old frontmatter. They were not parsed by `_parse_entities()` or `_enrich_plots()`. New: they ARE imported as `plot_crisis`/`plot_climax` relations. This is a **new field addition** — either it was added to schemas between branches, or it's an unintended addition.

---

## scene

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `type` | FM `type` = "scene" | entities.type = "scene" | — | — | ✓ |
| `title` | FM `title` | entities.name | — | — | 🔀 |
| `order` | FM `order` | entities.order_key | — | — | 🔀 |
| `status` | FM `status` | entities.status | — | — | 🔀 |
| `heading` | FM `heading` | entities.extra | — | — | ✓ |
| `location` | FM `location` | entities.location_id | — | — | 🔀 |
| `time_of_day` | FM `time_of_day` | entities.extra | — | — | ✓ |
| `sequence_id` | FM `sequence_id` | entities.parent_id | — | — | 🔀 |
| `act_id` | FM `act_id` | entities.extra | — | — | 🔀 |
| `characters` | FM `characters[]` | relations.character_scene | — | — | ⚠ |
| `value` | FM `value` | entities.extra | — | — | ✓ |
| `value_open` | FM `value_open` | entities.extra | — | — | ✓ |
| `value_close` | FM `value_close` | entities.extra | — | — | ✓ |
| `conflict_levels` | FM `conflict_levels[]` | entities.extra | — | — | ✓ |
| `dramatic_role` | FM `dramatic_role` | entities.extra | — | — | ✓ |
| `is_inciting_incident` | FM `is_inciting_incident` | entities.extra | — | — | ✓ |
| `is_sequence_climax` | FM `is_sequence_climax` | entities.extra | — | — | ✓ |
| `is_act_climax` | FM `is_act_climax` | entities.extra | — | — | ✓ |
| `is_story_climax` | FM `is_story_climax` | entities.extra | — | — | ✓ |
| `locations` | — | — | NOT derived in old system | Reverse: `location_scene` relations → list of loc IDs | ⚠ |
| `plots` | — | — | Reverse: scan all plots' setups/payoffs crisis/climax for scene.id → `[{id, beat}]` | Reverse: `plot_setup`/`plot_payoff` relations → list of plot IDs (strings) | ⚠ |
| `arc_beats` | — | — | Reverse: scan all arcs where beat.scene == scene.id → `[{character, beat_id, label, y, is_crisis, is_climax}]` | NOT DERIVED | ✗ |

**Issues:**

- **`characters`**: Old: frontmatter list `["char1", "char2"]`. New: relation-based. On read-back, `char_ids` is built from reverse lookup of `character_scene` relations where `to_id` = scene.id. **This reverse lookup iterates ALL relations of ALL entities** — O(n) scan. The old system used `scene.characters` directly from frontmatter (O(1)). Performance regression.
- **`plots`**: Old: `[{id, beat}]` where beat ∈ {setup, crisis, climax, payoff}. New: `[plot_id_strings]`. The beat info is lost.
- **`arc_beats`**: **MISSING entirely.** Old: `_enrich_scenes_with_arcs()` built `scene.arc_beats[]`. New: no equivalent derivation in `get_dashboard_data()`. Dashboard reads `scene.arc_beats` at line 3864 and `s.arc_beats` at line 2272 — both will be undefined.
- **`act_id`**: Old: frontmatter `act_id` field. New: stored in `extra` (since `ENTITY_COLUMN_MAP["scene"]` doesn't map `act_id`). Dashboard reads `s.act_id` in several places (lines 3762–3772) — this will now come from extra. ✓ (works, but storage reshuffled)

---

## sequence

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `type` | FM `type` = "sequence" | entities.type | — | — | ✓ |
| `title` | FM `title` | entities.name | — | — | 🔀 |
| `order` | FM `order` | entities.order_key | — | — | 🔀 |
| `status` | FM `status` | entities.status | — | — | 🔀 |
| `act_id` | FM `act_id` | entities.parent_id | — | — | 🔀 |
| `value` | FM `value` | entities.extra | — | — | ✓ |
| `value_open` | FM `value_open` | entities.extra | — | — | ✓ |
| `value_close` | FM `value_close` | entities.extra | — | — | ✓ |
| `climax_scene_id` | FM `climax_scene_id` | entities.extra | — | — | ✓ |
| `primary_plot` | FM `primary_plot` | entities.extra | — | — | ✓ |
| `purpose` | FM `purpose` | entities.extra | — | — | ✓ |
| `scenes_list` | — | — | Reverse: scenes where sequence_id == seq.id → `[scene_id]` sorted by order | **NOT DERIVED** | ✗ |
| `scene_count` | — | — | `len(scenes_list)` | **NOT DERIVED** | ✗ |
| `plots` | — | — | Aggregate from scene.plots → `{id, has_setup, has_crisis, has_climax, has_payoff, plot_scope, plot_type, value_arc}` | **NOT DERIVED** | ✗ |

**Issues:**

- **`scenes_list`**: **MISSING.** Dashboard reads `seq.scenes_list` at line 2922. Always undefined → sequence panel shows no scenes.
- **`scene_count`**: **MISSING.** Dashboard falls back to `seq.scene_count || 0`. Shows 0.
- **`plots`**: **MISSING.** Dashboard reads `seq.plots` at line 2932. Always undefined.

---

## act

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id | — | — | ✓ |
| `type` | FM `type` = "act" | entities.type | — | — | ✓ |
| `title` | FM `title` | entities.name | — | — | 🔀 |
| `order` | FM `order` | entities.order_key | — | — | 🔀 |
| `status` | FM `status` | entities.status | — | — | 🔀 |
| `value` | FM `value` | entities.extra | — | — | ✓ |
| `value_open` | FM `value_open` | entities.extra | — | — | ✓ |
| `value_close` | FM `value_close` | entities.extra | — | — | ✓ |
| `climax_scene_id` | FM `climax_scene_id` | entities.extra | — | — | ✓ |
| `act_objective` | FM `act_objective` | entities.extra | — | — | ✓ |
| `sequences_list` | — | — | Reverse: sequences where act_id == act.id → `[seq_id]` sorted by order | **NOT DERIVED** | ✗ |
| `scenes_list` | — | — | Reverse: scenes where act_id == act.id → `[scene_id]` sorted by order | **NOT DERIVED** | ✗ |
| `sequence_count` | — | — | `len(sequences_list)` | **NOT DERIVED** | ✗ |
| `scene_count` | — | — | `len(scenes_list)` | **NOT DERIVED** | ✗ |
| `plots` | — | — | Aggregate from scene.plots (same as sequence) | **NOT DERIVED** | ✗ |

**Issues:** Same pattern as sequence — all reverse-derived structure fields missing.

---

## arc

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `id` | FM (note stem) | entities.id = `"{char_slug}-{beat_id}"` | — | — | ⚠ |
| `character` | FM `character` | entities.parent_id + extra | — | — | 🔀 |
| `scene` | FM `scene` | entities.extra | — | — | ✓ |
| `order` | FM `order` | entities.order_key | — | — | 🔀 |
| `label` | FM `label` | entities.name | — | — | 🔀 |
| `action` | FM `action` | entities.extra | — | — | ✓ |
| `gap` | FM `gap` | entities.extra | — | — | ✓ |
| `choice` | FM `choice` | entities.extra | — | — | ✓ |
| `shift` | FM `shift` | entities.extra | — | — | ✓ |
| `y` | FM `y` | entities.extra | — | — | ✓ |
| `is_crisis` | FM `is_crisis` | entities.extra | — | — | ✓ |
| `is_climax` | FM `is_climax` | entities.extra | — | — | ✓ |

**Issues:**

- **`id`**: Old: simple beat slug (e.g., `"1"`, `"2"`). New: composite `"char_slug-beat_slug"` (e.g., `"kael-1"`). Breaks any code relying on entity ID format. The export code derives `beat_id = entity_id[len(parent_id)+1:]` which correctly strips the prefix, but any external reference to beat IDs (e.g., in frontmatter cross-references) would need updating.

---

## project

| Field | Old Storage | New Storage | Old Derivation | New Derivation | Status |
|-------|-------------|-------------|----------------|----------------|--------|
| `name` | FM `name` | entities.name | — | — | ✓ |
| `logline` | FM `logline` | entities.one_sentence | — | — | 🔀 |
| `genre` | FM `genre` | entities.extra | — | — | ✓ |
| `setting` | FM `setting` | entities.extra | — | — | ✓ |
| `status` | FM `status` | entities.extra | — | — | ✓ |
| `screenplay_title` | FM `screenplay_title` | entities.extra | — | — | ✓ |
| `credit` | FM `credit` | entities.extra | — | — | ✓ |
| `author` | FM `author` | entities.extra | — | — | ✓ |
| `contact` | FM `contact` | entities.extra | — | — | ✓ |
| `draft_date` | FM `draft_date` | entities.extra | — | — | ✓ |
| `draft` | FM `draft` | entities.extra | — | — | ✓ |
| `spine` | FM `spine` | entities.extra | — | — | ✓ |
| `controlling_idea` | FM `controlling_idea` | entities.extra | — | — | ✓ |
| `value` | FM `value` | entities.extra | — | — | ✓ |
| `value_at_open` | FM `value_at_open` | entities.extra | — | — | ✓ |
| `value_at_close` | FM `value_at_close` | entities.extra | — | — | ✓ |
| `inciting_incident_scene_id` | FM `inciting_incident_scene_id` | entities.extra | — | — | ✓ |
| `story_climax_scene_id` | FM `story_climax_scene_id` | entities.extra | — | — | ✓ |
| `structure_type` | FM `structure_type` | entities.extra | — | — | ✓ |
| `scene_count` | — | — | `len(scenes)` | **NOT DERIVED** | ✗ |
| `character_count` | — | — | `len(characters)` | **NOT DERIVED** | ✗ |
| `location_count` | — | — | `len(locations)` | **NOT DERIVED** | ✗ |
| `world_count` | — | — | `len(worlds)` | **NOT DERIVED** | ✗ |
| `plot_count` | — | — | `len(plots)` | **NOT DERIVED** | ✗ |
| `sequence_count` | — | — | `len(sequences)` | **NOT DERIVED** | ✗ |
| `act_count` | — | — | `max(declared, len(acts))` | **NOT DERIVED** | ✗ |
| `arc_count` | — | — | `len(arcs)` | **NOT DERIVED** | ✗ |

**Issues:**

- All count fields missing. Dashboard falls back to computing from array lengths, so display is OK, but any consumer reading `project.scene_count` directly (without fallback) breaks.
- **`act_count`**: Old had special logic: `max(declared, len(acts))` — the user could declare 3 acts even if only 2 exist yet. New: no such logic.

---

## structural_stats

| Field | Old Derivation | New Derivation | Status |
|-------|----------------|----------------|--------|
| `sceneCount` | `len(scenes)` | `SUM(status_counts)` | ⚠ |
| `sequenceCount` | `len(sequences)` | `COUNT(*) WHERE type='sequence'` | ✓ |
| `actCount` | `len(acts)` | `COUNT(*) WHERE type='act'` | ✓ |
| `sceneStatus` | Counter of `scene.status` | `GROUP BY status` | ✓ |
| `sceneRoles` | Counter of `scene.dramatic_role` or `"unset"` | Same | ✓ |
| `plotCoverage` | Computed from scene.plots reverse-lookup → `[{id, name, plot_scope, plot_type, value_arc, sceneCount, coveragePct}]` | **`[]`** | ✗ |
| `acts` | `[{id, title, sceneCount, sequenceCount}]` | `[{id, title, sceneCount, sequenceCount}]` | ✓ |

**Issues:**

- **`plotCoverage`**: **EMPTY ARRAY.** Old: `compute_structural_stats()` built full coverage data. New: hardcoded `[]`. Dashboard chart at line 3425 reads `ss.plotCoverage || []` → always empty.
- **`sceneCount`**: Old: `len(scenes)`. New: `sum(scene_status.values())`. If any scene has a status NOT in the status enum (e.g., empty string), it would be counted in old but potentially not in new — actually it would be counted in new too since `GROUP BY status` captures all statuses. ✓ (semantically equivalent)

---

## Cross-Cutting Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| **Arc ID format change** | 🔴 High | `1` → `kael-1`. Breaks any external references to beat IDs. |
| **Relationships round-trip corruption** | 🔴 High | Original `{id, label, feeling}` → relation note `"label — feeling"` → read-back `{id: target_name, label: target_name, feeling: note}`. Label text replaced by target character name. |
| **All structure derived fields missing** | 🔴 High | `scenes_list`, `sequences_list`, `scenes_list` (act), `scene_count`, `sequence_count`, `plots` (on sequence/act) — all absent. Dashboard panels for sequences and acts are non-functional. |
| **`scene.arc_beats` missing** | 🔴 High | `_enrich_scenes_with_arcs()` has no equivalent. Arc visualization on scenes broken. |
| **`plotCoverage` empty** | 🔴 High | Plot coverage chart permanently empty. |
| **Character/location scenes shape change** | 🟡 Medium | `[{id, title, heading}]` → `[id_strings]`. Dashboard handles both, but `_scene_objs` path is deadcode with new data. |
| **`scene.plots` loses beat info** | 🟡 Medium | Old: `[{id, beat}]`. New: `[plot_id_strings]`. Dashboard beat labels in scene panel blank. |
| **`unfilled_fields` can't see column data** | 🟡 Medium | For scene/sequence/plot, `status` is in a column but `unfilled_fields()` only checks extra. Always reports status as "unfilled" even when set. |
| **Performance: character_scene reverse lookup** | 🟡 Medium | O(n) scan over all relations to find characters per scene. Old system: O(1) from frontmatter. |
| **Arc `scenes_list` / `sequences_list` / `scenes_list` on act missing** | 🔴 High | Without these, the sequence and act panels in the dashboard cannot render their child lists. |

---

## Summary of Missing Derived Fields (must be implemented)

These are fields that existed in the old system but are **completely absent** in `get_dashboard_data()`:

1. `scene.arc_beats[]` — reverse from arc entities
2. `sequence.scenes_list[]` — scenes where sequence_id = seq.id, sorted by order
3. `sequence.scene_count` — len(scenes_list)
4. `sequence.plots[]` — aggregated from scene.plots
5. `act.sequences_list[]` — sequences where act_id = act.id, sorted by order
6. `act.scenes_list[]` — scenes where act_id = act.id, sorted by order
7. `act.sequence_count` — len(sequences_list)
8. `act.scene_count` — len(scenes_list)
9. `act.plots[]` — aggregated from scene.plots
10. `project.scene_count` through `project.arc_count` — 8 count fields
11. `structural_stats.plotCoverage[]` — per-plot scene coverage stats
12. `scene.plots[]` — must include beat info (`{id, beat}` not just `id`)