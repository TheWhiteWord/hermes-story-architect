# Task 1: Fix `relationships` Round-Trip Corruption

## Goal
Fix the data corruption when character relationships are imported → stored in DB → read back for dashboard. Currently the label text is lost and replaced by the target character's name.

## The Bug
- **Import** (`core/entity.py:relations_for_insert`): `{id, label, feeling}` → note = `"{label} — {feeling}"` (single string)
- **Denormalizer** (`core/db.py:get_dashboard_data`): reads `label = t["name"]` (target character name), `feeling = note` — **label text is lost**
- **Export** (`tools/story_export.py`): does NOT reconstruct `relationships` from `character_relationship` relations at all

## Spec (from `dev` branch)
Old system stored `relationships` as `[{id, label, feeling}]` dicts in frontmatter. The dashboard reads `char.relationships` as a list of `{id, label, feeling}` objects.

## Files to Touch
1. `core/entity.py` — `relations_for_insert()` (character_relationship branch)
2. `core/db.py` — `get_dashboard_data()` (character denormalization)
3. `tools/story_export.py` — `_export_all()` (add character_relationship export)

## Implementation

### 1. `core/entity.py` — Store structured data in note field
Change the note format from `"{label} — {feeling}"` to JSON:
```python
import json
# ...
note = json.dumps({"label": label, "feeling": feeling})
```

### 2. `core/db.py` — Parse structured note in denormalizer
In the character denormalization loop, parse the note as JSON:
```python
for rel in rel_map.get(eid, {}).get("character_relationship", []):
    target_id = rel.get("to_id", "") if isinstance(rel, dict) else rel
    if target_id in entity_by_id:
        t = entity_by_id[target_id]
        # Parse structured note
        note = rel.get("note", "") if isinstance(rel, dict) else ""
        try:
            parsed = json.loads(note) if note else {}
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        rels.append({
            "id": t["id"],
            "label": parsed.get("label", ""),
            "feeling": parsed.get("feeling", ""),
        })
```

### 3. `tools/story_export.py` — Reconstruct relationships
Add character_relationship handling in `_export_all()`:
```python
if entity_type == "character":
    rels = conn.execute(
        "SELECT to_id, note FROM relations WHERE from_id=? AND kind='character_relationship'",
        (entity_id,)
    ).fetchall()
    if rels:
        relationships = []
        for to_id, note in rels:
            try:
                parsed = json.loads(note) if note else {}
            except (json.JSONDecodeError, TypeError):
                parsed = {}
            relationships.append({
                "id": to_id,
                "label": parsed.get("label", ""),
                "feeling": parsed.get("feeling", ""),
            })
        extra["relationships"] = relationships
```

## Verification (against old dashboard from `dev` branch)
- [ ] Import a project with character relationships
- [ ] Check DB: `SELECT note FROM relations WHERE kind='character_relationship'` — should be JSON `{"label": "...", "feeling": "..."}`
- [ ] Open **old dashboard** (`git show dev:src/dashboard/story-dashboard.html`): character panel at line ~2601 reads `rel.label` and `rel.feeling` — must show correct label text (not target character name)
- [ ] Export and re-import: relationships should survive round-trip intact
- [ ] Verify old dashboard normalization at line ~1927 (`c.related = c.relationships.map(...)`) still works — both `relationships` and `related` paths must populate

## Deferred Issues
None.

## Good Practice
- No `old_`, `_legacy`, `_bak` names
- No historical-reference comments
- No dead code left behind
