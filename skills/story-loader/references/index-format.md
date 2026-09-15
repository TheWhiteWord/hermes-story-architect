# Index Format Reference

> Full YAML schema for `.story/index.yaml` — the always-loaded project graph.
> Field names match the code exactly. Descriptions are minimal.
>
> **Source column:**
> - **frontmatter** — LLM domain. Can be set/edited via `story_create` or `story_edit`.
> - **code** — Derived/calculated by the index generator or screenplay analysis. Do not modify directly.
> - **filename** — Pre-established from the note's filename. Do not modify.

---

## Top-Level Structure

```yaml
project:
  id: project-slug
  name: Project Name
  logline: One-sentence summary
  genre: Genre
  setting: Primary setting
  status: active
  sections: [Logline, Themes, Notes]
  scene_count: 9
  character_count: 5
  location_count: 2
  world_count: 1
  plot_count: 2
  sequence_count: 3
  act_count: 2
  arc_count: 2

characters:
  - id: character-slug
    name: Character Name
    story_role: Protagonist
    one_sentence: Short description
    sections: [Personality, Background, Voice, Arc, Relationships, Goals]
    scenes:
      - id: scene-slug
        title: Scene Title
        heading: INT. LOCATION - DAY

locations:
  - id: location-slug
    name: Location Name
    one_sentence: Short description
    sections: [Description, History, Scenes]
    scenes:
      - id: scene-slug
        title: Scene Title
        heading: INT. LOCATION - DAY

worlds:
  - id: world-slug
    name: World Name
    one_sentence: Short description
    sections: [Description, History, Conflict]

plots:
  - id: plot-slug
    name: Plot Name
    one_sentence: Short description
    status: active
    characters: [character-slug]
    setups:
      - scene_id: scene-slug
        description: What happens at this scene
    payoffs:
      - scene_id: scene-slug
        description: Resolution
    sections: [Summary, Obstacles, Stakes]

scenes:
  - id: scene-slug
    title: Scene Title
    order: 1
    status: planned
    sequence_id: sequence-slug
    act_id: act-slug
    heading: INT. LOCATION - DAY
    characters: [character-slug]
    plots: [plot-slug]
    location: location-slug

sequences:
  - id: sequence-slug
    title: Sequence Title
    order: 1
    status: planned
    act_id: act-slug
    scenes_list: [scene-slug]
    scene_count: 3

acts:
  - id: act-slug
    title: Act I
    order: 1
    status: planned
    sequences_list: [sequence-slug]
    scenes_list: [scene-slug]
    sequence_count: 1
    scene_count: 3
```

---

## Field Descriptions

### Project
| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Slug (from folder name) | filename |
| `name` | string | Display name | frontmatter |
| `logline` | string | One-sentence summary | frontmatter |
| `genre` | string | Story genre | frontmatter |
| `setting` | string | Primary setting | frontmatter |
| `status` | string | One of: active, abandoned, archived | frontmatter |
| `sections` | string[] | Available `##` headings | code |
| `scene_count` | number | Total scenes | code |
| `character_count` | number | Total characters | code |
| `location_count` | number | Total locations | code |
| `world_count` | number | Total worlds | code |
| `plot_count` | number | Total plots | code |
| `sequence_count` | number | Total sequences | code |
| `act_count` | number | Total acts | code |
| `spine` | string | Protagonist's core desire driving the whole story | frontmatter |
| `controlling_idea` | string | The story's argument — how and why life changes | frontmatter |
| `value` | string | Value at stake for the whole story (e.g. `Trust`) | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `inciting_incident_scene_id` | string | Scene slug of the inciting incident | frontmatter |
| `story_climax_scene_id` | string | Scene slug of the story's climax | frontmatter |
| `structure_type` | string | One of: `Classical`, `Miniplot`, `Antiplot` | frontmatter |

### Character
| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Slug (from filename) | filename |
| `name` | string | Display name | frontmatter |
| `story_role` | string | One of: Protagonist, Antagonist, Supporting, Minor, Cameo | frontmatter |
| `one_sentence` | string | One-sentence summary for index label | frontmatter |
| `sections` | string[] | Available `##` headings | code |
| `scenes` | object[] | Scene references: `number` + `heading` | code |
| `relationships` | object[] | Unidirectional. Each: {id, label, feeling} | frontmatter |
| `goals_short` | string | Short-term goal | frontmatter |
| `goals_long` | string | Long-term goal | frontmatter |
| `knowledge` | string[] | Facts the character knows | frontmatter |

### Location
| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Slug (from filename) | filename |
| `name` | string | Display name | frontmatter |
| `one_sentence` | string | One-sentence summary for index label | frontmatter |
| `sections` | string[] | Available `##` headings | code |
| `scenes` | object[] | Scene references: `number` + `heading` | code |

### World
| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Slug (from filename) | filename |
| `name` | string | Display name | frontmatter |
| `one_sentence` | string | One-sentence summary for index label | frontmatter |
| `sections` | string[] | Available `##` headings | code |
| `rules` | string[] | World rules | frontmatter |

### Plot
| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Slug (from filename) | filename |
| `name` | string | Display name | frontmatter |
| `one_sentence` | string | One-sentence summary for index label | frontmatter |
| `plot_type` | string | One of: Contradictory, Resonant, Complicating, Setup | frontmatter |
| `status` | string | One of: active, resolved, abandoned | frontmatter |
| `characters` | string[] | Character slugs (frontmatter-only) | frontmatter |
| `setups` | object[] | Scenes where plot is established: `scene_id` + `description` | frontmatter |
| `payoffs` | object[] | Scenes where plot resolves: `scene_id` + `description` | frontmatter |
| `sections` | string[] | Available `##` headings | code |

### Scene
> **From scene files** — scenes are individual `.md` files in `scenes/`, assembled in sequence order by the dashboard.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Dramatic-function slug (e.g. `mara-discovers-files`) | frontmatter |
| `title` | string | Display name | frontmatter |
| `order` | number | Position within parent sequence | frontmatter |
| `status` | string | One of: planned, drafted, written, locked | frontmatter |
| `sequence_id` | string | Parent sequence slug | frontmatter |
| `act_id` | string | Parent act slug (denormalized) | frontmatter |
| `heading` | string | Fountain scene heading | frontmatter |
| `characters` | string[] | Character slugs | frontmatter |
| `plots` | object[] | Plot references: `id` + `beat` (setup or payoff) | code |
| `location` | string | Location slug | frontmatter |
| `value` | string | Value at stake in this scene | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `conflict_levels` | string[] | Any of: `inner`, `personal`, `extra-personal` | frontmatter |
| `dramatic_role` | string | One of: `setup`, `complication`, `crisis`, `climax`, `resolution`, `transition`, `non-event` | frontmatter |
| `is_inciting_incident` | boolean | Marks the story's inciting incident | frontmatter |
| `is_sequence_climax` | boolean | Marks the sequence's climax scene | frontmatter |
| `is_act_climax` | boolean | Marks the act's climax scene | frontmatter |
| `is_story_climax` | boolean | Marks the story's climax scene | frontmatter |
| `arc_beat_refs` | array | Reserved for future arc beat linking (always `[]`) | code |

### Sequence

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Stable slug | frontmatter |
| `title` | string | Display name | frontmatter |
| `order` | number | Position within parent act | frontmatter |
| `status` | string | One of: planned, in-progress, complete | frontmatter |
| `act_id` | string | Parent act slug | frontmatter |
| `scenes_list` | string[] | Scene slugs in this sequence (sorted by order) | code |
| `scene_count` | number | Total scenes in this sequence | code |
| `plots` | object[] | Plots in this sequence: `id` + `has_setup` + `has_payoff` | code |
| `value` | string | Value at stake in this sequence | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `climax_scene_id` | string | Scene slug where this sequence's reversal lands | frontmatter |

### Act

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Stable slug | frontmatter |
| `title` | string | Display name | frontmatter |
| `order` | number | Position within story | frontmatter |
| `status` | string | One of: planned, in-progress, complete | frontmatter |
| `sequences_list` | string[] | Sequence slugs in this act (sorted by order) | code |
| `scenes_list` | string[] | Scene slugs in this act (sorted by order) | code |
| `sequence_count` | number | Total sequences in this act | code |
| `scene_count` | number | Total scenes in this act | code |
| `plots` | object[] | Plots in this act: `id` + `has_setup` + `has_payoff` | code |
| `value` | string | Value at stake in this act | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `climax_scene_id` | string | Scene slug where this act's major reversal lands | frontmatter |

---

## Arcs

```yaml
arcs:
  - id: "1"
    character: character-slug
    scene: scene-slug
    label: "First Doubt"
    action: "What the character does"
    gap: "Expectation vs reality"
    choice: "The choice made"
    shift: "positive → mixed"
    y: 0.5
    order: 1
    is_crisis: false
    is_climax: false
    sections: [Action, Gap, Choice, Shift, Development Log]
```

**Notes:**
- Arc beats are stored in `arcs/{character}/{beat_id}.md` (nested by character)
- Beat files use numeric IDs (`1.md`, `2.md`) for ordering
- The `character` field is inferred from the folder if not in frontmatter
- The `y` field is the value charge at that beat (-1.0 to +1.0)

### Enriched Fields on Characters

```yaml
characters:
  - id: character-slug
    arc_type: positive | negative | flat | ironic | absent
    arc_value: Value at stake
    arc_value_at_open: positive | negative | mixed | ironic
    arc_value_at_close: positive | negative | mixed | ironic
    arc_complete: true | false
    arc_beat_count: 3
    arc_beats_list:
      - id: "1"
        label: "First Doubt"
        scene: scene-slug
        shift: "positive → mixed"
        y: 0.5
        order: 1
        is_crisis: false
        is_climax: false
```

**Source:** `arc_beats_list` and `arc_beat_count` are derived by the index generator. `arc_type`, `arc_value`, `arc_value_at_open`, `arc_value_at_close`, `arc_complete` are frontmatter (LLM domain).

### Enriched Fields on Scenes

```yaml
scenes:
  - id: scene-slug
    arc_beats:
      - character: character-slug
        beat_id: "1"
        label: "First Doubt"
        y: 0.5
        is_crisis: false
        is_climax: false
```

**Source:** `arc_beats` is derived by reverse lookup from arc beat files.


The value arc tracks whether a value (`Trust`, `Freedom`, etc.) is positively or negatively charged at each structural level. The arc moves from `value_open` to `value_close`:

- **positive → negative**: value degrades (tragedy)
- **negative → positive**: value triumphs (comedy)
- **positive → ironic**: value wins but at great cost
- **negative → mixed**: partial recovery, ambiguous

The arc system compares story-level, act-level, sequence-level, and scene-level arcs to evaluate whether character arcs build toward the right destination.

## Non-Event Scenes

McKee says some scenes don't turn — they're exposition, transition, or setup with no value shift. These are valid (sometimes necessary) but structurally weak. Use `dramatic_role: non-event` and leave `value_open`/`value_close` empty. The future structure system can flag them ("this sequence has three non-events in a row") without the data model breaking.

---

## Scene Numbering

- `id` is **sequential** (1, 2, 3...), regenerated on each index update
- `number` mirrors `id` (both are sequential; kept for compatibility)
- Cross-references use **scene headings** (not numbers) for stability

---

## Relationship Representation

Relationships are **unidirectional** — each character lists their own in frontmatter:

```yaml
# characters/some-character.md
related:
  - id: other-character
    label: Partner
    feeling: Wary respect
```

The index does **not** store relationships — they live in the note frontmatter only.

---

## Story Memory

The index does **not** store story memory. It lives in `.story/memory.md` as plain Markdown.
