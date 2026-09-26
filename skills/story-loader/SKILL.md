---
name: story-loader
description: "Load a story project's index and memory into context. Also use to start new projects."
version: 0.2.0
author: TWW, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [story, loading, project, index]
    related_skills: [story-editor]
---

# Story Loader Skill

Loads a story project's index and memory into the LLM context. Read-only — does
not edit anything. Works with any story project in the configured story root.

## When to Use

- "load project <slug or name>"
- "open story <name>"
- "switch to project <slug>"
- "start a new project"
- "create a story called <name>"

Don't use for: editing (use story-editor), searching across projects (use story_search).

## Prerequisites

- Story root configured (Hermes plugin config: `story_architect.root_path`)
- Project exists at `<root>/projects/<slug>/`
- Project created via `story_create(entity_type='project', ...)` (creates all files)

## Tools Available

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `story_load` | Load project index and memory | `project` (slug or name) |
| `story_index` | Regenerate the project index | `project` |
| `story_create` | Create new entities (including projects) | `entity_type`, `slug`, `project`, `frontmatter` |
| `story_dashboard` | Open the dashboard in preview | `project` |

## Creating a New Project

1. Create the project via `story_create`:
   ```
   story_create(
     entity_type="project",
     slug="<project-slug>",
     project="",
     frontmatter={"name": "Display Name", "logline": "...", ...}
   )
   ```
   This creates:
   - `project.md` with full frontmatter schema (all fields, defaults like "not set")
   - `.story/memory.md` with standard sections (Continuity notes, Character knowledge, World events, Open questions)
   - Entity folders (characters, locations, worlds, plots, scenes, sequences, acts, arcs)
   - `.story/index.yaml` (initial index)
   - Standard body sections (Synopsis, Themes, Structure, Notes)

2. Load the project: `story_load(project="<slug>")`
3. Open dashboard: `story_dashboard(project="<slug>")`

**Required fields:** `name` (only required field; `logline` is optional).

**Default values:** Core fields like `logline`, `genre`, `setting`, `spine`, `value`, `value_at_open`, `value_at_close`, `structure_type`, `controlling_idea`, `inciting_incident_scene_id`, `story_climax_scene_id` default to `"not set"`. Title page fields (`screenplay_title`, `credit`, `author`, `contact`, `draft_date`, `draft`) default to `""`.

## Procedure

1. **Resolve project** — match user input to a project folder
   - Try exact slug match first: `<root>/projects/<input>/`
   - Try fuzzy match on slug + project name (rapidfuzz, threshold 40)
   - If multiple matches: list them, ask user to pick
   - If no match: suggest similar, then list all available projects

2. **Load index** — call `story_load` with `project`. This returns:
   - `index` — navigation graph (entities, cross-references, counts)
   - `project` — project frontmatter (name, logline, genre, status, counts)
   - `memory` — continuity notes from `.story/memory.md`

3. **Confirm** — report loaded project:
   ```
   Loaded <name> — <scenes> scenes, <sequences> sequences, <acts> acts, <characters> characters, <locations> locations, <plots> plots.
   Logline: <logline>
   ```

## Quick Reference

- Root: `<root>/projects/<slug>/`
- Index: `.story/index.yaml` (always-loaded graph)
- Memory: `.story/memory.md` (continuity map)
- Match: fuzzy on slug + name, threshold 40

### Entity Quick Reference

| Entity | Key Frontmatter Fields |
| --- | --- |
| Project | `name`, `logline`, `genre`, `setting`, `status`, `structure_type`, `spine`, `value`, `value_at_open`, `value_at_close` |
| Scene | `id` (dramatic-function slug, e.g. `mara-discovers-files`), `title` (display name), `sequence_id`, `act_id`, `order`, `status`, `characters`, `plots` |
| Sequence | `id`, `title`, `act_id`, `order`, `status`, `climax_scene_id` |
| Act | `id`, `title`, `order`, `status`, `climax_scene_id` |

## Pitfalls

- **Multiple matches**: list matches, don't guess
- **Missing project.md**: use `story_create(entity_type="project")` to create properly
- **Malformed index**: warn but continue with valid sections
- **No memory file**: not required; skip if absent
- **Entity creation**: `story_create` auto-fills all expected fields with schema defaults. Load `references/index-format.md` only if you need the full field list, sub-field structure (e.g. plot setups/payoffs use `{scene_id, description}`), or dramatic metadata fields (value arcs, dramatic roles, climax flags).

## Verification

- Confirm: "Loaded <name> — <scenes> scenes, <characters> characters, <plots> plots."
- Cross-check counts match index top-level fields
