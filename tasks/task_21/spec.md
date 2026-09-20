# `story_load` & `story_retrieve` — Consolidated Spec

Target: define the boundary between load (structural map) and retrieve (entity drill-down), and specify the extended structural views for load.

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
  "locations": [
    {
      "id": "the-central-room",
      "name": "The Central Room",
      "one_sentence": "..."
    }
  ],
  "worlds": [
    {
      "id": "the-i",
      "name": "The I",
      "one_sentence": "..."
    }
  ],
  "unfilled": {
    "goals_short": ["char-a", "char-b"],
    "arc_type": ["char-c"]
  },
  "memory_outline": {
    "status": "placeholder — design deferred",
    "sections": []
  }
}
```

**Base view field rules:**
- Project: core identity + value fields + structure metadata (no title-page fields)
- Acts/Sequences/Scenes: id, title, status, chars, loc (no climax, no dramatic_role, no value fields, no one_sentence on stubs)
- Characters: name, one_sentence, story_role, rel (no arc_type, no arc_value, no arc beats)
- Plots: name, one_sentence, status, plot_scope, characters (no setups/crisis/climax/payoffs arrays)
- Locations/Worlds: name, one_sentence
- Unfilled: inverted field→entity list, ~180 tokens
- Memory: headers-only outline

---

## 3. `story_load` — Extended Views

Opt-in structural overviews. Activated via `view` parameter. All views return only the fields relevant to their domain — no prose sections, no dropped fields.

### 3.1 `view="arc"` — Character Arc Shape

Returns one character's arc: character FM + all beat FM, hierarchical.

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
- Character FM: arc_type, arc_value, arc_value_at_open/close, arc_complete (grouped — always returned together)
- Beat FM: label, scene ref, shift, y, is_crisis, is_climax (no action/gap/choice prose)
- Beat markers (is_crisis, is_climax): omit when FALSE — only TRUE values emitted
- Beats ordered by array position (order_key)
- Stub beats (no label) included as bare strings

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

---

## 4. `story_retrieve` — Entity Drill-Down

Single or multiple entity focus. Returns sections (prose) and/or frontmatter fields.

**Parameters:**
- `project` (required)
- `entity_type` (required) — character|location|world|plot|project|scene|sequence|act|arc
- `id` (required) — list of entity slugs/ids (from story_load output `id` field)
- `sections` (optional) — section names to retrieve. `["all"]` for all sections.
- `fields` (optional) — FM field names to retrieve. No grouping — agent names exactly what it wants.

**Note on `arc`:** The entity type is `arc`, but each entry is an individual *beat* (e.g., `kael-1`, `kael-2`). Retrieving `entity_type="arc"` returns the specified beats, not a whole arc as a sequence. To get all beats for a character, use `story_load(view="arc", character="kael")`.

**Call patterns (from brainstorm):**

| Pattern | Call | Returns |
|---|---|---|
| (a) Full entity | `id=["kael"], sections=["all"]` | All sections + all FM |
| (b) Partial sections | `id=["kael"], sections=["Action", "Gap"]` | Selected sections + all FM |
| (c) Structured only | `id=["kael"], fields=["all"]` | All FM (no sections) |
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
- `fields=["all"]` returns all FM for the entity type
- `sections=["all"]` returns all sections with content
- Unfilled fields included when `fields` is requested (shows what's still at default)
- Empty/default FM fields are included (they signal "not set")
- Sections not found return available list
- No field grouping — agent names exactly what it wants
- `id` accepts entity slugs from story_load output (the `id` field on each entity object)

---

## 5. Field Selection

The agent requests exactly what it needs.

- `fields=["all"]` → returns all FM fields for the entity
- `fields=["arc_value", "arc_type"]` → returns only those fields
- Agent discovers available fields via `story_describe` or by reading a full entity

---

## 6. Unfilled Fields

**In load:** included as a small `unfilled` key in base view (~180 tokens). Inverted field→entity list.

**In retrieve:** included when `fields` is requested. Shows which FM fields are still at default for this entity.

**Not a separate tool.** Unfilled is a data-quality signal, not a domain concern.

---

## 7. Open Questions

1. **Batch retrieve** — skip for now. Agent drills one entity at a time. Add `slugs=[...]` when a real need surfaces.
2. **Memory retrieval** — deferred. No clean path yet.
3. **World rules retrieval** — stored as frontmatter, not section. Future expansion.
4. **Plot beat descriptions** — stored as relation notes, not sections. Future expansion.

---

## 8. Migration Notes

- Current `story_load` base view already close — remove plot scene arrays, remove arc beats from characters, remove climax/dramatic_role from scenes
- Current `story_retrieve` needs FM field support added (currently sections-only)
- Extended views (`arc`, `story_value`, `dramatic_elements`) are new — no migration needed
- Unfilled fields stay in load but may move to a separate `story_status` tool later
- Agent requests `fields=["all"]` → returns all groups
- Agent can request specific fields by name if it wants to ignore grouping
- Grouping is a return-shape concern, not a request concern

---

## 6. Unfilled Fields

**In load:** included as a small `unfilled` key in base view (~180 tokens). Inverted field→entity list.

**In retrieve:** included when `fields` is requested. Shows which FM fields are still at default for this entity.

**Not a separate tool.** Unfilled is a data-quality signal, not a domain concern.

---

## 7. Open Questions

1. **Batch retrieve** — skip for now. Agent drills one entity at a time. Add `slugs=[...]` when a real need surfaces.
2. **Memory retrieval** — deferred. No clean path yet.
3. **World rules retrieval** — stored as frontmatter, not section. Future expansion.
4. **Plot beat descriptions** — stored as relation notes, not sections. Future expansion.

---

## 8. Migration Notes

- Current `story_load` base view already close — remove plot scene arrays, remove arc beats from characters, remove climax/dramatic_role from scenes
- Current `story_retrieve` needs FM field support added (currently sections-only)
- Extended views (`arc`, `story_value`, `dramatic_elements`) are new — no migration needed
- Unfilled fields stay in load but may move to a separate `story_status` tool later
