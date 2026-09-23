# Task 23: Relationship as First-Class Entity — Refactor Plan

## Goal

Make `relationship` a first-class entity with its own type, frontmatter schema, CRUD operations, and dashboard views — replacing the current system where relationships are embedded in character files as a frontmatter list.

**Related**: `CONVENTION_computed_fields.md` — defines the `"computed": True` schema marker used by this plan.

---

## Design Decisions

### Note 1: Character-Level Relationship Awareness (Computed Field)

Characters keep a **minimal, computed summary** of their relationships, derived from the relationship entities. This gives the LLM context awareness without bloating character files.

**Convention**: Use `"computed": True` marker in `ENTITY_SCHEMAS` (see `CONVENTION_computed_fields.md`). This makes the field:
- **Discoverable**: LLM sees it via `story_describe` (marked as read-only)
- **Guarded**: `story_create` and `story_edit` skip it automatically
- **Present**: Included in `story_load`, `story_retrieve`, `story_dashboard` output
- **Absent**: Omitted from `story_export` frontmatter (derived, not persisted)

```python
ENTITY_SCHEMAS["character"] = {
    # ... other fields ...
    "relationships": {
        "type": "list", "default": [], "optional": True, "computed": True,
        "description": "Computed summary of relationship entities (read-only)"
    },
}
```

**Implementation** (enforced by convention — ~25 lines across 5 files):
- `story_create:114` — skip computed fields in schema merge
- `story_edit:149` — skip computed fields in update loop
- `story_describe` — include `computed: true` marker in output
- `story_export` — strip computed fields from `extra` JSON before writing frontmatter

**Derivation** (follows existing `arc_beats_list` pattern in `db.py:822-842`):
```python
# In get_project_summary (minimal for load)
char_rel_summary = {}
for rel in relationships.values():
    for char_id in rel["characters"]:
        other_id = [c for c in rel["characters"] if c != char_id][0]
        p = rel["perspectives"].get(char_id, {})
        char_rel_summary.setdefault(char_id, []).append({
            "with": other_id,
            "label": p.get("label", ""),
            "type": p.get("type", ""),
        })

# In get_dashboard_data (richer for dashboard)
char_rel_summary[char_id].append({
    "with": other_id, "label": ..., "type": ..., "strength": ...,
})
```

### Note 2: story_load Does NOT Expose Full Relationship Data

The load output for characters includes only the computed summary above. Full relationship data is available via:
- `story_retrieve` on the relationship entity itself
- `story_dashboard` which includes the full `relationships` dict

### Note 3: story_search Global Limitation

The search limitation (extra JSON not indexed) is system-wide, not relationship-specific. Accept the limitation for now. Future work on story_search will address it globally.

---

## Phase 0: Verify Current Behavior (pre-refactor baseline)

| Check | Where | Assert |
|-------|-------|--------|
| `save-the-children` characters use `## Relationship` free-text sections | `fixtures/save-the-children/characters/*.md` | Section present |
| `test_character_has_rel` asserts `char.rel` with `id` + `label` | `test_phase2_db_reads.py:181-189` | Will need update |
| `test_field_coverage` generates `relationships` for characters | `test_field_coverage.py:52-53` | Will need update |
| All existing tests pass | `pytest tests/` | Baseline green |

---

## Phase 1: Schema & Entity Definition

### 1.1 Relationship entity schema (`core/constants.py`)

```python
ENTITY_SCHEMAS["relationship"] = {
    "name": {"type": "string", "default": "", "optional": False, "description": "Display name (e.g. 'Kael & Mira')"},
    "type": {"type": "string", "default": "relationship", "optional": False, "description": "Always 'relationship'"},
    "characters": {"type": "list", "default": [], "optional": False, "description": "Exactly two character slugs"},
    "perspectives": {"type": "object", "default": {}, "optional": False, "description": "Per-character relationship view", "sub_fields": {
        "label": {"type": "string", "description": "Relationship label from this character's POV"},
        "feeling": {"type": "string", "description": "Emotional stance"},
        "type": {"type": "string", "description": "Category: ally/enemy/family/romantic/professional/mentor/rival/custom"},
        "strength": {"type": "number", "description": "Intensity -1.0 to 1.0"},
        "secret": {"type": "boolean", "description": "Hidden from other character"},
    }},
    "scenes": {"type": "list", "default": [], "optional": True, "description": "Scenes where this relationship is featured"},
    "status": {"type": "string", "default": "active", "optional": True, "description": "active/resolved/complex"},
    "history": {"type": "string", "default": "", "optional": True, "description": "How this relationship evolved"},
}
```

### 1.2 Computed field convention (`core/constants.py`)

Add to character schema AND retroactively to `arc_beats_list`:

```python
ENTITY_SCHEMAS["character"] = {
    # ... existing fields ...
    "relationships": {
        "type": "list", "default": [], "optional": True, "computed": True,
        "description": "Computed summary of relationship entities (read-only, derived from relationships/)"
    },
    "arc_beats_list": {
        "type": "list", "default": [], "optional": True, "computed": True,
        "description": "Computed list of arc beats for this character (read-only, derived from arc_beat entities)"
    },
}
```

### 1.3 Computed field guards (`CONVENTION_computed_fields.md` implementation)

**`story_create.py:114`** — skip in merge:
```python
for field, meta in schema.items():
    if meta.get("computed"):
        continue  # Skip computed fields — derived at read time
    merged[field] = frontmatter_data.get(field, meta["default"])
```

**`story_edit.py:149-151`** — skip in update loop:
```python
for key, value in data.items():
    if key in _FIELDS_TO_SKIP:
        continue
    field_meta = schema.get(key, {})
    if field_meta.get("computed"):
        continue  # Read-only field — derived from other entities
    # ... existing logic ...
```

**`story_describe.py`** — mark in output:
```python
# In _all_fields() or _build_tool_schema():
if meta.get("computed"):
    field_schema["computed"] = True
    field_schema["description"] += " (read-only, computed)"
```

**`story_export.py`** — strip from extra:
```python
extra = {k: v for k, v in extra.items() if not schema.get(k, {}).get("computed")}
```

**Cost**: ~25 lines across 5 files.

### 1.4 Validation (`core/entity.py:validate_entity`)

```python
if entity_type == "relationship":
    chars = frontmatter.get("characters", [])
    if len(chars) != 2:
        warnings.append(f"relationship requires exactly 2 characters, got {len(chars)}")
    perspectives = frontmatter.get("perspectives", {})
    for char in chars:
        if char not in perspectives:
            warnings.append(f"Missing perspective for character: {char}")
    for char, p in perspectives.items():
        if "strength" in p and isinstance(p["strength"], (int, float)):
            if not (-1.0 <= float(p["strength"]) <= 1.0):
                warnings.append(f"strength out of range for {char}: {p['strength']}")
```

### 1.5 Column mapping (`core/entity.py`)

```python
ENTITY_COLUMN_MAP["relationship"] = {
    "name": "name", "type": "type", "status": "status",
}
_RELATION_FIELDS["relationship"] = {}  # No relation fields — all data in extra JSON
```

### 1.6 Standard sections

```python
# In entity.py:standard_sections, story_create.py:_get_standard_sections, story_edit.py:_get_standard_sections
"relationship": ["Description", "History", "Dynamics", "Scenes", "Notes"]
```

---

## Phase 2: CRUD Tools

### 2.1 `story_create`

Add `"relationship"` to the entity_type enum in `_build_schema()`. The handler is fully generic — `relations_for_insert("relationship", ...)` returns `[]` (no _RELATION_FIELDS), so all data lives in `extra` JSON.

**Change**: 1 line (enum).

### 2.2 `story_edit`

Add `"relationship"` to enum. Generic handler works — updates extra JSON via the `else` branch in `_edit_note_db`.

**Change**: 1 line (enum).

### 2.3 `story_import`

```python
# In _import_all, add:
_import_folder(conn, project_path, "relationships", "relationship")
```

**Change**: 1 line.

### 2.4 `story_export`

```python
# In _folder_for:
"relationship": "relationships",
```

**Change**: 1 line.

---

## Phase 3: Read Paths (Load/Retrieve/Dashboard)

### 3.1 `story_load` — Character summary + separate relationships

In `get_project_summary`:

```python
# Build relationship entities (new)
relationships = {}
for eid, etype, name, one_sentence, status, order_key, parent_id, extra_json in ent_rows:
    ...
    elif etype == "relationship":
        extra = json.loads(extra_json) if extra_json else {}
        relationships[eid] = {
            "id": eid, "name": name, "status": status,
            "characters": extra.get("characters", []),
            "perspectives": extra.get("perspectives", {}),
            "scenes": extra.get("scenes", []),
            "history": extra.get("history", ""),
        }

# Computed summary on characters (follows CONVENTION_computed_fields)
char_rel_summary = {}
for rel in relationships.values():
    for char_id in rel["characters"]:
        other_id = [c for c in rel["characters"] if c != char_id][0]
        p = rel["perspectives"].get(char_id, {})
        char_rel_summary.setdefault(char_id, []).append({
            "with": other_id,
            "label": p.get("label", ""),
            "type": p.get("type", ""),
        })

# In _build_character:
result["relationships"] = char_rel_summary.get(char_id, [])

# In result dict:
result["relationships"] = relationships
```

**Cost**: ~50 lines (relationship output + computed summary + character integration)

### 3.2 `story_dashboard`

Same as 3.1 but slightly richer summary (include `strength`):

```python
char_rel_summary[char_id].append({
    "with": other_id,
    "label": p.get("label", ""),
    "type": p.get("type", ""),
    "strength": p.get("strength", 0),
})
```

Full `relationships` dict included in `story_data`.

**Cost**: ~50 lines.

### 3.3 `story_retrieve`

Add `"relationship"` to enum. Generic handler works — reads sections by entity_id.

**Change**: 1 line.

---

## Phase 4: Character Schema Cleanup

Remove old relationship handling from `char_rels` / `rel` field in `get_project_summary:177-195,378`. The `## Relationships` free-text section remains as a standard section — it's prose, not structured data.

The `relationships` field is now computed (Phase 1.2), so no explicit removal needed — the convention handles it.

**Cost**: ~20 lines removed.

---

## Phase 5: Migration & Tests

### 5.1 Fixture update (`save-the-children`)

Create `relationships/` files from character `## Relationship` sections:

```
relationships/kael-mira.md
relationships/kael-administrator.md
relationships/mira-administrator.md
```

### 5.2 Test updates

| Test | Change |
|------|--------|
| `test_character_has_rel` | Rewrite: assert `char.relationships` is computed summary with `with`/`label`/`type`; or assert relationship entity in load output |
| `test_field_coverage` | Remove `_sample_value("relationships")` for character; add `"relationship"` entity type test |
| `test_round_trip` | Add relationship entity round-trip |
| `test_core` | Update relationship comments |

**Cost**: ~80 lines.

---

## Phase 6: Skill Documentation Update (DEFERRED - skills will need to be look at independenly in a different task)

In `skills/hermes-story-architect/SKILL.md`:

```markdown
## Relationships

Relationships are first-class entities. Each relationship stores two `perspectives` — one per character — capturing direction-dependent qualities (A loves B / B sees A as friend).

### story_load view
Characters include a computed `relationships` summary (minimal: `with`, `label`, `type`). Full relationship data is in the top-level `relationships` dict.

### story_retrieve
Use `entity_type="relationship"` with the relationship slug to get full details.

### story_create
Create relationships after both characters exist. The `perspectives` object must contain both character slugs.

### Computed fields
`character.relationships` and `character.arc_beats_list` are computed fields — they appear in load/retrieve/dashboard output but are NOT writable via create/edit. They are always derived fresh from their source entities.
```

---

## Phase 7: Dashboard UI Brief (for UI specialist)

### 7.1 Data contract

```json
{
  "characters": {
    "kael": {
      "id": "kael",
      "name": "Kael",
      "relationships": [
        {"with": "mira", "label": "Closest friend", "type": "family", "strength": 0.9},
        {"with": "the-administrator", "label": "Antagonist", "type": "rival", "strength": -0.3}
      ]
    }
  },
  "relationships": {
    "kael-mira": {
      "id": "kael-mira",
      "name": "Kael & Mira",
      "characters": ["kael", "mira"],
      "perspectives": {
        "kael": {"label": "Closest friend", "feeling": "Trusts her feelings...", "type": "family", "strength": 0.9},
        "mira": {"label": "Friend, anchor", "feeling": "Understands his silences", "type": "romantic", "strength": 0.7, "secret": true}
      },
      "scenes": ["central-room-day", "central-room-night"],
      "status": "active"
    }
  }
}
```

### 7.2 Changes to existing UI

**Network graph** (`buildGraphView`):
- Read from `story.relationships`, NOT `c.related`
- Each relationship → one or two directed edges (one if mutual, two if asymmetric)
- Edge color by `type`, thickness by `strength`, dashed if `secret`
- Multiple edges between same pair: parallel curves
- Click edge → show relationship panel

**Character panel** (`showCharacterPanel`):
- Show "Relationships" section from `char.relationships` array
- Each entry: clickable name + label + type icon
- Secret indicator (🔗/🔒) for relationships where perspective is secret

**New relationship panel** (`showRelationshipPanel`):
- Both perspectives side-by-side
- Scenes list, history section
- Edit button → `story_edit` for relationship

**Sidebar**:
- Add "Relationships" tab between "Characters" and "Plots"
- Filter by type/status

---

## Phase 8: Verification

### 8.1 Test suite
```bash
pytest tests/ -x
```

### 8.2 Manual checks
1. Create project with 2 characters + 1 asymmetric relationship
2. Dashboard: graph shows two directed edges with different labels
3. Character panel: shows relationship summary
4. Export: `relationships/` folder has correct files
5. Re-import: relationships restored

### 8.3 Edge cases
- Delete one character → relationship shows as `broken` or cascade-deletes
- Three characters → 3 relationship entities, graph shows triangle
- Same pair, multiple relationships → separate relationship entities

---

## Dependency Map

```
constants.py (schema + computed markers)
    ↓
entity.py (validation, columns, relations_for_insert)
    ↓
story_create.py ← enum + computed guard
story_edit.py ← enum + computed guard
story_import.py ← folder
story_export.py ← folder + computed strip
story_describe.py ← computed marker in output
    ↓
db.py (get_project_summary, get_dashboard_data)
    ↓
story_dashboard.py ← consumes data
SKILL.md ← documents computed field
src/dashboard/*.html ← UI (Phase 7)
```

---

## Total Estimate

| Phase | Lines |
|-------|-------|
| 1. Schema + validation + computed convention | ~85 |
| 2. CRUD enum updates | ~5 |
| 3. Read paths (load + dashboard) | ~100 |
| 4. Character cleanup | -20 |
| 5. Migration & tests | ~80 |
| 6. Skill docs | ~20 |
| 7. UI brief (doc) | ~100 |
| 8. Verification | ~40 |
| **Total** | **~410** |
