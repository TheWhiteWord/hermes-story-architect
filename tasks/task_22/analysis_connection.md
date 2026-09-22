# Phase C — World ↔ Location Connection Brainstorm

## The concept
"A location belongs to a world." One world, many locations.

## Existing patterns in the codebase (reuse first)
1. **`parent_id` column** — scene→sequence, sequence→act, arc_beat→character.
   Single-parent containment. This IS the belongs-to pattern already in the DB.
2. **`relations` table** (`from_id, to_id, kind, note, order`) — used for
   character_scene, plot_setup/crisis/climax/payoff, character_relationship.
   Multi-relations with kind + note.
3. **`scene.location` FM field** → `location_id` column — loose single link.

## Options for location→world

### Option 1: `world` FM field on location → `parent_id` column
```yaml
# location FM
world: verona   # → entities.parent_id
```
- Reuses the existing containment pattern exactly (scene does this with sequence_id).
- Zero new machinery: ENTITY_COLUMN_MAP gains `"world": "parent_id"` for location.
- Export/import already handle parent_id generically.
- Single-world assumption baked in (fine until Phase D says otherwise).

### Option 2: relations row (`kind='location_world'`)
- More flexible (multi-world), but no current need.
- Requires new kind registration, export/import handling, relation field map.
- More machinery for the same one-parent result.

### Option 3: world holds `locations` list (world→locations direction)
- Inverts ownership; world FM grows a list that must be kept in sync with
  location edits. Worse.

## What the connection enables (derived, not stored)
- story_load: world node with its locations as children (tree already renders
  parent_id children — scenes under sequences prove it).
- Location retrieve: world context comes free via parent_id.
- No `Scenes`/`Locations` sections needed anywhere — the tree IS the list.

## Phase A/B reframe check
- World sections (Description, History, Livelihood, Power, Rituals, Values,
  Conflict) — unaffected. Good.
- Location sections — unaffected.
- No new sections needed for the connection itself. The "belongs to" is
  structural, not prose.

## Discovery-mechanism constraint (traced 2026-09-22)
The fuzzy location matcher is `core/screenplay.py: match_location(heading, locations)`:
exact → substring → rapidfuzz token_set_ratio ≥ 40. It matches **by name only**
(uses just `id` and `name` from the locations list). Currently dormant — consumed
only by tests; planned for the future "import entities from .fountain" feature.
Live scene→location is a direct slug (scene.location → location_id), no fuzzy.
Dashboard `_parse_scene_location` parses headings for stats, never matches entities.

- Phase C impact: **none** — `world`→parent_id touches neither id nor name. ✅
- **HARD CONSTRAINT for Phase D: location variants must keep distinct display
  names** (e.g. "Kitchen (Dream)"), or name-based fuzzy matching becomes
  ambiguous (extractOne picks arbitrarily among same-name entities).
  Alternatively the matcher gains a world/variant scope argument — more machinery,
  avoid unless needed.

## LOCKED (user decisions)
- Option 1 confirmed: `world` FM field on location → `parent_id` column.
- Fuzzy matcher audited, unaffected by Phase C; constraint recorded for Phase D.

## Phase C result (locked)
```yaml
# location FM (lean, after Phase C)
name:
one_sentence:
mood:    # (revised from motif — see analysis_location.md)
world:    # world slug this location belongs to (optional for now — D may revisit)
```
- Mapping: ENTITY_COLUMN_MAP["location"]["world"] = "parent_id".
- Derived lists only: story_load tree renders world → locations via parent_id.
  No stored Locations/Scenes lists anywhere.
- Rejected: relations-table kind (machinery for unused multi-world), world-owned
  list (sync burden, inverted ownership).
