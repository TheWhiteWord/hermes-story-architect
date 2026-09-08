---
name: story-loader
description: "Load a story project's index and memory into context."
version: 0.1.0
author: Davide, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [story, loading, project, index]
    related_skills: [story-editor]
---

# Story Loader Skill

Loads a story project's index and memory into the LLM context. Read-only — does
not edit anything. Works with any story project in the configured vault.

## When to Use

- "load project <slug or name>"
- "open story <name>"
- "switch to project <slug>"

Don't use for: editing (use story-editor), searching across projects (use
story_search), creating projects (use story_create).

## Prerequisites

- Story vault configured (Hermes plugin config: `story_architect.vault_path`)
- Project exists at `<vault>/projects/<slug>/`
- Index generated (`.story/index.yaml`) — run `story_index` if missing

## Creating a New Project

1. Create the project folder: `mkdir -p <vault>/projects/<slug>/`
2. Run `story_index` with the project slug — this auto-creates:
   - `project.md` (minimal frontmatter with name)
   - `.story/memory.md` (empty)
   - `.story/index.yaml` (initial index)
3. The project is now ready for entity creation via `story_create`

## Procedure

1. **Resolve project**: match user input to a project folder
   - Try exact slug match first: `<vault>/projects/<input>/`
   - Try fuzzy match on slug + project name (rapidfuzz, threshold 40)
   - If multiple matches: list them, ask user to pick
   - If no match: suggest similar, then list all available projects

2. **Read index**: `read_file(<project>/.story/index.yaml)` into context

3. **Read memory**: `read_file(<project>/.story/memory.md)` into context

4. **Confirm**: report loaded project:
   ```
   Loaded <name> — <scenes> scenes, <characters> characters, <locations> locations, <plots> plots.
   Logline: <logline>
   ```

## Quick Reference

- Vault: `<vault>/projects/<slug>/`
- Index: `.story/index.yaml` (always-loaded graph)
- Memory: `.story/memory.md` (continuity map)
- Match: fuzzy on slug + name, threshold 40

## Pitfalls

- **Multiple matches**: list matches, don't guess
- **Missing index**: run `story_index` first, then retry
- **Malformed index**: warn but continue with valid sections
- **No memory file**: not required; skip if absent

## Verification

- Confirm: "Loaded <name> — <scenes> scenes, <characters> characters, <plots> plots."
- Cross-check counts match index top-level fields
