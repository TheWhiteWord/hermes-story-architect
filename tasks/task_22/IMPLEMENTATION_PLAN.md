# Task: World & Location Refinement — Implementation Plan

Source: `tasks/task_22/FINAL_PLAN.md` (design). This plan defines code phases.

**Scope:** Add FM fields to world/location, model location→world containment via parent_id, model variant_of via relations tree, propagate through import/export/load/dashboard/create/edit, update fixtures + tests.

---

## Phase 1 — Schema & Constants

**Goal:** All new fields discoverable from ENTITY_SCHEMAS; column/relation maps updated.

| File | Change |
|---|---|
| `core/constants.py` | **World** — add `period` (string), `values` (list), `power` (list), `variant_of` (string). **Location** — add `mood` (string), `dramatic_function` (string), `world` (string), `variant_of` (string). |
| `core/entity.py` | `ENTITY_COLUMN_MAP["location"]`: add `"world": "parent_id"`. `_RELATION_FIELDS`: add `"location": {"variant_of": ("location_variant", False)}`, `"world": {"variant_of": ("world_variant", False)}`. Implement non-list branch in `relations_for_insert`: `to_id = str(value)`, single relation row. |
| `core/entity.py` | `standard_sections()`: location → `[Description, Atmosphere, Image System, History, Dramatic Function]`; world → `[Description, History, Livelihood, Power, Rituals, Values, Conflict]`. |
| `tools/story_edit.py` | `_ENTITY_COLUMN_MAP`: same location.world → parent_id. `_get_standard_sections()`: same new section lists. |
| `tools/story_create.py` | `_get_standard_sections()`: same new section lists. |

**Notes:**
- `variant_of` uses kind `location_variant` / `world_variant` with `is_list=False`. Star topology: single pointer, no symmetric lists.
- `world` (location) maps to `parent_id` column — same containment as scene→sequence. No new column, no migration.
- `variant_of` is a string slug in FM, stored as a single relation row (not a list).
- World `rules` stays in extra (already there). World `values`/`power` stay in extra (list type). All new location/world FM fields that aren't column-mapped go to extra JSON automatically.

---

## Phase 2 — Import Path (`story_import.py`)

**Goal:** Markdown vault → DB correctly maps all new fields.

| Location | Change |
|---|---|
| `_columns_for("location", ...)` | `"parent_id": fm.get("world")` — world slug becomes parent_id. |
| `_columns_for("world", ...)` | unchanged (no parent; variant_of is a relation). |
| `_extra_for("location", fm)` | skip set stays `{name, one_sentence, id}` — new fields (mood, dramatic_function, variant_of) flow to extra automatically. But `world` must be removed from extra (it's parent_id) — add `"world"` to skip set. |
| `_extra_for("world", fm)` | add `"variant_of"` to skip set (handled as relation). `period`, `values`, `power`, `rules` flow to extra. |
| `_insert_relations(conn, "location", slug, fm)` | after existing logic: if `fm.get("variant_of")`, insert `relation(slug, fm["variant_of"], "location_variant")`. |
| `_insert_relations(conn, "world", slug, fm)` | if `fm.get("variant_of")`, insert `relation(slug, fm["variant_of"], "world_variant")`. |

**Notes:**
- Import already handles `relations` for character and `setups/crisis/climax/payoffs` for plot. variant_of follows the same INSERT OR IGNORE pattern.
- No DB schema change — parent_id and relations tables already exist.

---

## Phase 3 — Export Path (`story_export.py`)

**Goal:** DB → Markdown vault round-trips all new fields.

| Location | Change |
|---|---|
| `_frontmatter_for("location", ...)` | Start with `name`, `one_sentence`. Merge `extra` at top level (mood, dramatic_function come from extra). Add `world` from `parent_id` if set. Add `variant_of` from relations query (query relations where from_id=entity_id AND kind='location_variant'). |
| `_frontmatter_for("world", ...)` | Start with `name`, `one_sentence`. Merge `extra` (rules, period, values, power all there). Add `variant_of` from relations query (kind='world_variant'). |
| `_export_all()` | After fetching rows, batch-fetch variant_of relations once (for both location and world), build a lookup map. |

**Notes:**
- `_export_all` already batch-fetches scene characters and character relationships. Add a single query for `location_variant` + `world_variant` relations.
- The `extra` merge must come AFTER explicit fields so explicit fields (like world from parent_id) don't get overwritten by stale extra data.

---

## Phase 4 — Load Path (`db.py get_project_summary`)

**Goal:** story_load returns new fields for world/location, world→location tree.

| Location | Change |
|---|---|
| `_build_location(loc_id)` | Return dict already has id/name/one_sentence. Add: `mood`, `dramatic_function` (from extra), `world` (from parent_id), `variant_of` (from relations lookup — build `variant_of` map in the rel loop). |
| `_build_world(world_id)` | Return dict: add `period`, `values`, `power` (from extra), `rules` (from extra), `variant_of` (from relations lookup). |
| `get_project_summary()` | Build a `loc_world` map: location_slug → world_slug (from parent_id). Build `world_locations` map: world_slug → [location_slug, ...]. Include `worlds_list` as flat (existing), but each world now carries its FM fields. Locations stay flat under top-level `locations` (the world→location tree is derivable from `world` field on each location). |

**Notes:**
- Existing code builds `locations_list` and `worlds_list` as flat arrays. Keep that shape — the containment is encoded by `location.world` pointing to a world slug, mirroring how `scene.sequence_id` points to a sequence.
- variant_of: build a dict `{from_id: to_id}` while iterating rel_rows. Both _build_location and _build_world consult it.
- FM fields stored in extra are accessible via `json.loads(extra_json)` — same pattern as scene's `dramatic_role`.

---

## Phase 5 — Dashboard

**Goal:** Dashboard renders world→location containment, new FM fields, variant badges.

| Location | Change |
|---|---|
| `db.py get_dashboard_data()` | Already merges extra at top level via `_entity_dict()`. No change needed for new FM fields — they flow automatically. Add `locations` world→location tree: for each location, if `parent_id` is set and points to a world, attach `world_id` field. **Also:** fetch `location_variant` + `world_variant` relations, attach `variant_of` to location/world dicts (not automatic — relations are not merged by `_entity_dict`). |
| `src/dashboard/story-dashboard.html` (JS) | **Worlds view**: render `period`, `values`, `power` as tags/sections in the world card. **Locations view**: group by world (show world name as section header), show `mood` + `dramatic_function` on the card. **Variant badge**: if `variant_of` is set, show a small "variant of X" link/label. |
| `src/dashboard/story-dashboard.html` (CSS) | `.tag-mood`, `.tag-dramatic-function`, `.variant-badge` — minimal styling matching existing `.tag-location` pattern. |

**Notes:**
- Dashboard gets data via `get_dashboard_data()` → `__STORY_DATA__`. Since extra fields are merged at top level, JS can read `world.period`, `world.values`, `location.mood` directly.
- World→location tree: JS can derive from `location.parent_id` matching `world.id`. No need to pre-build nested arrays.
- World `rules` are already rendered (CSS `.world-rule` exists). Just ensure the JS passes them through.

---

## Phase 6 — Create/Edit

**Goal:** story_create and story_edit handle new fields.

| Location | Change |
|---|---|
| `tools/story_create.py` | Uses `ENTITY_SCHEMAS` for merged defaults + `columns_for_insert` / `relations_for_insert` from `core.entity`. Both already updated in Phase 1. `_get_standard_sections` updated. **No additional changes needed** — flows through automatically. |
| `tools/story_edit.py` | Uses `_ENTITY_COLUMN_MAP` (updated Phase 1) + `_get_standard_sections` (updated). For variant_of edit: it's in `_RELATION_FIELDS` with `is_list=False`. The edit handler's relation logic currently only handles plot beat fields (setups/crisis/etc.). Need to add generic handling: if a field is in `_RELATION_FIELDS[entity_type]` and `is_list=False`, delete old relation + insert new single row. |

**Notes:**
- story_edit's relation handling is currently hardcoded to plot fields (`plot_rel_fields`). Refactor to iterate `_RELATION_FIELDS[entity_type]` generically, dispatching on `is_list`.
- `story_edit` already handles arbitrary extra fields via the `else: extra_updates[key] = value` branch — mood, dramatic_function, period, values, power all flow there automatically.

---

## Phase 7 — Fixtures & Tests

**Goal:** Existing tests pass; new tests cover variant round-trip + world→location tree.

| Location | Change |
|---|---|
| `tests/fixtures/save-the-children/worlds/the-i.md` | Add `period: +400y after the collapse`, sample `values`, `power` entries. New sections: `## Livelihood`, `## Power`, `## Rituals`, `## Values`. Keep `rules` if present. |
| `tests/fixtures/save-the-children/worlds/the-real-world.md` | Add same fields + sections. |
| `tests/fixtures/save-the-children/locations/the-central-room.md` | Add `world: the-i`, `mood: oppressive stillness`, `dramatic_function: where the children's hope is tested`. New sections: `## Atmosphere`, `## Image System`, `## Dramatic Function`. |
| `tests/fixtures/save-the-children/locations/the-garden.md` | Add `world: the-i`, `mood: fragile peace`, `dramatic_function: Kael's emotional anchor`. Same new sections. |
| `tests/test_round_trip.py` | Add `test_location_world_round_trip`: create location with world field → import → export → assert location.md has `world: the-i` frontmatter. Add `test_world_variant_field`: world with variant_of → relation round-trips. |
| `tests/test_phase2_db_reads.py` | Extend `TestNestedStructure`: assert `location` dict in load output has `world`, `mood`, `dramatic_function`. Assert `world` dict has `period`, `values`, `power`. |
| `tests/test_core.py` | Update `test_extract_world` if assertions on sections are strict (they're not — it just checks name + sections key). No change needed unless fixture section names break existing assertions (they don't). |

**Notes:**
- Fixture changes: keep existing content, just add new FM fields + new sections. Tests that parse specific sections (like round-trip) use the section list from `standard_sections()`, so adding sections is additive.
- If any test asserts exact section count or names for location/world, update it. Currently no such assertion exists (test_core's `test_extract_world` only checks name + sections key presence).

---

## Open Decisions (pick at implementation time)

1. **`world` on location: required or optional?** Plan says optional. Decision: **optional** — existing locations without a world still valid. `parent_id` stays null.
2. **`variant_of` as string in FM vs single-item list?** FM is single string (per FINAL_PLAN). Relation row stores `to_id` = that string. Export writes it back as string. Round-trips cleanly.
3. **World→location tree representation in load output:** Flat locations array with `world` field on each, OR nested `worlds[].locations[]`? Decision: **flat with `world` field** — matches existing pattern (flat `locations` + flat `worlds`), containment derivable. Smaller diff, consistent with `scene.sequence_id` approach.

---

## Dependency Order

```
Phase 1 (schema) → Phase 2 (import) → Phase 3 (export) → Phase 4 (load)
                                              ↓
                              Phase 5 (dashboard) ← Phase 6 (create/edit)
                                              ↓
                              Phase 7 (fixtures & tests)
```

Phases 2 and 6 are independent (both depend only on Phase 1). Phase 5 depends on Phase 4 (load data shapes) but can be developed in parallel if Phase 4's output contract is agreed first.
