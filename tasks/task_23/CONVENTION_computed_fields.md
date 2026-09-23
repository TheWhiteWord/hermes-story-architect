# Convention: Computed / Read-Only Fields in Entity Schema

## Problem

Some fields exist on entities at read time (load, retrieve, dashboard, search) but should NOT be writable via create or edit. Examples:

- `character.relationships` — materialized summary derived from relationship entities
- `character.arc_beats_list` — derived from arc_beat entities (already exists, currently implicit)
- Future: `scene.character_arcs`, `plot.character_list`, etc.

Without a convention, these fields are either:
- **Invisible** to the LLM (not in schema, only in SKILL.md docs) — LLM can't discover them
- **Accidentally writable** — LLM tries to set them, data gets silently ignored or causes confusion

## Best Practice (Industry Standard)

Modern frameworks use an explicit schema marker:

| Framework | Mechanism |
|-----------|-----------|
| Django ORM | `editable=False` on model fields |
| SQLAlchemy | `column_property`, `hybrid_property` |
| Pydantic v2 | `Field(computed=True)` |
| OpenAPI / JSON Schema | `readOnly: true` |
| GraphQL | Fields are read-only by default; mutations define writable subset |
| Django REST Framework | `read_only_fields` in serializer Meta |

The pattern is: **the schema declares the field AND marks it as non-writable.**

## Convention for This Plugin

Add a `"computed": True` marker to field definitions in `ENTITY_SCHEMAS`.

### Schema Definition

```python
ENTITY_SCHEMAS["character"] = {
    # ... other fields ...
    "relationships": {
        "type": "list",
        "default": [],
        "optional": True,
        "computed": True,  # ← NEW: marks as read-only, derived at read time
        "description": "Computed summary of relationship entities (read-only, derived from relationships/)"
    },
}
```

### Behavior by Tool

| Tool | Behavior with computed fields |
|------|-------------------------------|
| `story_create` | Skip computed fields in merge — they are never written from user input |
| `story_edit` | Skip computed fields in update — reject or silently ignore if provided |
| `story_describe` | Include in output, mark as `computed: true` so LLM knows it's read-only |
| `story_load` | Include in output (derived from source entities) |
| `story_retrieve` | Include in output |
| `story_dashboard` | Include in output |
| `story_export` | Omit from frontmatter (not persisted — derived on import/read) |

### Implementation

**1. Schema marker** (`core/constants.py`):
```python
"relationships": {
    "type": "list", "default": [], "optional": True, "computed": True,
    "description": "Computed summary of relationship entities (read-only)"
}
```

**2. Create guard** (`story_create.py:114`):
```python
for field, meta in schema.items():
    if meta.get("computed"):
        continue  # Skip computed fields — derived at read time
    merged[field] = frontmatter_data.get(field, meta["default"])
```

**3. Edit guard** (`story_edit.py:149-151`):
```python
for key, value in data.items():
    if key in _FIELDS_TO_SKIP:
        continue
    field_meta = schema.get(key, {})
    if field_meta.get("computed"):
        continue  # Reject computed fields — they are read-only
    # ... existing logic ...
```

**4. Describe output** (`story_describe.py`):
```python
# In _all_fields() or _build_tool_schema():
if meta.get("computed"):
    field_schema["computed"] = True
    field_schema["description"] += " (read-only, computed)"
```

**5. Export** (`story_export.py`):
Computed fields are not in the DB as frontmatter — they're derived. So export naturally omits them. If a computed field somehow ends up in `extra` JSON, strip it:
```python
extra = {k: v for k, v in extra.items() if not schema.get(k, {}).get("computed")}
```

### Why This Over Implicit?

The current `arc_beats_list` is implicit — not in schema, only in code. Problems:
- LLM can't discover it via `story_describe`
- No guard prevents LLM from trying to write it
- Each new computed field requires manual documentation in SKILL.md

The explicit marker:
- Single source of truth (schema)
- Tools enforce uniformly
- LLM discovers and respects read-only nature
- Self-documenting for future developers

## Migration for Existing Computed Fields

`arc_beats_list` should be retroactively added to `ENTITY_SCHEMAS["character"]` with `"computed": True`. This is backward-compatible — it only adds documentation and guards.

```python
"arc_beats_list": {
    "type": "list", "default": [], "optional": True, "computed": True,
    "description": "Computed list of arc beats for this character (read-only)"
}
```

## Summary

| Approach | Discoverable | Guarded | Maintainable |
|----------|-------------|---------|--------------|
| Implicit (current `arc_beats_list`) | ❌ No | ❌ No | ❌ Manual docs |
| Schema marker (`computed: True`) | ✅ Yes | ✅ Yes | ✅ Self-documenting |

**Decision**: Use `"computed": True` marker in `ENTITY_SCHEMAS`. Apply to `relationships` on character, retroactively to `arc_beats_list`, and to all future derived fields.
