# Task 13: Decide Arc ID Format (Breaking Change — DISCUSS WITH USER)

## Goal
Decide whether to keep the composite arc ID format (`"kael-1"`) from the new system or revert to the simple format (`"1"`) from the `dev` branch. This is a breaking change that affects all existing data.

## The Change
- **Old (`dev` branch)**: beat slug = `"1"`, `"2"`, `"3"` — unique within character folder
- **New (`sqlite-migration`)**: entity_id = `"kael-1"`, `"kael-2"` — composite (char_slug + beat_id)

## Current State
- Import (`tools/story_import.py:148`): `slug = f"{char_slug}-{beat_id}"`
- Export (`tools/story_export.py:90`): `beat_id = entity_id[len(parent_id)+1:]` — strips prefix to recover original
- Dashboard: **does not read beat ID directly** — uses `ab.character` + `ab.label` only

## Impact Analysis

### Composite ID (current)
- ✅ Self-documenting (character visible in ID)
- ✅ Globally unique (no collision across characters)
- ❌ Breaks any external reference to beat IDs (frontmatter cross-references, story structure notes)
- ❌ Longer IDs in dashboard JSON
- ❌ User-facing IDs less clean

### Simple ID (old system)
- ✅ Matches `dev` branch storage contract
- ✅ Shorter, cleaner IDs
- ✅ No migration needed for existing arc files
- ❌ Requires character context to identify beat
- ❌ Folder structure still provides uniqueness

## What the Dashboard Actually Reads
The old dashboard reads from `arc_beats_list`:
- `b.label` (display name)
- `b.shift` (value shift)
- `b.y` (value charge)
- `b.order` (sort order)
- `b.id` (fallback label only: `b.label || b.id`)

From `scene.arc_beats`:
- `ab.character` (character ID)
- `ab.label` (beat label)

**Neither reads `beat_id` as a critical field.** The ID is only used as a fallback display label.

## Migration Path
If reverting to simple IDs:
1. Update `tools/story_import.py` to use simple beat_id as entity_id
2. Update `tools/story_export.py` to use simple beat_id (remove prefix stripping)
3. Re-import all projects (or write migration script to rename existing entities + relations)

## Decision Needed
**Ask the user which format to use.** Both work for the dashboard. The composite format is safer for DB uniqueness; the simple format matches the original contract.

## Verification
- [ ] After decision: arc IDs in dashboard JSON match chosen format
- [ ] Export → re-import preserves arc IDs correctly
- [ ] Arc visualization works (character arc chart, scene arc dots)

## Deferred Issues
- **If keeping composite:** document that beat IDs are `char-slug` prefixed
- **If reverting:** plan migration for existing DB data
