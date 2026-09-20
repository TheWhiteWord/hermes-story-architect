---
name: hermes-story-architect
description: "Story Architect — manage story projects (characters, locations, plots, scenes, sequences, acts, arcs)."
version: 0.1.0
author: TWW
---

# Story Architect

## Tool Boundary

- **story_load** = structural map of the whole project. Called once per session or on-demand for views. Returns nested tree.
- **story_retrieve** = entity drill-down. Called many times. Returns flat entity + requested fields/sections.
- Rule: load answers "what exists and where." Retrieve answers "what does this say."

## story_load Views

- `view="arc"` + `character` param — single character arc: character FM + all beat FM, hierarchical
- `view="story_value"` + optional `act` param — value tracking across act→seq→scene
- `view="dramatic_elements"` + optional `act` + `add_plot` (default false) — dramatic_role + milestone per scene, with optional plot cross-refs

## story_retrieve

- Uses `refs` (list of entity keys from load output), not single `slug`. Batch by default.
- `fields` and `sections` are composable in one call.
- No field grouping — agent requests exactly what it wants.
- `fields=["all"]` returns all FM; `sections=["all"]` returns all sections.

## Naming Conventions

- Scene markers use `milestone` field with full-word values: `"inciting incident"`, `"sequence climax"`, `"act climax"`, `"story climax"`. NOT `climax: "inciting"`.
- All entities share `id` as DB PK, but JSON output uses different display keys: `name` for character/location/world/plot/project; `id` + `title` for scene/sequence/act/arc.

## Boolean Markers

- Omit FALSE values. Only emit TRUE. Applies to: `is_crisis`, `is_climax`, `is_inciting_incident`, `is_sequence_climax`, `is_act_climax`, `is_story_climax`, plot structural roles (setups/crisis/climax/payoffs).

## Pitfalls

- Don't merge load and retrieve into one tool with a mode parameter — two tools with clear names is simpler than one tool the agent has to switch modes on.
- Don't add field grouping (auto-expanding requested fields to semantic groups) — overcomplication. Agent names what it wants.
- Don't include plot cross-references by default in dramatic_elements — opt-in via `add_plot=true` keeps the base view lean.
- Don't use `slug` for retrieve — use `refs` (list) to support batch entity selection.
- Don't emit `climax: "inciting"` or `climax: "seq"` — use `milestone: "inciting incident"` and `milestone: "sequence climax"`.
