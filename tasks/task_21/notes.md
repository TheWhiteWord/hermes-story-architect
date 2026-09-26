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
---
### example
```
"arc": [
        {
          "label": "The Unlocked Door",
          "scene": "central-room-day",
          "shift": "positive trust → suspicious doubt",
          "y": 0.2,
          "is_crisis": false, //no need fo this - only true fields required//
          "is_climax": false, //no need fo this - only true fields required//
        },
        {
          "label": "The Administrator's Offer",
          "scene": "central-room-night",
          "shift": "suspicious doubt → active defiance",
          "y": -0.3,
          "is_crisis": true,
          "is_climax": false, //no need fo this - only true fields required//
        },
        {
          "label": "Into the Real",
          "scene": "the-core-day",
          "shift": "active defiance → grounded hope",
          "y": 0.6,
          "is_crisis": false,  //no need fo this - only true fields required//
          "is_climax": true,
        },
        {
          "label": "The Point of No Return",
          "scene": "the-door-closes",
          "shift": "grounded hope → hard-won clarity",
          "y": 0.4,
          "is_crisis": false, //no need fo this - only true fields required//
          "is_climax": false, //no need fo this - only true fields required//
        }
      ]
    },
```
---

## story_retrieve: dropped fields call patterns

After the load redesign, fields marked "drop" in the spec are no longer in `story_load` output. The agent must generate `story_retrieve` calls to access them on demand. Map of dropped fields → required retrieve calls:

| Dropped field(s) | Retrieve call |
|---|---|
| Character goals | `story_retrieve("character", slug, sections=["Goals"])` |
| Character knowledge/background | `story_retrieve("character", slug, sections=["Background"])` |
| Character arc_value* | `story_retrieve("character", slug, sections=["Arc"])` |
| Scene heading/content/value | `story_retrieve("scene", slug, sections=["Description","Content"])` |
| Arc beat action/gap/choice | `story_retrieve("arc", slug, sections=["Action","Gap","Choice"])` |
| Plot obstacles/stakes | `story_retrieve("plot", slug, sections=["Summary","Obstacles"])` |
| Sequence/act purpose | `story_retrieve("sequence"/"act", slug, sections=["Summary"])` |
| World rules | **no current retrieve path — needs expansion** |
| Project title-page fields | **no current retrieve path — needs expansion** |
| Plot beat descriptions | **no current retrieve path — needs expansion** |
| Memory detail | **no current retrieve path — flagged backlog** |

---

## story_retrieve: expansion for relation notes and frontmatter extra

Several dropped fields are stored as relation `note` (JSON on the relation row) or frontmatter `extra` JSON — **not** as section bodies in the `sections` table. The current `story_retrieve` tool only returns section bodies from the `sections` table. After the redesign, these fields become inaccessible until `story_retrieve` expands to cover:

- Relation notes (e.g., character relationship `{label, feeling}` sub-fields stored in `relations.note` JSON)
- Frontmatter `extra` JSON fields (e.g., world `rules`, project title-page fields, plot beat descriptions)

This is a known gap. As the redesign is implemented, additional retrieval gaps may surface — capture them in the same backlog.

**Status:** notes captured — to be expanded when implementing.
