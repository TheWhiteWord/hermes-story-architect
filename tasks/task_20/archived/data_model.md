# Data Model Reference — Field Inventory & Token Cost Estimates

## Token Estimation Rules

- ~4 chars per token for JSON (rough)
- String field: length + 2 (quotes) tokens
- Number field: ~2 tokens
- Boolean: ~1 token
- JSON object overhead: ~2 tokens per key
- Array element overhead: ~1 token

---

## Entity Fields — All Types

### Common Fields (all entities)

| Field | Storage | Type | Required | Token cost |
|-------|---------|------|----------|------------|
| `id` | column (PK) | string | yes | ~8 |
| `type` | column | string | yes | ~8 |

---

### Character (4 fixture entities: kael, mira, the-administrator, the-outsider, dr-elena-voss, marcus-chen)

| Field | Storage | Required | Typical length | Tokens/entity |
|-------|---------|----------|----------------|---------------|
| `name` | column | yes | 15 chars | 4 |
| `one_sentence` | column | yes | 60 chars | 15 |
| `story_role` | extra | yes | 12 chars | 3 |
| `arc_type` | extra | no | 8 chars | 2 |
| `arc_value` | extra | no | 15 chars | 4 |
| `arc_value_at_open` | extra | no | 8 chars | 2 |
| `arc_value_at_close` | extra | no | 8 chars | 2 |
| `arc_complete` | extra | no | boolean | 1 |
| `relationships` | relation | no | varies | ~20 |
| `goals_short` | extra | no | 15 chars | 4 |
| `goals_long` | extra | no | 20 chars | 5 |
| `knowledge` | extra | no | list of strings | ~15 |
| `status` | column | no | 8 chars | 2 |

**Character total: ~80 tokens/entity × 6 chars = ~480 tokens**

At feature scale (20 characters): **~1,600 tokens**

---

### Scene (3 fixture scenes: central-room-day, central-room-night, the-core-day)

| Field | Storage | Required | Typical length | Tokens/entity |
|-------|---------|----------|----------------|---------------|
| `id` | column (PK) | yes | 15 chars | 4 |
| `title` | column (name) | yes | 20 chars | 5 |
| `order` | column (order_key) | yes | number | 2 |
| `status` | column | no | 10 chars | 3 |
| `sequence_id` | column (parent_id) | yes | 12 chars | 3 |
| `act_id` | extra | yes | 6 chars | 2 |
| `location` | column (location_id) | no | 15 chars | 4 |
| `heading` | extra | no | 30 chars | 8 |
| `time_of_day` | extra | no | 5 chars | 2 |
| `characters` | relation | no | list | ~15 |
| `value` | extra | no | 10 chars | 3 |
| `value_open` | extra | no | 8 chars | 2 |
| `value_close` | extra | no | 8 chars | 2 |
| `conflict_levels` | extra | no | list | ~8 |
| `dramatic_role` | extra | no | 10 chars | 3 |
| `is_inciting_incident` | extra | no | boolean | 1 |
| `is_sequence_climax` | extra | no | boolean | 1 |
| `is_act_climax` | extra | no | boolean | 1 |
| `is_story_climax` | extra | no | boolean | 1 |

**Scene total: ~75 tokens/entity × 3 scenes = ~225 tokens**

At feature scale (120 scenes): **~9,000 tokens** ← biggest contributor

---

### Sequence (1 fixture: seq-discovery)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `title` | column (name) | yes | 5 |
| `order` | column | yes | 2 |
| `status` | column | no | 3 |
| `act_id` | column (parent_id) | yes | 3 |
| `value` | extra | no | 3 |
| `value_open` | extra | no | 2 |
| `value_close` | extra | no | 2 |
| `climax_scene_id` | extra | no | 4 |
| `primary_plot` | extra | no | 4 |
| `purpose` | extra | no | 5 |

**Sequence total: ~40 tokens/entity**

At feature scale (20 sequences): **~800 tokens**

---

### Act (1 fixture: act-1)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `title` | column (name) | yes | 5 |
| `order` | column | yes | 2 |
| `status` | column | no | 3 |
| `value` | extra | no | 3 |
| `value_open` | extra | no | 2 |
| `value_close` | extra | no | 2 |
| `climax_scene_id` | extra | no | 4 |
| `act_objective` | extra | no | 5 |

**Act total: ~30 tokens/entity**

At feature scale (3 acts): **~90 tokens**

---

### Arc Beat (8 fixture beats across kael, dr-elena-voss, marcus-chen, the-administrator)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `label` | column (name) | yes | 12 |
| `order` | column | yes | 2 |
| `character` | column (parent_id) | yes | 4 |
| `scene` | extra | yes | 4 |
| `action` | extra | no | 25 |
| `gap` | extra | no | 25 |
| `choice` | extra | no | 25 |
| `shift` | extra | no | 15 |
| `y` | extra | no | 2 |
| `is_crisis` | extra | no | 1 |
| `is_climax` | extra | no | 1 |

**Arc total: ~120 tokens/entity × 8 beats = ~960 tokens**

At feature scale (20 chars × 5 beats avg = 100 beats): **~12,000 tokens**

---

### Plot (2 fixtures: the-resistance, the-scientists-last-stand)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `name` | column | yes | 20 |
| `one_sentence` | column | no | 15 |
| `status` | column | yes | 3 |
| `plot_type` | extra | no | 3 |
| `plot_scope` | extra | no | 3 |
| `value_arc` | extra | no | 4 |
| `characters` | extra | no | 10 |
| `setups` | relation | no | 20 |
| `crisis` | relation | no | 20 |
| `climax` | relation | no | 20 |
| `payoffs` | relation | no | 20 |

**Plot total: ~140 tokens/entity × 2 = ~280 tokens**

At feature scale (8 plots): **~1,120 tokens**

---

### Location (2 fixtures: the-central-room, the-garden)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `name` | column | yes | 15 |
| `one_sentence` | column | no | 20 |

**Location total: ~40 tokens/entity**

At feature scale (15 locations): **~600 tokens**

---

### World (2 fixtures: the-real-world, the-i)

| Field | Storage | Required | Tokens/entity |
|-------|---------|----------|---------------|
| `id` | column | yes | 4 |
| `name` | column | yes | 12 |
| `one_sentence` | column | no | 20 |
| `rules` | extra | no | 10 |

**World total: ~50 tokens/entity**

At feature scale (5 worlds): **~250 tokens**

---

## Relations — Token Cost

Per relation row: `from_id, to_id, kind` = ~15 tokens

**Fixture**: ~20 relations = ~300 tokens

**Feature scale estimate**:
- character_scene: 120 scenes × 3 chars avg = 360 relations
- location_scene: 120 scenes × 1 location = 120 relations
- character_relationship: 20 chars × 3 avg = 60 relations
- plot_setup/crisis/climax/payoff: 8 plots × 10 scenes avg × 4 beat types = 320 relations
- **Total: ~860 relations × 15 tokens = ~12,900 tokens**

---

## Total Token Budget Estimates

| Component | Fixture (small) | Feature (large) |
|-----------|----------------|-----------------|
| Project metadata | ~150 | ~200 |
| Characters (full extra) | ~480 | ~1,600 |
| Scenes (full extra) | ~225 | **~9,000** |
| Sequences | ~40 | ~800 |
| Acts | ~30 | ~90 |
| Arc beats | ~960 | **~12,000** |
| Plots | ~280 | ~1,120 |
| Locations | ~80 | ~600 |
| Worlds | ~100 | ~250 |
| Relations (all) | ~300 | **~12,900** |
| Unfilled fields | ~100 | ~800 |
| Memory | ~500 | ~5,000 |
| **JSON overhead** | ~500 | ~3,000 |
| **TOTAL** | **~3,700** | **~47,000** |

**The three biggest cost centers for feature films:**
1. Arc beats (12k tokens) — action/gap/choice are long strings
2. Relations (12.9k tokens) — 800+ rows of cross-references
3. Scenes (9k tokens) — 120+ scenes with many extra fields

---

## What story_retrieve Replaces

For each entity type, the body sections available via retrieve:

| Entity | Sections |
|--------|----------|
| character | Personality, Background, Voice, Greatest Fear, Secrets, Arc, Relationships, Goals |
| location | Description, History, Scenes |
| world | Description, History, Conflict |
| plot | Summary, Obstacles, Stakes |
| scene | Description, Dramatic Function, Notes, Content |
| sequence | Summary, Scene Order, Notes |
| act | Summary, Thematic Function, Notes |
| arc | Action, Gap, Choice, Shift, Development Log |
| project | Synopsis, Themes, Structure, Notes |

---

## What story_search Replaces

Full-text search across all section bodies — no equivalent in the current load payload.
