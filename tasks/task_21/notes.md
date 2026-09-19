# Task 21 — Notes

## story_retrieve: section discovery

Sections were removed from `story_load` payload (token budget). The LLM now has no way to know which sections an entity has available before requesting them.

**Need:** `story_retrieve` should expose which sections exist for an entity, so the LLM can decide what to fetch without guessing.

**Status:** placeholder — to be expanded.

---

## story_retrieve: arc beat retrieval

Arc beats were removed from `story_load` output. Characters now expose only:
- `arc_type`
- `arc_value`
- `arc_value_at_open`
- `arc_value_at_close`

The full arc array (with beats) is no longer in load output. `story_retrieve` needs to handle arc retrieval on demand.

### Reference: old arc logic from `get_project_summary()` (removed in commit 8f9f7e1)

**1. Arc entity processing (in entity loop):**
```python
arcs_by_char = {}  # char_slug -> [arc_info, ...]

# Inside entity loop:
elif etype == "arc":
    arcs_by_char.setdefault(parent_id, []).append({
        "id": eid, "label": name,
        "scene": extra.get("scene", ""),
        "shift": extra.get("shift", ""),
        "y": extra.get("y", 0.0),
        "is_crisis": extra.get("is_crisis", False),
        "is_climax": extra.get("is_climax", False),
        "_order_key": order_key,
    })
```

**2. Character builder (arc array construction):**
```python
char_arcs = sorted(
    arcs_by_char.get(char_id, []),
    key=lambda a: (a["_order_key"], a["id"])
)
arc_list = []
for beat in char_arcs:
    if not beat["label"]:
        arc_list.append(beat["id"])  # stub: bare string
    else:
        beat_obj = {
            "label": beat["label"],
            "scene": beat["scene"],
            "shift": beat["shift"],
            "y": beat["y"],
            "is_crisis": beat["is_crisis"],
            "is_climax": beat["is_climax"],
        }
        arc_list.append(beat_obj)
```

### Reference: old `get_character_arcs` function (removed, for story_retrieve)

```python
def get_character_arcs(project_path: Path, char_id: str) -> list[dict]:
    """Return arc beats for a character, ordered by order_key then id."""
    import sqlite3
    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT id, name, extra, order_key FROM entities WHERE type='arc' AND parent_id=? ORDER BY order_key, id",
            (char_id,),
        ).fetchall()
        return [
            {
                "id": row[0],
                "label": row[1],
                "scene": json.loads(row[2]).get("scene", "") if row[2] else "",
                "shift": json.loads(row[2]).get("shift", "") if row[2] else "",
                "y": json.loads(row[2]).get("y", 0.0) if row[2] else 0.0,
                "is_crisis": json.loads(row[2]).get("is_crisis", False) if row[2] else False,
                "is_climax": json.loads(row[2]).get("is_climax", False) if row[2] else False,
            }
            for row in rows
        ]
    except Exception:
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
```

### DB schema reference

Arc beats are stored in the `entities` table with:
- `type = 'arc'`
- `parent_id` = character slug
- `id` = arc beat slug (e.g., `kael-1`)
- `extra` JSON contains: `scene`, `shift`, `y`, `is_crisis`, `is_climax`

### What story_retrieve needs to do

1. When `entity_type == "arc"`, fetch the arc beat by slug (already works via `_entity_id_for`)
2. Return the arc beat's sections (already works via `get_entity_sections`)
3. **New:** Also return the arc beat's metadata (label, scene, shift, y, is_crisis, is_climax) so the LLM can see the full arc context
4. **New:** When retrieving a character, optionally include their arc beats (or a summary) so the LLM knows what arcs exist

**Status:** placeholder — to be expanded when implementing.
