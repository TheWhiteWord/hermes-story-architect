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
      - heading: INT. LOCATION - DAY
        number: 2
        description: What happens at this scene
    payoffs:
      - heading: INT. LOCATION - NIGHT
        number: 8
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
| `status` | string | One of: active, resolved, abandoned | frontmatter |
| `characters` | string[] | Character slugs (frontmatter-only) | frontmatter |
| `setups` | object[] | Scenes where plot is established: `heading` + `number` (id) + `description` | frontmatter |
| `payoffs` | object[] | Scenes where plot resolves: `heading` + `number` (id) + `description` | frontmatter |
| `sections` | string[] | Available `##` headings | code |

### Scene
> **Derived from screenplay** — scenes are extracted from `screenplay.fountain`, not from notes. No scene notes exist.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | number | Sequential (regenerated on each index update) | code |
| `heading` | string | Fountain heading | code |
| `number` | number | Sequential (from screenplay order) | code |
| `characters` | string[] | Character slugs (matched from screenplay) | code |
| `location` | string | Location slug (matched from screenplay) | code |
| `plots` | string[] | Plot slugs (from plot setups/payoffs reverse lookup) | code |

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
