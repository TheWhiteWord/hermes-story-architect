# Task 5.1: Fixture & Test Updates

## Goal
Update test fixtures and test files to work with the new relationship entity system.

## Context
The old system stores relationships as frontmatter lists on character files. The new system stores them as separate `relationship` entity files in a `relationships/` folder. Tests need to reflect this.

## Steps

### 5.1.1: Create relationship fixture files
- **Action**: Create `tests/fixtures/save-the-children/relationships/` directory with relationship files derived from character `## Relationship` sections
- **Files to create**:
  - `relationships/kael-mira.md` — Kael & Mira relationship
  - `relationships/kael-the-administrator.md` — Kael & The Administrator relationship
  - `relationships/mira-the-administrator.md` — Mira & The Administrator relationship (if exists in fixture)
- **Frontmatter template**:
```yaml
---
name: "Kael & Mira"
characters: ["kael", "mira"]
perspectives:
  kael:
    label: "Closest friend"
    feeling: "Trusts her feelings more than their own logic"
    type: "family"
    strength: 0.9
  mira:
    label: "Friend, anchor"
    feeling: "Understands his silences"
    type: "romantic"
    strength: 0.7
    secret: true
scenes: ["central-room-day", "central-room-night"]
status: "active"
---

## Description

## History

## Dynamics

## Scenes

## Notes
```
- **Note**: Check actual character files in fixture to derive relationship data

### 5.1.2: Update `test_character_has_rel` in `test_phase2_db_reads.py`
- **File**: `tests/test_phase2_db_reads.py`
- **Location**: Lines 181-189
- **Current state**: Asserts `char.rel` with `id` + `label`
- **Action**: Replace with assertion on `char.relationships` computed summary:
```python
def test_character_has_rel(self, db_project):
    """character.relationships populated from relationship entities."""
    proj, vault = db_project
    result = json.loads(load_handler({"project": str(proj), "vault_path": vault}))
    for char in result["characters"]:
        if "relationships" in char:
            for rel in char["relationships"]:
                assert "with" in rel
                assert "label" in rel
                assert "type" in rel
```
- **Note**: `relationships` is now a computed field with `with`/`label`/`type` (not `id`/`label`)

### 5.1.3: Update `test_field_coverage.py`
- **File**: `tests/test_field_coverage.py`
- **Location**: Lines 52-53, the `_sample_value` function
- **Action**: Remove the `relationships` sample for character:
```python
# REMOVE:
if field == "relationships":
    return [{"id": "mira", "label": "Friend", "feeling": "Trust"}]
```
- **Action**: The `_sample_frontmatter` function (lines 68-76) will naturally skip computed fields since they're marked `computed: True` — verify this works
- **Action**: The `test_create_load_retrieve` test (line 168) parametrizes over all entity types — `relationship` will be included automatically once added to `ENTITY_SCHEMAS`

### 5.1.4: Update `test_round_trip.py`
- **File**: `tests/test_round_trip.py`
- **Action**: Add relationship round-trip test:
```python
def test_relationship_round_trip(fixture_path):
    """Relationship entities survive import → export → re-import."""
    # Import → export → verify relationships/ folder has files
    # Re-import → verify relationship entities in DB
```
- **Note**: The existing `test_import_creates_schema_and_entities` test should verify entity count includes relationships

### 5.1.5: Update `test_core.py` if it references relationships
- **File**: `tests/test_core.py`
- **Action**: Check for any relationship-related assertions and update if needed

### 5.1.6: Add `test_dashboard_relationships` in `test_phase2_db_reads.py`
- **Action**: Add test verifying relationship data in dashboard:
```python
def test_dashboard_has_relationships(self, db_project):
    """Dashboard includes relationship entities."""
    proj, vault = db_project
    result = json.loads(dashboard_handler({
        "project": str(proj),
        "vault_path": vault
    }))
    assert result["success"] is True
    html = Path(result["dashboard_url"].replace("file://", "")).read_text()
    # Check that __STORY_DATA__ contains relationships
    assert "relationships" in html
```

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -m pytest tests/ -x -q
```

## Cleanup Checklist
- [ ] Relationship fixture files created from character `## Relationship` sections
- [ ] `test_character_has_rel` updated to assert computed `relationships` field
- [ ] `test_field_coverage` updated — `relationships` removed from character samples
- [ ] `test_round_trip` includes relationship round-trip
- [ ] `test_core` reviewed and updated
- [ ] `test_dashboard_relationships` added
- [ ] Full test suite passes

## Notes
- The fixture `save-the-children` currently has NO `relationships/` folder — it must be created
- The fixture characters have `## Relationship` body sections (prose), NOT structured frontmatter
- The new system uses both: `## Relationships` body section (prose) + `relationship` entity files (structured data)
- Tests should verify both the computed summary (from entities) and the body section content
