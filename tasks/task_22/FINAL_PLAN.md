# Task 22 — Final Plan: Location & World Refinement

Status: **DESIGN COMPLETE — not yet implemented.** No code changed.
Phases A–D analysis in this folder; this document is the implementation spec.

---

## 1. World entity

### Frontmatter (lean — decisions only)
| Field | Type | Req | Description |
|---|---|---|---|
| `name` | string | yes | World display name |
| `one_sentence` | string | yes | One-sentence summary for index label |
| `rules` | list | no | World rules (audience contract). Each entry a string. *(existing)* |
| `period` | string | no | **NEW.** When this world exists (e.g. "2040s", "+400y after the collapse"). Distinguishes world versions. |
| `values` | list | no | **NEW.** Short entries of what this world holds sacred/moral (e.g. "truth is sacred", "debt outlives the debtor"). Permeates every scene. |
| `power` | list | no | **NEW.** Short entries of who holds power and how (e.g. "the Church sanctions all tech", "water barons rule the coast"). Source of extra-personal antagonism. |
| `variant_of` | string | no | **NEW.** Slug of the base world this is a version of. Empty on base worlds. |

### Sections (verbose — writer prompts)
Replace `[Description, History, Conflict]` with:
`[Description, History, Livelihood, Power, Rituals, Values, Conflict]`

McKee's pre-inciting-incident world questions become sections (Livelihood,
Power, Rituals, Values), not FM fields — they are prompts for the writer, not
queryable data. `Power` and `Values` sections expand their FM counterparts
(FM = short gist entries; section = full reasoning, exceptions, tensions).

## 2. Location entity

### Frontmatter (lean)
| Field | Type | Req | Description |
|---|---|---|---|
| `name` | string | yes | Location display name |
| `one_sentence` | string | yes | One-sentence summary for index label |
| `mood` | string | no | **NEW.** Emotional register of the place, generalized (e.g. "oppressive domesticity") — NOT specific imagery; specifics live in the Image System section. |
| `dramatic_function` | string | no | **NEW.** Why this place exists in the story, short (e.g. "where the protagonist's past catches up"). Permeates every scene set here. |
| `world` | string | no | **NEW.** World slug this location belongs to. |
| `variant_of` | string | no | **NEW.** Slug of the base location this is a variant of. Empty on base locations. |

### Sections (verbose)
Replace `[Description, History, Scenes]` with:
`[Description, Atmosphere, Image System, History, Dramatic Function]`

- Description — what the camera sees (sensory surface)
- Atmosphere — expands `mood`: sensory palette, how the register is felt
- Image System — recurring images/sounds associated with this place; material
  to draw from, NOT requirements (see design rule below)
- History — backstory of the place
- Dramatic Function — expands `dramatic_function`: full reasoning, what
  pressure it exerts, scene-usage notes
- `Scenes` **dropped** — redundant with scene→location relation (derived list)

**Design rule (LLM constraint risk):** FM = constraints + permeating context
(needed in EVERY scene; absent it, the LLM defaults wrongly and doesn't know to
ask). Sections = expansions + situational material (needed when the moment
calls — the moment itself prompts retrieval). A specific image ("the oak
table") in FM would be treated by an LLM as an absolute constraint imposed on
every scene. Generalized mood in FM, specific imagery in the Image System
section — LLMs treat section prose as palette, not mandate.

**FM-summary test** (applied — do not re-litigate without new evidence):
a section earns an FM counterpart only if BOTH hold:
1. Needed at FM-only access time (index/pick, or scene-writing context), not
   just at drill-down time.
2. Treating the summary as a constraint is harmless or correct (permeation is
   the field's job — values, power, dramatic_function pass; rituals fail:
   they're insertable material, the motif lesson).
Passed: world `values`, world `power`, location `dramatic_function`.
Failed: rituals (material), livelihood (folds into power), history summaries
(`period` covers the "when"), Image System (motif lesson).

## 3. Connection: location belongs to world

- `world` FM field on location → **`entities.parent_id`** column
  (same containment pattern as scene→sequence, sequence→act).
- One-line mapping in `ENTITY_COLUMN_MAP["location"]`.
- No stored lists in either direction — story_load tree derives
  world → locations via parent_id.

## 4. Variants (time/space special cases)

**Model: variants are separate entities + one identity link.**

```yaml
# base                                 # variant
name: Kitchen                          name: Kitchen (Dream)
world: reality-world                   world: dream-world
mood: oppressive domesticity           mood: oppressive domesticity, unmoored
                                       variant_of: kitchen
```

- `variant_of` → **relations table** via existing `_RELATION_FIELDS` machinery
  (template: `character_relationship`). Kinds: `location_variant`, `world_variant`.
- **Star topology:** single pointer to base. No chains, no symmetric lists.
  Reverse lookup gathers the family.
- **Orthogonal links:** `world` = containment (where it lives);
  `variant_of` = identity (same place/world as). Both can be set.
- **Base-holds-core convention:** base location/world holds the common,
  enduring facts; variant holds only the deltas + its own mood/atmosphere
  charge. Retrieve base + variants in one story_retrieve batch to see core
  once, deltas per variant.
- World versions: `period` states WHEN, `variant_of` states SAME-AS-WHAT.

### Conventions (naming — enforced by docs, not code)
1. Variant display names MUST be distinct: "Kitchen (Dream)",
   "Earth (400 Years Later)". Keeps name-based fuzzy matching unambiguous.
2. Base = the reality/original. Every variant points at the base.
3. `variant_of` stays empty on bases.

## 5. Implementation checklist (when we code)

1. `core/constants.py` — ENTITY_SCHEMAS: add `period`, `values`, `power`,
   `variant_of` to world; add `mood`, `dramatic_function`, `world`,
   `variant_of` to location. Update REQUIRED_FIELDS only
   if we decide `world` required (currently: optional — see open points).
2. `core/entity.py`:
   - `ENTITY_COLUMN_MAP["location"]["world"] = "parent_id"`
   - `_RELATION_FIELDS`: location/world gain `variant_of` (kind
     `location_variant`/`world_variant`, not a list — single string field;
     needs the non-list branch currently `pass`ed in relations extraction, or
     store as single-item list).
   - `standard_sections()`: new section lists for location + world.
3. `tools/story_edit.py` — `_SECTION_MAP` (line ~367) + column map (~48):
   same updates.
4. `tools/story_export.py` — `_frontmatter_for`: location emits
   name/one_sentence/mood/dramatic_function/variant_of (+ world from
   parent_id); world emits name/one_sentence/rules/period/values/power/
   variant_of.
5. `tools/story_import.py` / `story_create.py` — sections lists
   (`_get_standard_sections`) updated to match.
6. Tests — existing suites keep passing; add coverage for variant round-trip
   (create → export → import) and world→location tree in story_load.
7. Skill doc (`hermes-story-architect` SKILL.md) — conventions section:
   variant naming, base-holds-core, world vs variant_of semantics.

## 6. Constraints & audit notes
- Fuzzy matcher (`core/screenplay.py: match_location`) matches by name only;
  dormant (future .fountain import). Distinct variant names keep it safe.
  `variant_of` is a future disambiguation hook — do NOT design now.
- Dashboard `_parse_scene_location` parses headings for stats only — unaffected.
- No DB migration: parent_id and relations table already exist.

## 7. Open points (decided at implementation time)
- `world` on location: optional (current decision). Revisit if variant
  entities make it structural.
- `variant_of` as string vs single-item list in `_RELATION_FIELDS` — pick
  whichever fits the existing extraction code with the smaller diff.
- `mood` stays free text, no enum (no — validation).

## 8. Rejected alternatives (for the record)
- `motif` (specific imagery) as location FM field — LLM constraint risk: FM
  reads as absolute constraint; specific images/sounds would be forced into
  every scene. Generalized `mood` in FM, imagery in Image System section.
- `rituals`/`livelihood` as world FM fields — situational/insertable material;
  the motif lesson applies (LLM would force rituals into every scene).
  Livelihood folds into `power`. Sections carry them.
- History summaries as FM — `period` covers the "when"; the rest is
  drill-down material.
- `reality_mode` enum on world — linked variants already express "this world
  has layers".
- relations-kind for world containment — parent_id does it with zero machinery.
- World-owned locations list — sync burden, inverted ownership.
- Symmetric variants lists / chains — sync burden / needless complexity.
- Shared-aspect field machinery — base-holds-core convention covers it.
- genre / level_of_conflict on world FM — duplicates project.genre and
  scene.conflict_levels.
