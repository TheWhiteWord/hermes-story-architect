# Subtask: Story Loader Skill — RESOLVED

> Design the skill that loads a project's context into the LLM. References: `task_1/04_decisions.md` (vault structure), `task_2/04_decisions.md` (index schema), `task_3/02_skill_standards.md` (skill standards).

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Project discovery | Fuzzy match on slug + name | `rapidfuzz` for typo tolerance |
| 2 | Multi-project | One at a time | Simpler mental model; "switch to X" unloads previous |
| 3 | Confirmation detail | Name + logline + counts | Enough to confirm without bloating context |
| 4 | Error on not found | Suggest similar (fuzzy) → list available | Helps user recover from typos |

---

## Final SKILL.md

```yaml
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
```

```markdown
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

## Procedure

1. **Resolve project**: match user input to a project folder
   - Try exact slug match first: `<vault>/projects/<input>/`
   - Try fuzzy match on slug + project name (rapidfuzz, threshold 85)
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
- Match: fuzzy on slug + name, threshold 85

## Pitfalls

- **Multiple matches**: list matches, don't guess
- **Missing index**: run `story_index` first, then retry
- **Malformed index**: warn but continue with valid sections
- **No memory file**: not required; skip if absent

## Verification

- Confirm: "Loaded <name> — <scenes> scenes, <characters> characters, <plots> plots."
- Cross-check counts match index top-level fields
```

---

## Reference File: `references/index-format.md`

**Content**:
- Full YAML schema for `.story/index.yaml`
- Field-by-field descriptions
- Complete example index
- Scene numbering rules
- Relationship representation
- Story Memory section

**Why separate**: SKILL.md targets ~100-200 lines. Schema details are bulk.

---

## Project Discovery Algorithm

```python
from rapidfuzz import fuzz, process
from pathlib import Path

def resolve_project(user_input: str, vault_path: Path) -> Path:
    """Resolve user input to a project folder path."""
    projects_dir = vault_path / "projects"
    
    # 1. Exact slug match
    exact = projects_dir / user_input
    if exact.is_dir():
        return exact
    
    # 2. Fuzzy match on slug + project name
    candidates = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        # Match on slug
        candidates.append((project_dir.name, project_dir))
        # Match on project name (from project.md frontmatter)
        project_md = project_dir / "project.md"
        if project_md.exists():
            import frontmatter
            post = frontmatter.load(project_md)
            if "name" in post.metadata:
                candidates.append((post.metadata["name"], project_dir))
    
    # Fuzzy match
    names = [c[0] for c in candidates]
    result = process.extractOne(user_input, names, scorer=fuzz.WRatio)
    
    if result and result[1] >= 85:
        matched_name = result[0]
        # Find the path for this name
        for name, path in candidates:
            if name == matched_name:
                return path
    
    # 3. No match — suggest similar or list all
    raise ProjectNotFoundError(user_input, [c[0] for c in candidates])
```

---

## Confirmation Format

```
Loaded The Water Audit — 24 scenes, 8 characters, 3 locations, 3 plots.
Logline: A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.
```

**Why this format**:
- Name + counts = quick verification
- Logline = context reminder
- Not too long (~3-4 lines)

---

## Error Handling

| Error | Response |
|-------|----------|
| No match | "No project matching '<input>'. Did you mean <similar>?" |
| Multiple matches | "Multiple matches: <list>. Which one?" |
| Missing index | "No index found. Run `story_index` first." |
| Malformed index | "Warning: index has errors. Loaded valid sections." |
| No memory | Skip silently (not required) |

---

## What this means for implementation

- `story_load` tool handler calls `skill_view(name="story-loader")`
- Tool handler executes the Procedure from SKILL.md
- Tool returns JSON: `{"loaded": true, "project": {...}, "confirmation": "..."}`
- Reference file loaded on demand: `skill_view(name="story-loader", file_path="references/index-format.md")`

---

## Status: RESOLVED
