# Task 0.1: Pre-Refactor Baseline Verification

## Goal
Confirm current behavior before making changes. Establish a green baseline.

## Steps

### 0.1.1: Verify fixture characters use `## Relationships` body sections
- **File**: `tests/fixtures/save-the-children/characters/*.md`
- **Assert**: Each character file has a `## Relationships` (or `## Relationship`) section in the body
- **Current state**: `kael.md` has `## Relationships` with Mira and The Administrator entries — CONFIRMED

### 0.1.2: Verify `test_character_has_rel` asserts `char.rel` with `id` + `label`
- **File**: `tests/test_phase2_db_reads.py:181-189`
- **Current state**: Test iterates `if "rel" in char` — may be vacuous if no `character_relationship` relations exist in fixture
- **Note**: Fixture characters use body sections, NOT `relationships:` frontmatter. The `char_rels` dict in `db.py:177` is built from `character_relationship` relations, which may be empty.

### 0.1.3: Verify `test_field_coverage` generates `relationships` for characters
- **File**: `tests/test_field_coverage.py:52-53`
- **Current state**: `_sample_value("relationships", meta)` returns `[{"id": "mira", "label": "Friend", "feeling": "Trust"}]`
- **Note**: This creates structured frontmatter that becomes `character_relationship` relations via `relations_for_insert`

### 0.1.4: Run full test suite
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -m pytest tests/ -x -q
```
- **Expected**: All tests pass (baseline green)

## Checklist
- [x] Fixture characters have `## Relationships` body sections
- [x] `test_character_has_rel` reviewed and noted for update
- [x] `test_field_coverage` relationship sampling noted for update
- [x] Full test suite passes (baseline green)

## Notes
- Verification only, except one baseline fix: export now round-trips `variant_of` (see Final Brief 0.1.4)
- The old relationship system uses `character_relationship` relations + `char_rels`/`rel` fields on characters
- The new system will use `relationship` entities + computed `relationships` field on characters

## Final Brief (completed)

### 0.1.1 — Fixture `## Relationships` sections: CONFIRMED
All 6 character files (`kael`, `mira`, `the-administrator`, `the-outsider`, `marcus-chen`, `dr-elena-voss`) have a `## Relationships` body section at line ~31-37. No character uses `relationships:` frontmatter — verified by grep across the whole fixture. Body sections are prose only; they never become `character_relationship` relations.

### 0.1.2 — `test_character_has_rel` is VACUOUS: CONFIRMED
`tests/test_phase2_db_reads.py:181-189` iterates `if "rel" in char` — but since no fixture character has `relationships:` frontmatter, `char_rels` (db.py:177) stays empty, `rel: []` is stripped by `_omit` (db.py:381), and the loop body never executes. The test passes without testing anything. Rewrite target for Phase 5.2.

### 0.1.3 — `test_field_coverage` relationship sampling: CONFIRMED
`tests/test_field_coverage.py:52-53` — `_sample_value("relationships")` returns `[{id, label, feeling}]`, exercising the `character.relationships` schema field (constants.py:52) → `character_relationship` relation via `relations_for_insert` (entity.py:146, 246-250). Will need update when `relationships` becomes computed (Phase 1.2/5.2).

### 0.1.4 — Baseline was NOT green; now fixed
`test_round_trip_preserves_data` and `test_world_variant_of_round_trip` failed: import converts `variant_of` FM → `world_variant`/`location_variant` relation (story_import.py:308-321), but export never denormalized it back — a task_22 leftover (its IMPLEMENTATION_PLAN.md:56-59 specified this step but it was never implemented).

**Fix applied** (`tools/story_export.py:83-90`): `_export_all` now fetches the `location_variant`/`world_variant` relation and writes `variant_of` back into extra before FM generation — mirroring the existing character/plot denormalization pattern. Covers both locations and worlds.

**Result**: 275/275 tests pass. Baseline green.
