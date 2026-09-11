# Index Format Reference

> Full YAML schema for `.story/index.yaml` — the always-loaded project graph.
> Field names match the code exactly. Descriptions are minimal.

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

characters:
  - id: character-slug
    name: Character Name
    story_role: Protagonist
    one_sentence: Short description
    sections: [Personality, Background, Voice, Arc, Relationships, Goals]
    scenes:
      - number: 1
        heading: INT. LOCATION - DAY

locations:
  - id: location-slug
    name: Location Name
    one_sentence: Short description
    sections: [Description, History, Scenes]
    scenes:
      - number: 1
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
      - scene: INT. LOCATION - DAY
        description: What happens at this beat
    payoffs:
      - scene: INT. LOCATION - NIGHT
        description: Resolution
    sections: [Summary, Obstacles, Stakes]

scenes:
  - id: 1
    heading: INT. LOCATION - DAY
    number: 1
    characters: [character-slug]
    location: location-slug
```

---

## Field Descriptions

### Project
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug (from folder name) |
| `name` | string | Display name |
| `logline` | string | One-sentence summary |
| `genre` | string | Story genre |
| `setting` | string | Primary setting |
| `status` | string | active/abandoned/archived |
| `sections` | string[] | Available `##` headings |
| `scene_count` | number | Derived from screenplay |
| `character_count` | number | Derived from notes |
| `location_count` | number | Derived from notes |
| `world_count` | number | Derived from notes |
| `plot_count` | number | Derived from notes |

### Character
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug (from filename) |
| `name` | string | Display name |
| `story_role` | string | Protagonist/Antagonist/Supporting/Minor/Cameo |
| `one_sentence` | string | Index label |
| `sections` | string[] | Available `##` headings |
| `scenes` | object[] | Scene references: `number` + `heading` |
| `relationships` | object[] | Relationships: `id` + `label` + `feeling` |
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
| `scenes` | object[] | Scene references: `number` + `heading` |

### World
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug |
| `name` | string | Display name |
| `one_sentence` | string | Index label |
| `sections` | string[] | Available `##` headings |
| `rules` | string[] | World rules (from frontmatter) |

### Plot
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Slug |
| `name` | string | Display name |
| `one_sentence` | string | Index label |
| `status` | string | active/resolved/abandoned |
| `characters` | string[] | Character slugs (frontmatter-only) |
| `setups` | object[] | Beats where plot is established: `scene` (heading) + `description` |
| `payoffs` | object[] | Beats where plot resolves: `scene` (heading) + `description` |
| `sections` | string[] | Available `##` headings |

### Scene
| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Sequential (regenerated on each index update) |
| `heading` | string | Fountain heading |
| `number` | number | Sequential (from screenplay order) |
| `characters` | string[] | Character slugs |
| `location` | string | Location slug |

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
