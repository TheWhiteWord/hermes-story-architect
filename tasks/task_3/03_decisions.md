# Task 3: Story Loader Skill — FINAL DECISIONS

> All subtasks resolved. This is the authoritative record of decisions made.

---

## Status: RESOLVED

| Subtask | Status |
|---------|--------|
| 01_story_loader.md | RESOLVED |
| 02_skill_standards.md | RESOLVED |

---

## 1. Skill Structure

```
plugin/skills/story-loader/
├── SKILL.md                        # main skill file
└── references/
    └── index-format.md             # index schema + example
```

**No scripts/** — uses Hermes built-in tools (`read_file`, `search_files`).
**No templates/** — no document generation.
**No conventions/** — conventions are vault-level, not skill-level.

---

## 2. SKILL.md Frontmatter

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

---

## 3. SKILL.md Body

### When to Use
- "load project <slug or name>"
- "open story <name>"
- "switch to project <slug>"

### Procedure
1. Resolve project (exact slug → fuzzy match on slug+name → list matches)
2. Read `.story/index.yaml` into context
3. Read `.story/memory.md` into context
4. Confirm: "Loaded <name> — <scenes> scenes, <characters> characters, <plots> plots."

### Error Handling
| Error | Response |
|-------|----------|
| No match | Suggest similar → list available |
| Multiple matches | List matches, ask user to pick |
| Missing index | Run `story_index` first |
| Malformed index | Warn, continue with valid sections |

---

## 4. Project Discovery

```python
from rapidfuzz import fuzz, process

def resolve_project(user_input: str, vault_path: Path) -> Path:
    # 1. Exact slug match
    # 2. Fuzzy match on slug + project name (threshold 85)
    # 3. No match → suggest similar or list all
```

- Exact slug match first
- Fuzzy match on slug + project name (from `project.md` frontmatter)
- Threshold: 85
- Multiple matches → list, don't guess

---

## 5. Confirmation Format

```
Loaded The Water Audit — 24 scenes, 8 characters, 3 locations, 3 plots.
Logline: A forensic accountant discovers her firm is laundering water-rationing profits for a corporate police state.
```

---

## 6. Multi-Project Handling

**One at a time** — "switch to X" unloads the previous project. Simpler mental model.

---

## 7. Skill-Tool Integration

- `story_load` tool handler calls `skill_view(name="story-loader")`
- Tool handler executes the Procedure from SKILL.md
- Tool returns JSON: `{"loaded": true, "project": {...}, "confirmation": "..."}`
- Reference file loaded on demand via `file_path="references/index-format.md"`

---

## 8. Reference File: `references/index-format.md`

**Content**:
- Full YAML schema for `.story/index.yaml`
- Field-by-field descriptions
- Complete example index
- Scene numbering rules (sequential `id` + screenplay-tools `scene_number`)
- Relationship representation (unidirectional, plain slugs)
- Story Memory section (summary-only)

---

## What happens next

1. Implement `plugin/skills/story-loader/SKILL.md`
2. Implement `plugin/skills/story-loader/references/index-format.md`
3. Implement `plugin/tools/story_load.py` (tool handler)
4. Test with a real project
5. Proceed to **Task 4 (Retrieval Engine)** or **Task 5 (Action Protocol)**
