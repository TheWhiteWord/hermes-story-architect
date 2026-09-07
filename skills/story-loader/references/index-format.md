# Index Format Reference

> Full YAML schema for `.story/index.yaml` — the always-loaded project graph.

---

## Top-Level Structure

```yaml
project:
  slug: the-water-audit
  name: The Water Audit
  logline: "A forensic accountant discovers..."
  genre: Sci-fi thriller
  setting: Near-future city-state
  scene_count: 24
  character_count: 8
  world_count: 2
  plot_count: 3

characters:
  - id: mara
    name: Mara Chen
    role: Protagonist
    one_sentence: "Forensic accountant..."
    sections: [Personality, Background, Voice, ...]
    scenes:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
    related:
      - id: detective-oak
        feeling: Wary respect
    goals_short: "Find the account number."
    goals_long: "Burn the network."
    knowledge:
      - "Her brother Daniel was murdered"

locations:
  - id: kitchen
    name: The Kitchen
    one_sentence: "Commercial kitchen..."
    sections: [Description, History, Scenes]
    scenes:
      - number: 7
        heading: "INT. KITCHEN - NIGHT"

worlds:
  - id: gilead
    name: Gilead
    one_sentence: "Near-future city-state..."
    sections: [Description, History, Conflict]
    rules:
      - "Water rationing is enforced by biometric scanners."

scenes:
  - id: 1
    heading: "INT. MARA'S APARTMENT - NIGHT"
    characters: [mara]
    locations: []
    plots: [brother-investigation]

plots:
  - id: brother-investigation
    name: Brother Investigation
    status: active
    setups:
      - number: 1
        heading: "INT. MARA'S APARTMENT - NIGHT"
    payoffs:
      - number: 22
        heading: "INT. KITCHEN - NIGHT"
    characters: [mara, detective-oak]
    sections: [Summary, Obstacles, Stakes]
    one_sentence: "Mara follows her brother's account number..."

story_memory:
  last_updated: 2026-09-06T14:30:00
  continuity_risks: 2
  headings:
    - CHARACTERS & RELATIONSHIPS
    - CHARACTER KNOWLEDGE
    - TIMELINE
    - PLOT THREADS
    - SETUPS & PAYOFFS
    - WORLD RULES
    - VOICE & STYLE
    - CONTINUITY RISKS
  summary: |
    Mara and Oak are allied but don't fully trust each other...
```

---

## Field Descriptions

### Project

| Field | Type | Description |
|-------|------|-------------|
| `slug` | string | URL-safe project identifier |
| `name` | string | Display name |
| `logline` | string | One-sentence summary |
| `genre` | string | Story genre |
| `setting` | string | Primary setting |
| `scene_count` | number | Total scenes (derived) |
| `character_count` | number | Total characters (derived) |
| `world_count` | number | Total worlds (derived) |
| `plot_count` | number | Total plots (derived) |

### Character

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug (from filename) |
| `name` | string | Display name |
| `role` | string | Protagonist/Antagonist/Supporting/Minor/Cameo |
| `one_sentence` | string | Index label |
| `sections` | string[] | Available `##` headings |
| `scenes` | object[] | Scene references (number + heading) |
| `related` | object[] | Relationships (id + feeling) |
| `goals_short` | string | Short-term goal |
| `goals_long` | string | Long-term goal |
| `knowledge` | string[] | Facts the character knows |

### Location

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug |
| `name` | string | Display name |
| `one_sentence` | string | Index label |
| `sections` | string[] | Available `##` headings |
| `scenes` | object[] | Scene references |

### World

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug |
| `name` | string | Display name |
| `one_sentence` | string | Index label |
| `sections` | string[] | Available `##` headings |
| `rules` | string[] | World rules |

### Scene

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Sequential (regenerated on each index update) |
| `heading` | string | Fountain heading |
| `characters` | string[] | Character slugs |
| `locations` | string[] | Location slugs |
| `plots` | string[] | Plot slugs |

### Plot

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug |
| `name` | string | Display name |
| `status` | string | active/resolved/abandoned |
| `setups` | object[] | Scene references where plot is established |
| `payoffs` | object[] | Scene references where plot resolves |
| `characters` | string[] | Character slugs |
| `sections` | string[] | Available `##` headings |
| `one_sentence` | string | Index label |

### Story Memory

| Field | Type | Description |
|-------|------|-------------|
| `last_updated` | string | ISO datetime |
| `continuity_risks` | number | Number of flagged risks |
| `headings` | string[] | Standard headings in memory |
| `summary` | string | Continuity summary |

---

## Scene Numbering

- `id` is **sequential** (1, 2, 3...), regenerated on each index update
- `scene_number` (from Fountain `#1a#` syntax) is stored as metadata
- Cross-references use **scene headings** (not numbers) for stability

---

## Relationship Representation

Relationships are **unidirectional** — each character lists their own:

```yaml
# characters/mara.md
related:
  - id: detective-oak
    feeling: Wary respect

# characters/detective-oak.md
related:
  - id: mara
    feeling: Wary respect — she's useful but unpredictable
```

Different feelings are valid — relationships are asymmetric.

---

## Story Memory Section

The index stores **summary only**. Full content lives in `.story/memory.md`.

Standard headings:
- CHARACTERS & RELATIONSHIPS
- CHARACTER KNOWLEDGE
- TIMELINE
- PLOT THREADS
- SETUPS & PAYOFFS
- WORLD RULES
- VOICE & STYLE
- CONTINUITY RISKS
