# Task 3.2: Read Paths — story_dashboard

## Goal
Update `story_dashboard` to expose relationship entities and richer character relationship summaries.

## Steps

### 3.2.1: Build relationship entities in dashboard data
- **File**: `core/db.py`
- **Location**: `get_dashboard_data()`, in the entity loop (around lines 672-820)
- **Action**: Add `relationship` entity handling:
```python
elif etype == "relationship":
    d = _entity_dict({
        "id": eid, "name": e[2], "one_sentence": e[3], "order": e[4],
        "status": e[5], "parent_id": e[6], "extra": extra,
    })
    d["characters"] = extra.get("characters", [])
    d["perspectives"] = extra.get("perspectives", {})
    d["scenes"] = extra.get("scenes", [])
    d["history"] = extra.get("history", "")
    relationships.append(d)
```
- **Note**: Must initialize `relationships = []` before the loop

### 3.2.2: Build richer computed character relationship summary for dashboard
- **File**: `core/db.py`
- **Location**: In `get_dashboard_data()`, after the entity loop
- **Action**: Add (richer than load — includes `strength`):
```python
# Computed summary on characters for dashboard (richer than load)
char_rel_summary = {}
for rel in relationships:
    for char_id in rel["characters"]:
        other_id = [c for c in rel["characters"] if c != char_id][0]
        p = rel["perspectives"].get(char_id, {})
        char_rel_summary.setdefault(char_id, []).append({
            "with": other_id,
            "label": p.get("label", ""),
            "type": p.get("type", ""),
            "strength": p.get("strength", 0),
        })
```

### 3.2.3: Add `relationships` to character output in dashboard
- **File**: `core/db.py`
- **Location**: In the character branch of `get_dashboard_data()` (around lines 677-711)
- **Action**: Add after the existing `d["relationships"] = rels` line:
```python
d["relationships"] = char_rel_summary.get(eid, [])  # Computed summary (richer)
```

### 3.2.4: Add `relationships` to dashboard story_data
- **File**: `core/db.py`
- **Location**: `story_data` dict in `get_dashboard_data()` (around lines 982-993)
- **Action**: Add:
```python
story_data = {
    # ... existing fields ...
    "relationships": relationships,
}
```

## Verification
```bash
cd /media/theww/AI/Projects/Plugins/Hermes/hermes-story-architect
python -c "from core.db import get_dashboard_data; print('OK')"
```

## Checklist
- [ ] Relationship entities built in dashboard data
- [ ] Richer computed character relationship summary (with `strength`)
- [ ] `relationships` field added to character output
- [ ] `relationships` array in `story_data`
- [ ] Import check passes
