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
- [ ] Fixture characters have `## Relationships` body sections
- [ ] `test_character_has_rel` reviewed and noted for update
- [ ] `test_field_coverage` relationship sampling noted for update
- [ ] Full test suite passes (baseline green)

## Notes
- No implementation changes in this phase — verification only
- The old relationship system uses `character_relationship` relations + `char_rels`/`rel` fields on characters
- The new system will use `relationship` entities + computed `relationships` field on characters
