---
name: hermes-story-architect
description: "Story Architect — manage story projects (characters, locations, plots, scenes, sequences, acts, arcs)."
version: 0.1.0
author: TWW
---

# Story Architect

## Project Entry and Story Memory

- Always call `story_load` before working on a story project. It contains the project structure and current story memory.
- Memory is explicit, bounded, project-level creative guidance stored in the project DB. `.story/memory.md` is only an export projection.
- Use `story_memory` to add, remove, or replace complete entries. Do not silently infer canon from scenes or implications.
- Keep one entry to one rule, fact, direction, question, or warning. Preserve unresolved questions and continuity warnings until the user resolves them.
- Memory is advisory. Authoritative entity data and explicit user decisions take precedence; report conflicts instead of rewriting memory automatically.


- **story_load** = structural map of the whole project. Called once per session or on-demand for views. Returns nested tree.
- **story_retrieve** = entity drill-down. Called many times. Returns flat entity + requested fields/sections.
- Rule: load answers "what exists and where." Retrieve answers "what does this say."

## story_load Views

- `view="arc"` + `character` param — single character arc: character FM + all beat FM, hierarchical
- `view="story_value"` + optional `act` param — value tracking across act→seq→scene
- `view="dramatic_elements"` + optional `act` + `add_plot` (default false) — dramatic_role + milestone per scene, with optional plot cross-refs

## Two value tracks

- The story's value is `story_value` on the project; the character's is `character_value` on the character. Same vocabulary, no derivation between them — a protagonist may arc on a different value from the story's.
- Act, sequence and scene **inherit** the story's value word and charge it per-entity (`value_at_open` / `value_at_close`). Beats inherit the character's and charge theirs (`character_value_at_open` / `_close`).
- A scene does not get a value word of its own. A second theme there is a character value, or a `plot` concern.
- `references/story-value-vs-character-value.md` — the field table, and why there is no continuity check.

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
