# Phase 1 — Backend: add `values` to the dashboard payload

## Goal

`core/db.py:get_dashboard_data` must emit a top-level `values` list in `story_data` so the graph can place a word on a lane.

## What to change

**File**: `core/db.py`, function `get_dashboard_data` (starts line 967).

### 1.1 — Add a `value` branch in the entity loop (around line 1064)

The loop at line 1064 iterates `ent_rows` and builds per-type arrays. There is no `value` branch. Add one:

```python
values = []
# ... alongside characters, scenes, locations, plots, worlds, acts, sequences, arcs, relationships

for e in ent_rows:
    etype = e[1]
    eid = e[0]
    extra = json.loads(e[8]) if e[8] else {}

    # ... existing branches ...

    elif etype == "value":
        values.append({
            "id": eid,
            "name": e[2],
            "p": extra.get("p", ""),
            "c": extra.get("c", ""),
            "cd": extra.get("cd", ""),
            "nn": extra.get("nn", ""),
            "note": extra.get("note", ""),
        })
```

Notes:
- `name` is the `name` column (`e[2]`), NOT from `extra`. The slug is derived from it.
- `p`, `c`, `cd`, `nn` live in the `extra` JSON (confirmed: `core/constants.py:303-316`).
- `note` is optional — default `""`.

### 1.2 — Add `"values"` to `story_data` (line 1388)

```python
story_data = {
    "project": {**proj_dict, "value_focus": story_focus},
    "characters": characters,
    "scenes": scenes,
    "locations": locations,
    "plots": [...],
    "worlds": worlds,
    "acts": [...],
    "sequences": [...],
    "arcs": story_arcs,
    "relationships": relationships,
    "story_memory": story_memory,
    "values": values,          # <-- NEW
}
```

## Checklist

- [x] `values` list built in the entity loop
- [x] Each entry has `id`, `name`, `p`, `c`, `cd`, `nn`, `note`
- [x] `"values"` key added to `story_data` dict
- [x] Existing test suite passes: `.venv/bin/pytest tests/ -x -q` (1157 tests)

## Final Brief

All three changes applied to `core/db.py`:

1. **`values = []` list initialized** at line 1063 (alongside the other entity lists).
2. **`elif etype == "value"` branch** added at line 1210 (after the `relationship` branch). Each entry contains `id`, `name` (from the `name` column `e[2]`), and `p`, `c`, `cd`, `nn`, `note` from the `extra` JSON — matching the schema at `core/constants.py:303-316`.
3. **`"values": values`** added to `story_data` dict at line 1412.

Test suite: 1157 passed, 0 failures.
