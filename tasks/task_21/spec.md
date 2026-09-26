# `story_load` & `story_retrieve` — Consolidated Spec

Target: define the boundary between load (structural map) and retrieve (entity drill-down), and specify the extended structural views for load.

## Runtime storage invariant (mandatory)

**Resolve the project path, require `.story/story.db`, and query only DB readers. Markdown is not a fallback and is not used to enrich or repair responses.**

This is the canonical rule for these tools and a reusable rule for future runtime tools:

- `story_load` and `story_retrieve` resolve the project path first, then require `.story/story.db`.
- All entity fields, computed values, relations, sections, and memory come from the DB readers in `core.db`.
- Do not read, parse, compare, or fall back to `project.md`, entity `.md` files, `memory.md`, `index.yaml`, or any other Markdown/YAML projection.
- A missing database is an explicit error. Do not reconstruct a response from Markdown.
- Markdown is used only by the explicit import/export boundary.
- This rule applies to extended views and field selection as well as the base views.

### DB source map

The implementation must not use “frontmatter” as a runtime storage assumption. The corresponding data is read from the DB as follows:

- `entities` columns: canonical entity identity and common fields.
- `entities.extra`: entity-specific structured fields.
- `relations` and `relations.note`: cross-entity references, plot beats, relationship perspectives, and relation metadata.
- `sections`: prose section bodies only.
- `core.db` readers: the only supported runtime read API for these tools.

If a value is not available from a DB reader, omit it or return the documented DB error. Never recover it from Markdown.

---

## 1. Tool Boundary

| | `story_load` | `story_retrieve` |
|---|---|---|
| **Scope** | Whole project (structural overview) | Single entity (content drill-down) |
| **Frequency** | Once per session, or on-demand for views | Many times during work |
| **Payload shape** | Nested tree or filtered structural view | Flat entity + requested fields/sections |
| **Agent intent** | "Show me the shape of X" | "Give me this specific thing" |
| **Token budget** | ~8K base, ~2-4K per view | ~1-2K |

**Rule:** Load answers "what exists and where." Retrieve answers "what does this say."

---

## 2. `story_load` — Base View (default)

The slim structural overview. No extended fields, no arc beats, no plot scene arrays.

```json
{
  "loaded": true,
  "confirmation": "Loaded <name> — N scenes (M developed), N sequences, N acts, N characters, N locations, N plots, N worlds.",
  "project": {
    "name": "...",
    "logline": "...",
    "status": "active",
    "genre": "...",
    "setting": "...",
    "spine": "...",
    "controlling_idea": "...",
    "value": "Trust",
    "value_at_open": "positive",
    "value_at_close": "ironic",
    "structure_type": "Classical",
    "act_count": 3
  },
  "acts": [
    {
      "id": "act-1",
      "title": "Act One",
      "status": "in-progress",
      "sequences": [
        {
          "id": "seq-discovery",
          "title": "The Discovery",
          "status": "in-progress",
          "scenes": [
            {
              "id": "central-room-day",
              "title": "Central Room - Day",
              "status": "drafted",
              "one_sentence": "...",
              "chars": ["kael", "mira"],
              "loc": "the-central-room"
            },
            {
              "id": "the-core-day",
              "title": "The Core - Day",
              "status": "written",
              "chars": ["kael", "mira"],
              "loc": "the-garden"
            }
          ]
        }
      ]
    }
  ],
  "characters": [
    {
      "id": "kael",
      "name": "Kael",
      "one_sentence": "...",
      "story_role": "Protagonist",
      "rel": [
        {"id": "mira", "label": "Closest friend", "feeling": "..."}
      ]
    }
  ],
  "plots": [
    {
      "id": "the-resistance",
      "name": "The Resistance",
      "one_sentence": "...",
      "status": "active",
      "plot_scope": "main",
      "characters": ["kael", "mira"]
    }
  ],
  "worlds": [
    {
      "id": "the-i",
      "name": "The I",
      "one_sentence": "A simulation environment where developing consciousness forms.",
      "locations": [
        {
          "id": "the-central-room",
          "name": "The Central Room",
          "one_sentence": "The heart of the Institute — where children believe freedom waits beyond the door."
        },
        {
          "id": "the-garden",
          "name": "The Garden",
          "one_sentence": "A simulated outdoor space where Kael dreams — the only place that feels real."
        }
      ],
      "period": "+400y after the collapse"
    }
  ],
  "memory_outline": {
    "status": "placeholder — design deferred",
    "sections": []
  }
}
```

**Memory rule:** if the base response includes a memory outline, it must come from `core.db.get_project_memory()` or another DB reader. It must not read `.story/memory.md`. The outline shape is deferred; the source and DB-only rule are not deferred.

**Base view field rules:**
- Project: core identity + value fields + structure metadata (no title-page fields)
- Acts/Sequences/Scenes: id, title, status, chars, loc (no climax, no dramatic_role, no value fields, no one_sentence on stubs)
- Characters: name, one_sentence, story_role, rel (no arc_type, no arc_value, no arc beats)
- Plots: name, one_sentence, status, plot_scope, characters (no setups/crisis/climax/payoffs arrays)
- Locations/Worlds: name, one_sentence
- Unfilled: not in base view — opt-in via `view="unfilled"` (§3.5)
- Memory: headers-only outline

---

## 3. `story_load` — Extended Views

Opt-in structural overviews. Activated via `view` parameter. All views return only the fields relevant to their domain — no prose sections, no dropped fields.

### 3.1 `view="arc"` — Character Arc Shape

Returns one character's arc: character DB fields + all beat DB fields, hierarchical.

**Parameters:**
- `project` (required)
- `view="arc"` (required)
- `character` (required) — character slug

```json
{
  "view": "arc",
  "character": "kael",
  "entity": {
    "id": "kael",
    "name": "Kael",
    "arc_type": "positive",
    "arc_value": "Freedom",
    "arc_value_at_open": "negative",
    "arc_value_at_close": "positive",
    "arc_complete": false,
    "beats": [
      {
        "id": "kael-1",
        "label": "The Awakening",
        "scene": "central-room-day",
        "shift": "positive",
        "y": 0.6
      },
      {
        "id": "kael-2",
        "label": "The Betrayal",
        "scene": "central-room-night",
        "shift": "negative",
        "y": -0.3,
        "is_crisis": true
      }
    ]
  }
}
```

**Field notes:**
- Character DB fields: arc_type, arc_value, arc_value_at_open/close, arc_complete (grouped — always returned together)
- Beat DB fields: label, scene ref, shift, y, is_crisis, is_climax (no action/gap/choice prose)
- Beat markers (is_crisis, is_climax): omit when FALSE — only TRUE values emitted
- Beats ordered by array position (order_key)
- Arc beats are returned as lean DB objects (`id`, `label`, `scene`, `shift`, `y`, `order`, `is_crisis`, `is_climax`). Unlabeled stub beats remain objects with an empty `label`; they are not serialized as bare strings.

**Convention:** Arc beats follow the computed-fields convention
(`tasks/task_23/CONVENTION_computed_fields.md`): `character.arc_beats_list` is
`"computed": True` in `ENTITY_SCHEMAS` — read-only, derived at read time, never
persisted, lean `{id, label, scene, shift, y, order, is_crisis, is_climax}`
objects (same shape as dashboard). `get_character_arcs` in `core/db.py` is the
existing backend for this view.

### 3.2 `view="story_value"` — Value Tracking Across Structure

Returns the value arc across acts/sequences/scenes.

**Parameters:**
- `project` (required)
- `view="story_value"` (required)
- `act` (optional, default "all") — act slug

```json
{
  "view": "story_value",
  "act": "act-1",
  "acts": [
    {
      "id": "act-1",
      "title": "Act One",
      "value": "Trust",
      "value_open": "positive",
      "value_close": "negative",
      "sequences": [
        {
          "id": "seq-discovery",
          "title": "The Discovery",
          "value": "Trust",
          "value_open": "positive",
          "value_close": "negative",
          "scenes": [
            {
              "id": "central-room-day",
              "title": "Central Room - Day",
              "value": "Trust",
              "value_open": "positive",
              "value_close": "negative"
            }
          ]
        }
      ]
    }
  ]
}
```

**Field notes:**
- Only value/value_open/value_close at each level
- Act filter: when specified, returns only that act (still wrapped in `acts` array — shape stays consistent)
- No other fields (no chars, no loc, no dramatic_role)

### 3.3 `view="dramatic_elements"` — Structural Markers with Plot Cross-References

Returns dramatic markers per scene + which plots reference each scene in which structural role.

**Parameters:**
- `project` (required)
- `view="dramatic_elements"` (required)
- `act` (optional, default "all") — act slug
- `add_plots` (optional, default false) — include plot cross-references per scene

```json
{
  "view": "dramatic_elements",
  "act": "act-1",
  "acts": [
    {
      "id": "act-1",
      "title": "Act One",
      "inciting_incident_scene_id": "central-room-day",
      "story_climax_scene_id": "central-room-night",
      "sequences": [
        {
          "id": "seq-discovery",
          "scenes": [
            {
              "id": "central-room-day",
              "title": "Central Room - Day",
              "dramatic_role": "setup",
              "milestone": "inciting incident"
            },
            {
              "id": "central-room-night",
              "title": "Central Room - Night",
              "dramatic_role": "climax",
              "milestone": "sequence climax"
            }
          ]
        }
      ]
    }
  ]
}
```

**With `add_plot=true`:**

```json
{
  "view": "dramatic_elements",
  "act": "act-1",
  "add_plot": true,
  "acts": [
    {
      "id": "act-1",
      "title": "Act One",
      "inciting_incident_scene_id": "central-room-day",
      "story_climax_scene_id": "central-room-night",
      "sequences": [
        {
          "id": "seq-discovery",
          "scenes": [
            {
              "id": "central-room-day",
              "title": "Central Room - Day",
              "dramatic_role": "setup",
              "milestone": "inciting incident",
              "plots": [
                {
                  "id": "the-resistance",
                  "scope": "main",
                  "setups": true
                },
                {
                  "id": "the-scientists-last-stand",
                  "scope": "sub",
                  "setups": true
                }
              ]
            },
            {
              "id": "central-room-night",
              "title": "Central Room - Night",
              "dramatic_role": "climax",
              "milestone": "sequence climax",
              "plots": [
                {
                  "id": "the-resistance",
                  "scope": "main",
                  "crisis": true,
                  "climax": true
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Field notes:**
- Story-level per scene: dramatic_role, milestone (single marker: inciting incident|sequence climax|act climax|story climax|null)
- Act-level: inciting_incident_scene_id, story_climax_scene_id
- Plot cross-references: opt-in via `add_plot=true`, default omitted
- Plot markers: only TRUE structural roles shown (setups/crisis/climax/payoffs) — omit FALSE
- Enables cross-verification: "story_climax_scene_id is X — does main plot's climax array include X?"

### 3.4 `view="relationship"` — Full Relationship Graph

Returns all relationship entities with full perspective data. This is the only view that exposes the complete relationship graph — the base view keeps only per-character computed summaries.

**Parameters:**
- `project` (required)
- `view="relationship"` (required)

```json
{
  "view": "relationship",
  "relationships": {
    "kael-mira": {
      "id": "kael-mira",
      "name": "Kael & Mira",
      "characters": ["kael", "mira"],
      "perspectives": {
        "kael": {
          "label": "Closest friend",
          "feeling": "Trusts her feelings more than their own logic",
          "type": "family",
          "strength": 0.9
        },
        "mira": {
          "label": "Friend, anchor",
          "feeling": "Understands his silences better than his words",
          "type": "romantic",
          "strength": 0.7,
          "secret": true
        }
      },
      "scenes": ["central-room-day", "central-room-night"],
      "status": "active"
    }
  }
}
```

**Field notes:**
- Each relationship contains both character perspectives (direction-dependent qualities)
- `secret` omitted when FALSE — only TRUE values emitted
- `strength` range: -1.0 (antagonistic) to 1.0 (bonded); 0.0 = neutral/unknown
- `scenes` list is populated from DB relationship data (optional)
- For network graph rendering: each relationship → one or two directed edges; color by `type`, thickness by `strength`, dashed if `secret`

### 3.5 `view="unfilled"` — What To Work On Next

Returns the inverted unfilled map: which optional fields are still at default, per entity. Answers "what could we work on next" / "what remains to be done" — a data-quality signal, not a domain concern.

**Parameters:**
- `project` (required)
- `view="unfilled"` (required)

```json
{
  "view": "unfilled",
  "unfilled": {
    "goals_short": ["char-a", "char-b"],
    "arc_type": ["char-c"],
    "value_arc": ["the-scientists-last-stand"]
  }
}
```

**Field notes:**
- Inverted map: field name → entity ids still at default
- Stub entities skipped (planned scenes, unlabeled arc beats) — maximally unfilled by definition
- Same logic as `story_retrieve`'s per-entity `unfilled_fields`, aggregated project-wide

**Convention:** `get_unfilled_map` in `core/db.py` is the existing backend for this view — same pattern as `get_character_arcs` (§3.1): backend ready, wired to the tool when task_21 lands.

---

## 4. `story_retrieve` — Entity Drill-Down

Returns the DB-backed entity fields and section prose requested for one or more entities. Fields come from `entities`/`entities.extra`; relation-backed fields come from `relations`; prose comes from `sections`.

**Parameters:**
- `project` (required)
- `entity_type` (required) — character|location|world|plot|project|scene|sequence|act|arc_beat|relationship
- `id` (required) — list of entity slugs/ids (from story_load output `id` field)
- `sections` (optional) — section names to retrieve. `["all"]` for all sections.
- `fields` (optional) — DB-backed field names to retrieve. No grouping — agent names exactly what it wants.

**Call patterns (from brainstorm):**

| Pattern | Call | Returns |
|---|---|---|
| (a) Full entity | `id=["kael"], sections=["all"]` | All DB sections + all DB-backed fields |
| (b) Partial sections | `id=["kael"], sections=["Action", "Gap"]` | Selected DB sections + all DB-backed fields |
| (c) Structured only | `id=["kael"], fields=["all"]` | All DB-backed fields (no sections) |
| (d) Partial fields | `id=["kael", "mira"], fields=["knowledge", "goals_short"]` | Selected fields for multiple entities |

**Return shape (single entity):**

```json
{
  "entity_type": "character",
  "entities": [
    {
      "id": "kael",
      "fields": {
        "arc_type": "positive",
        "arc_value": "Freedom",
        "arc_value_at_open": "negative",
        "arc_value_at_close": "positive"
      },
      "sections": {
        "Arc": "## Arc\nThe arc prose...",
        "Goals": "## Goals\n..."
      },
      "unfilled_fields": ["goals_short", "knowledge"]
    }
  ]
}
```

**Return shape (multiple entities):**

```json
{
  "entity_type": "character",
  "entities": [
    {
      "id": "kael",
      "fields": {
        "knowledge": ["fact1", "fact2"],
        "goals_short": "Find the truth"
      },
      "unfilled_fields": ["goals_long"]
    },
    {
      "id": "mira",
      "fields": {
        "knowledge": [],
        "goals_short": "Protect Kael"
      },
      "unfilled_fields": ["knowledge", "goals_long"]
    }
  ]
}
```

**Notes:**
- `fields` and `sections` are composable — both can be requested in one call
- `fields=["all"]` returns all available DB-backed fields for the entity type
- `fields=["arc_value", "arc_type"]` returns only those DB-backed fields
- Relation-backed fields (for example plot beats and relationship perspectives) are resolved from `relations`, not from Markdown or sections
- `sections=["all"]` returns all DB-stored sections with content
- Unfilled fields are calculated from DB state and included when `fields` is requested
- Empty/default DB fields are included (they signal "not set")
- Sections not found return the available DB-stored section names
- `id` accepts entity slugs from `story_load` output (the `id` field on each entity object)

---

## 5. Field Selection

The agent requests exactly what it needs.

- `fields=["all"]` → returns all DB-backed fields for the entity
- `fields=["arc_value", "arc_type"]` → returns only those fields
- Agent discovers available fields via `story_describe` or by reading a full entity

---

## 6. Unfilled Fields

**In load:** not in the base view. Opt-in via `view="unfilled"` (§3.5) — the "what to work on next" overview. Inverted field→entity list.

**In retrieve:** included when `fields` is requested. Shows which DB-backed fields are still at default for this entity.

**Not a separate tool.** Unfilled is a data-quality signal, not a domain concern.

---

## 7. Open Questions

1. **Batch retrieve** — skip for now. Agent drills one entity at a time. Add `ids=[...]` when a real need surfaces.
2. **Memory retrieval** — deferred. No clean path yet.
3. **World rules retrieval** — stored in DB entity data, not a section. Future expansion.
4. **Plot beat descriptions** — stored as relation notes, not sections. Future expansion.

---

## 8. Migration Notes

- **DB-only runtime:** both handlers resolve the project path, require `.story/story.db`, and query only the `core.db` readers. Markdown is not a fallback, enrichment source, repair source, or comparison source.
- **Storage map:** `entities` columns + `entities.extra` for entity fields; `relations`/`relations.note` for relation-backed fields; `sections` for prose; `core.db.get_project_memory()` for memory.
- **Focused views:** `arc` uses `get_character_arcs`; `unfilled` uses `get_unfilled_map`; base load uses `get_project_summary`; story-value and dramatic-elements views use focused DB projections, not the dashboard payload and not Markdown.
- **Missing data:** omit unavailable values or return a documented DB error; never recover a value from Markdown.
- `get_character_arcs`, `get_unfilled_map`, `get_project_summary`, and the new focused readers must be the only runtime inputs for the corresponding views.
- `story_load` and `story_retrieve` must not import or call `story_export`/`story_import` logic.
- Import/export remain independent file boundaries and are not runtime fallbacks.

---