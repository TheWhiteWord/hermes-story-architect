# Current Payload Example (Fixture: save-the-children)

## Shape

```json
{
  "loaded": true,
  "confirmation": "Loaded Save the Children — 0 arc beats, 3 scenes, 1 sequences, 1 acts, 6 characters, 2 locations, 2 plots.",
  "project": {
    "name": "Save the Children",
    "logline": "In a world where humanity survives only as consciousness inside a machine, a young person fights to escape an oppressive system — unaware that the rebellion itself, the system, and every feeling of purpose they have ever known are the inherited memories of the last scientists who built the world that imprisoned them.",
    "genre": "Sci-fi drama",
    "setting": "The Institute — a decaying research facility, 400 years apart",
    "status": "active",
    "spine": "A young person discovers the truth about their world and chooses to escape",
    "controlling_idea": "Freedom requires sacrifice",
    "value": "Trust",
    "value_at_open": "positive",
    "value_at_close": "negative",
    "inciting_incident_scene_id": "central-room-day",
    "story_climax_scene_id": "central-room-night",
    "structure_type": "Classical",
    "act_count": 3
  },
  "entities": {
    "cols": ["id", "type", "name", "one_sentence", "status", "order_key", "parent_id", "location_id", "extra"],
    "rows": [
      ["act-1", "act", "Act I", "", "planned", 0, null, null, {}],
      ["seq-discovery", "sequence", "Sequence A", "", "planned", 0, "act-1", null, {}],
      ["central-room-day", "scene", "Central Room - Day", "Kael discovers the door isn't locked — it was never locked.", "drafted", 1, "seq-discovery", "the-central-room", {"heading": "INT. THE CENTRAL ROOM - DAY", "time_of_day": "DAY", "act_id": "act-1", "characters": ["kael", "mira"], "value": "Trust", "value_open": "positive", "value_close": "negative", "conflict_levels": ["inner", "personal"], "dramatic_role": "setup", "is_inciting_incident": false, "is_sequence_climax": false, "is_act_climax": false, "is_story_climax": false}],
      ["central-room-night", "scene", "Central Room - Night", "", "planned", 2, "seq-discovery", "the-central-room", {"heading": "INT. THE CENTRAL ROOM - NIGHT", "time_of_day": "NIGHT", "act_id": "act-1", "characters": [], "value": "", "value_open": "", "value_close": "", "conflict_levels": [], "dramatic_role": "", "is_inciting_incident": false, "is_sequence_climax": false, "is_act_climax": false, "is_story_climax": false}],
      ["the-core-day", "scene", "The Core - Day", "", "planned", 3, "seq-discovery", null, {"heading": "INT. THE CORE - DAY", "time_of_day": "DAY", "act_id": "act-1", "characters": [], "value": "", "value_open": "", "value_close": "", "conflict_levels": [], "dramatic_role": "", "is_inciting_incident": false, "is_sequence_climax": false, "is_act_climax": false, "is_story_climax": false}],
      ["kael", "character", "Kael", "A young person inside The I who begins to feel the system is wrong.", "", 0, null, null, {"story_role": "Protagonist", "arc_type": "positive", "arc_value": "", "arc_value_at_open": "", "arc_value_at_close": "", "arc_complete": false, "relationships": [{"id": "mira", "label": "closest friend", "feeling": "..."}, {"id": "the-administrator", "label": "antagonist", "feeling": "..."}], "goals_short": "", "goals_long": "", "knowledge": []}],
      ["mira", "character", "Mira", "...", "", 0, null, null, {"story_role": "Supporting", "arc_type": "positive", ...}],
      ["the-administrator", "character", "The Administrator", "...", "", 0, null, null, {"story_role": "Antagonist", ...}],
      ["the-outsider", "character", "The Outsider", "...", "", 0, null, null, {"story_role": "Supporting", ...}],
      ["dr-elena-voss", "character", "Dr. Elena Voss", "...", "", 0, null, null, {"story_role": "Supporting", ...}],
      ["marcus-chen", "character", "Marcus Chen", "...", "", 0, null, null, {"story_role": "Supporting", ...}],
      ["the-central-room", "location", "The Central Room", "...", "", 0, null, null, {}],
      ["the-garden", "location", "The Garden", "...", "", 0, null, null, {}],
      ["the-real-world", "world", "The Real World", "...", "", 0, null, null, {rules: [...]}],
      ["the-i", "world", "The I", "...", "", 0, null, null, {rules: [...]}],
      ["the-resistance", "plot", "The Resistance", "The core plot...", "active", 0, null, null, {"plot_type": "Complicating", "plot_scope": "main", "value_arc": "Maturation", "characters": ["kael", "mira"], "setups": [{"scene_id": "central-room-day", "description": "..."}], "crisis": [...], "climax": [...], "payoffs": [...]}],
      ["the-scientists-last-stand", "plot", "The Scientist's Last Stand", "...", "active", 0, null, null, {"plot_type": "Contradictory", "plot_scope": "main", "value_arc": "Education", ...}],
      ["kael-1", "arc", "First Doubt", "Kael asks Mira about the inconsistency...", "", 1, "kael", null, {"scene": "central-room-day", "action": "Kael asks Mira...", "gap": "Mira deflects...", "choice": "Kael drops it...", "shift": "positive → mixed", "y": 0.8, "is_crisis": false, "is_climax": false}],
      ["kael-2", "arc", "Second Doubt", "...", "", 2, "kael", null, {"scene": "...", "action": "...", "gap": "...", "choice": "...", "shift": "...", "y": 0.4, ...}],
      ["kael-3", "arc", "...", "...", "", 3, "kael", null, {...}],
      ["dr-elena-voss-1", "arc", "...", "...", "", 1, "dr-elena-voss", null, {...}],
      ["dr-elena-voss-2", "arc", "...", "...", "", 2, "dr-elena-voss", null, {...}],
      ["dr-elena-voss-3", "arc", "...", "...", "", 3, "dr-elena-voss", null, {...}],
      ["marcus-chen-1", "arc", "...", "...", "", 1, "marcus-chen", null, {...}],
      ["marcus-chen-2", "arc", "...", "...", "", 2, "marcus-chen", null, {...}],
      ["the-administrator-1", "arc", "...", "...", "", 1, "the-administrator", null, {...}],
      ["the-administrator-2", "arc", "...", "...", "", 2, "the-administrator", null, {...}],
      ["the-administrator-3", "arc", "...", "...", "", 3, "the-administrator", null, {...}]
    ]
  },
  "relations": {
    "cols": ["from_id", "to_id", "kind"],
    "rows": [
      ["kael", "central-room-day", "character_scene"],
      ["mira", "central-room-day", "character_scene"],
      ["the-central-room", "central-room-day", "location_scene"],
      ["the-central-room", "central-room-night", "location_scene"],
      ["the-resistance", "central-room-day", "plot_setup"],
      ["the-resistance", "central-room-night", "plot_crisis"],
      ["the-scientists-last-stand", "central-room-day", "plot_setup"],
      ["the-scientists-last-stand", "the-core-day", "plot_payoff"],
      ...
    ]
  },
  "memory": "# Story Memory\n\n## Continuity notes\n...\n## Character knowledge\n...\n## World events\n...\n## Open questions\n...",
  "unfilled": {
    "kael": ["goals_short", "goals_long", "knowledge", "arc_value", ...],
    "central-room-day": ["characters", ...],
    ...
  }
}
```

## Actual Token Cost (Fixture)

The JSON for the fixture project (28 entities, ~20 relations, memory ~500 chars) is approximately **3,500-4,000 tokens**.

This is a small project (3 scenes, 6 chars, 8 arc beats, 2 plots).

## Scaling Analysis

At feature scale (120 scenes, 20 chars, 100 arc beats, 8 plots, 860 relations):

| Component | Current tokens | Notes |
|-----------|---------------|-------|
| Project metadata | ~200 | One entity |
| Characters (all extra) | ~1,600 | 20 chars × 80 tokens |
| Scenes (all extra) | **~9,000** | 120 scenes × 75 tokens |
| Sequences | ~800 | 20 seqs × 40 tokens |
| Acts | ~90 | 3 acts × 30 tokens |
| Arc beats | **~12,000** | 100 beats × 120 tokens |
| Plots | ~1,120 | 8 plots × 140 tokens |
| Locations | ~600 | 15 locs × 40 tokens |
| Worlds | ~250 | 5 worlds × 50 tokens |
| Relations | **~12,900** | 860 rows × 15 tokens |
| Unfilled fields | ~800 | ~140 entities × 6 fields avg |
| Memory | ~5,000 | Large continuity notes |
| JSON overhead | ~3,000 | Brackets, commas, keys |
| **TOTAL** | **~47,000** | Way too much for a session-start overview |

---

## Observations

1. **Arc beats dominate** — the `action`, `gap`, `choice` fields are long prose (25+ tokens each). At 100 beats this is 12k tokens of body-level detail.
2. **Relations are raw** — all 860 relation rows dumped flat. The agent has to scan/join them mentally.
3. **Scenes carry heavy extra** — every scene dumps all frontmatter in extra JSON, including empty defaults.
4. **All entities at same fidelity** — no distinction between "overview" and "detail work" fields.

---

## Retrieval Capabilities (What Can Replace Load Data)

| Need | Tool | Granularity |
|------|------|-------------|
| Character personality, background, voice | `story_retrieve(entity_type="character", slug="kael", sections=["Personality", "Background"])` | Per-section |
| Scene description, content, notes | `story_retrieve(entity_type="scene", slug="central-room-day", sections=["Description", "Content"])` | Per-section |
| Arc beat action/gap/choice text | `story_retrieve(entity_type="arc", slug="kael-1", sections=["Action", "Gap", "Choice"])` | Per-section |
| Plot summary, obstacles, stakes | `story_retrieve(entity_type="plot", slug="the-resistance", sections=["Summary", "Obstacles"])` | Per-section |
| Find text across all sections | `story_search(query="garden")` | Full-text |
| Project synopsis, themes | `story_retrieve(entity_type="project", slug="project", sections=["Synopsis", "Themes"])` | Per-section |
| Visual structure/dashboard | `story_dashboard(project="save-the-children")` | Visual HTML |
