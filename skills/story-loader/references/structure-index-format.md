# Structure Index Format Reference

> Full YAML schema for `.story/structure-index.yaml` — the dramatic metadata sidecar.
> Loaded lazily via `story_load` with `structure_only: true`.
> Field names match the code exactly. Descriptions are minimal.

---

## Top-Level Structure

```yaml
story:
  id: story
  value: Value at stake for the whole story
  value_open: One of: positive, negative, mixed, ironic
  value_close: One of: positive, negative, mixed, ironic
  spine: Protagonist's desire (story-level)
  controlling_idea: The story's argument
  inciting_incident_scene_id: scene-slug
  story_climax_scene_id: scene-slug
  structure_type: One of: Classical, Miniplot, Antiplot

acts:
  - id: act-slug
    value: Value at stake in this act
    value_open: One of: positive, negative, mixed, ironic
    value_close: One of: positive, negative, mixed, ironic
    climax_scene_id: scene-slug  # Scene where this act's major reversal lands

sequences:
  - id: sequence-slug
    value: Value at stake in this sequence
    value_open: One of: positive, negative, mixed, ironic
    value_close: One of: positive, negative, mixed, ironic
    climax_scene_id: scene-slug  # Scene where this sequence's reversal lands

scenes:
  - id: scene-slug
    value: Value at stake in this scene
    value_open: One of: positive, negative, mixed, ironic
    value_close: One of: positive, negative, mixed, ironic
    conflict_levels:
      - inner
      - personal
      - extra-personal
    dramatic_role: One of: setup, complication, crisis, climax, resolution, transition, non-event
    is_inciting_incident: false
    is_sequence_climax: false
    is_act_climax: false
    is_story_climax: false
    arc_beat_refs: []
```

---

## Field Descriptions

### Story
> Story-level dramatic metadata. All fields are optional (default to empty).

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Always `"story"` | code |
| `value` | string | Value at stake for the whole story (e.g. `"Trust"`) | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `spine` | string | Protagonist's core desire driving the whole story | frontmatter |
| `controlling_idea` | string | The story's argument — how and why life changes | frontmatter |
| `inciting_incident_scene_id` | string | Scene slug of the inciting incident | frontmatter |
| `story_climax_scene_id` | string | Scene slug of the story's climax | frontmatter |
| `structure_type` | string | One of: `Classical`, `Miniplot`, `Antiplot` | frontmatter |

### Act

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Stable slug | frontmatter |
| `value` | string | Value at stake in this act | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `climax_scene_id` | string | Scene slug where this act's major reversal lands | frontmatter |

### Sequence

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Stable slug | frontmatter |
| `value` | string | Value at stake in this sequence | frontmatter |
| `value_open` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `value_close` | string | One of: `positive`, `negative`, `mixed`, `ironic` | frontmatter |
| `climax_scene_id` | string | Scene slug where this sequence's reversal lands | frontmatter |

### Scene

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `id` | string | Dramatic-function slug (e.g. `mara-discovers-files`) | frontmatter |
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

---

## Value Arc System

The value arc tracks whether a value (`Trust`, `Freedom`, etc.) is positively or negatively charged at each structural level. The arc moves from `value_open` to `value_close`:

- **positive → negative**: value degrades (tragedy)
- **negative → positive**: value triumphs (comedy)
- **positive → ironic**: value wins but at great cost
- **negative → mixed**: partial recovery, ambiguous

The arc system compares story-level, act-level, sequence-level, and scene-level arcs to evaluate whether character arcs build toward the right destination.
