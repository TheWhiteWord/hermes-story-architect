# SKILL.md — Structure Draft

> Section-level outline. No content yet — just what each section holds and why.

---

## Frontmatter

- **name**: skill identifier
- **description**: what this plugin does + when to trigger (must be self-contained — this is the only thing the agent sees before choosing to load the skill)

---

## Section 1: Purpose

- One-paragraph description of the plugin
- Assumptions: user is mid-project, has entities, wants to edit/answer
- Does NOT explain what stories are, what characters are, etc.

## Section 2: Quick Start (The Common Case)

- The 4-step pattern that happens 80% of the time — written as a **Markdown checklist** (the guide mandates checklists for >3 sequential steps; the agent copies this into working notes):
  ```
  - [ ] Load project (always first)
  - [ ] Read index (what entities/sections are available)
  - [ ] Retrieve targeted sections
  - [ ] Answer or propose edit
  ```

- Concrete tool call sequence for the common path
- What "loaded" looks like (the agent now sees index + memory)

## Section 3: Standard Sections (Compact Table)

- Entity type → list of standard `##` sections (one row each)
- This is ALL the agent needs for 90% of retrieval decisions — no reason to load schemas.md
- Grouped by entity type, concise format

## Section 4: Frontmatter → Body Mapping

- The core architectural concept: frontmatter = labels/summaries, body = detailed prose
- Why this matters for retrieval (target by section name from index)
- Terminal fields vs. mapped fields (which fields have body counterparts)

## Section 5: Decision Tree

- "If user wants to..." branches:
  - Create entity → `story_create` + when to use `story_describe` for field discovery
  - Edit entity → action protocol pointer
  - Answer question → retrieve sections
  - Search → `story_search` + retrieve pattern
  - Show dashboard → `story_dashboard`

- Each branch: the ONE reference file to open next

## Section 6: Pointers to References

- One line per file: what it contains + when to open it
- `story_describe` mentioned here as the primary schema discovery tool (schemas.md is fallback)
- Format: "If you need X, read Y"

---

## What This Structure Skips

- Full field schemas → `references/operational/schemas.md` (tool is primary)
- Action protocol details → `references/operational/action-protocol.md`
- Value/plot theory → `references/theory/`
- Screenplay formatting → `references/screenplay.md`
- Code samples → in references or examples, not here
