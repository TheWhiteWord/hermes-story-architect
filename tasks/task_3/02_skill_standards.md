# Subtask: Skill Authoring Standards — RESOLVED

> Verify our skill structure follows Hermes skill authoring standards. References: `hermes-agent-skill-authoring` skill, `hermes-plugin-development` skill.

---

## Key Clarification

The user listed `/conventions/` as a skill subdirectory, but **Hermes skills do NOT have a `conventions/` subfolder**. Conventions are a vault-level concept — they live in the vault (`.vault/conventions.md`), not in the skill directory. Skills have:

```
<skill>/
├── SKILL.md              # required
├── references/           # optional — detailed docs
├── templates/            # optional — document templates
└── scripts/              # optional — Python helpers
```

The confusion comes from `obsidian-vault` which teaches you about conventions but stores a template in `templates/vault-conventions.md` that gets copied TO the vault.

---

## Decisions

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Skill subdirectory | `references/` only | No scripts needed (built-in tools), no templates needed (no doc generation) |
| 2 | `related_skills` | `[story-editor]` | Will exist in same plugin |
| 3 | Description length | 53 chars | Under 60-char limit |
| 4 | Author format | `Davide, Hermes Agent` | Human first per hardline rule |
| 5 | Platforms | `[linux, macos, windows]` | Cross-platform (no OS-specific calls) |
| 6 | Skill loading | `skill_view(name="story-loader")` | Tool handler invokes it explicitly |
| 7 | Skill scope | Loading only | Retrieval hints go in story-editor skill |
| 8 | Reference file content | Full schema + example | SKILL.md points to it, keeps main file lean |

---

## Final Skill Structure

```
plugin/skills/story-loader/
├── SKILL.md                        # main skill file
└── references/
    └── index-format.md             # index schema + example
```

**No scripts/** — uses Hermes `read_file` / `search_files`.
**No templates/** — no document generation.
**No conventions/** — conventions are vault-level, not skill-level.

---

## SKILL.md Frontmatter (Final)

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

**Checks**:
- name: lowercase, hyphens, ≤64 chars ✓
- description: 53 chars, one sentence, ends with period ✓
- version: semver ✓
- author: human first, then "Hermes Agent" ✓
- platforms: audited ✓
- related_skills: story-editor will exist in same plugin ✓

---

## SKILL.md Body Structure (Final)

```
# Story Loader Skill
Loads a story project's index and memory into the LLM context. Does not edit
anything — read-only. Works with any story project in the configured vault.

## When to Use
- "load project <slug>"
- "open story <name>"
- "switch to project <slug>"
Don't use for: editing (use story-editor), searching across projects (use story_search).

## Prerequisites
- Story vault configured (Hermes plugin config: story_architect.vault_path)
- Project exists at <vault>/projects/<slug>/
- Index generated (.story/index.yaml)

## Procedure
1. Resolve project slug/name to a folder path
2. Read .story/index.yaml into context
3. Read .story/memory.md into context
4. Report loaded project (name, counts, logline)
5. If project not found: suggest similar or list available

## Quick Reference
- Vault: <vault>/projects/<slug>/
- Index: .story/index.yaml (always-loaded graph)
- Memory: .story/memory.md (continuity map)

## Pitfalls
- Multiple projects match: list matches, ask user to pick
- Missing index: run `story_index` first
- Malformed index: warn but continue with valid sections

## Verification
- Confirm: "Loaded <name> — <scenes> scenes, <characters> characters, <plots> plots."
- Cross-check counts match index top-level fields
```

---

## Reference File: `references/index-format.md`

**Content**:
- Full YAML schema for `.story/index.yaml`
- Field-by-field descriptions (what each field means, what the index uses it for)
- Complete example index
- Scene numbering rules (sequential `id` + screenplay-tools `scene_number`)
- Relationship representation (unidirectional, plain slugs)
- Story Memory section (summary-only, full content in `.story/memory.md`)

**Why separate**: SKILL.md targets ~100-200 lines. Schema details are bulk that would bloat it. SKILL.md points to this file: "For full schema, see `references/index-format.md`."

---

## Skill-Tool Integration

**Pattern**: Tool = the "what" (registration, schema). Skill = the "how" (procedure, rules).

**Flow**:
1. User says "load project the-water-audit"
2. Agent invokes `story_load(project="the-water-audit")` tool
3. Tool handler:
   - Calls `skill_view(name="story-loader")` to load SKILL.md into context
   - Executes the Procedure from SKILL.md
   - Returns JSON result (loaded project data + confirmation)

**Why this pattern**:
- Skill guides LLM behavior (process predictability)
- Tool provides the schema/API contract
- Separating them keeps the tool handler thin and the skill focused on process

---

## What this means for 01_story_loader.md

- Structure is confirmed
- Frontmatter is finalized
- Body outline is set
- Reference file scope is defined
- Skill-tool integration pattern is chosen

---

## Status: RESOLVED
