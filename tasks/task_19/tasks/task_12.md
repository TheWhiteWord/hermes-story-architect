# Task 12: Fix `unfilled_fields` to Check Column Data for Scene/Sequence/Plot

## Goal
Fix `unfilled_fields()` to check `status` column for entities that store it there (scene, sequence, plot, act). Currently it only checks `extra`, so status fields in DB columns always show as "unfilled" even when set.

## The Problem
`core/entity.py:unfilled_fields(entity_type, extra)` only checks the `extra` dict. But for scene/sequence/plot, `status` is stored in a DB column, not extra. So `unfilled_fields` always reports status as "unfilled" for these types.

**Verify before editing:** check if `unfilled_fields` receives column data or just extra.

Current call in `core/db.py:get_project_summary()` (line ~130-132):
```python
for row in entities["rows"]:
    unfilled_map[row[0]] = unfilled_fields(row[1], row[8])
```

It passes `row[8]` which is `extra`. Does it also have access to `row[5]` (status)?

Yes — the row has all entity columns. But `unfilled_fields` only takes `extra`.

## Fix Options

### Option A: Pass status column to unfilled_fields
Change signature to accept optional column data:
```python
def unfilled_fields(entity_type: str, extra: dict, columns: dict = None) -> list[str]:
```

Then for scene/sequence/plot: check `columns.get("status")` if field is in column map.

### Option B: Merge column data into extra before calling
In `get_project_summary`, merge status into extra before calling:
```python
for row in entities["rows"]:
    merged_extra = dict(json.loads(row[8]) if row[8] else {})
    if row[1] in ("scene", "sequence", "plot", "act") and row[5]:
        merged_extra["status"] = row[5]
    unfilled_map[row[0]] = unfilled_fields(row[1], merged_extra)
```

**Option B is simpler** — no signature change.

## Implementation

In `get_project_summary()`, change lines ~130-132:
```python
for row in entities["rows"]:
    entity_type = row[1]
    extra = json.loads(row[8]) if row[8] else {}
    # Merge column data for fields stored outside extra
    if entity_type in ("scene", "sequence", "plot", "act") and row[5]:
        extra = {**extra, "status": row[5]}
    unfilled_map[row[0]] = unfilled_fields(entity_type, extra)
```

Also need to fix `get_dashboard_data()` if it calls `unfilled_fields` too — check and apply same pattern.

## Files
- `core/db.py` — `get_project_summary()` and `get_dashboard_data()` (if applicable)

## Verification
- [ ] Import a project with scenes that have status set (e.g., "drafted")
- [ ] Check `unfilled` map in `get_project_summary` output: scene status must not be in unfilled list when set
- [ ] Edit scene to remove status — should reappear in unfilled list

## Deferred Issues
None.
