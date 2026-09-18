# Task 2: Fix `arc_beats_list` Shape

## Goal
Make `character.arc_beats_list` match the `dev` branch output shape: lean objects with exactly the fields the dashboard reads, not bloated entity dicts.

## The Problem
Current `core/db.py:get_dashboard_data()` attaches full arc entity dicts (all extra fields merged at top level) to `character.arc_beats_list`. The old system produced lean objects.

## Spec (from `dev` branch `_enrich_characters_with_arcs`)
```python
char_beats[char_id].append({
    "id": beat.get("id", ""),
    "label": beat.get("label", ""),
    "scene": beat.get("scene", ""),
    "shift": beat.get("shift", ""),
    "y": beat.get("y", 0.0),
    "order": beat.get("order", 0),
    "is_crisis": beat.get("is_crisis", False),
    "is_climax": beat.get("is_climax", False),
})
```

## What Old Dashboard Reads (line ~2566-3951)
- `b.label` (line 2566)
- `b.shift` (line 2567)
- `b.y` (lines 3792, 3831, 3841)
- `b.order` (line 3830)
- `b.id` (line 2566, fallback)
- `beat.is_crisis`, `beat.is_climax` (lines 3846-3848 via CSS class logic — check old dashboard)

## Current Buggy Code (db.py:384-401)
```python
for a in arcs:
    char_id = a.get("character") or a.get("parent_id")
    if not char_id:
        continue
    for c in characters:
        if c["id"] == char_id:
            if "arc_beats_list" not in c:
                c["arc_beats_list"] = []
            c["arc_beats_list"].append(a)  # ← full entity dict!
            break
```

## Fix
Replace the arc grouping with the correct lean shape:
```python
for e in ent_rows:
    if e[1] == "arc":
        extra = json.loads(e[8]) if e[8] else {}
        char_id = extra.get("character", e[6]) or e[6]  # character from extra, fallback to parent_id
        beat_id = e[0]
        for c in characters:
            if c["id"] == char_id:
                if "arc_beats_list" not in c:
                    c["arc_beats_list"] = []
                c["arc_beats_list"].append({
                    "id": beat_id,
                    "label": e[2] or extra.get("label", ""),
                    "scene": extra.get("scene", ""),
                    "shift": extra.get("shift", ""),
                    "y": extra.get("y", 0.0),
                    "order": e[4],  # order_key
                    "is_crisis": extra.get("is_crisis", False),
                    "is_climax": extra.get("is_climax", False),
                })
                break
```

## Files
- `core/db.py` — `get_dashboard_data()` arc grouping section (lines ~384-401)

## Verification (against old dashboard)
- [ ] Check `character.arc_beats_list[0]` in dashboard JSON: must have exactly `{id, label, scene, shift, y, order, is_crisis, is_climax}` (no extra bloat)
- [ ] Old dashboard arc chart (line ~3739) filters `c.arc_beats_list.length > 0` — character must appear
- [ ] Old dashboard arc SVG (line ~3830) reads `beat.label`, `beat.shift`, `beat.y`, `beat.is_crisis`, `beat.is_climax` — all must exist
- [ ] Dashboard arc tooltip (line ~3951) reads `el.dataset.shift` and `el.dataset.y` — must show correct values

## Deferred Issues
None.
