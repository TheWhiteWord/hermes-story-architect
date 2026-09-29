---
name: hermes-story-architect
description: "Use when co-writing a story: characters, structure, prose."
version: 0.1.0
author: TWW
license: MIT
metadata:
  hermes:
    tags: [writing, story, creative, database]
    related_skills: []
---

# Story Architect

*Schematic draft — headings and notes only.*

## When to Use

*Reach for this skill when the user is writing a story in this plugin: asking
about a character, an arc, a structure, a scene, or a place, and the answer
belongs in the project rather than in a chat message.*

A structured store for a story, and eleven tools that read and write it. The
human is the author; the agent is the one holding the structure.

**The governing idea.** A story in progress is a set of decisions, not a
document. Some decisions belong in fields, where they are queryable and can be
contradicted later; some belong in sections, where they are free prose that
explains itself. Both are the same kind of writing and neither is more
authoritative. → `model/entity-sections.md`

---

## The hard rules

*Short, and true everywhere. Everything else defers to these.*

1. **Never commit a draft the user has not approved.** `story_draft` proposes;
   `story_draft` with `action="commit"` is the user's decision to make. A
   proposal is not a change. → `mechanics/staging-changes.md`
2. **Never invent an id.** Ids are global, permanent, and never renamed. The
   user names them, or they are read from something the user wrote. → `mechanics/ids-and-links.md`
3. **A blank field is a question, not a defect.** Do not fill a field to make
   the store look complete. The unfilled view exists to report, not to be
   silenced. → `model/entity-sections.md`
4. **The database is the source of truth.** The Markdown files are an export of
   it, not a second copy that can be edited. → `mechanics/project-lifecycle.md`

## How a session runs

*Orienting first, every time, is cheaper than any wrong write.*

- **Orient.** `story_load` with nothing else. It returns the structure, the
  project, and the whole story memory in one call — which is also how the agent
  learns what has already been decided. → `mechanics/reading-the-project.md`
- **Then narrow.** A view for the question, `story_retrieve` for the contents.
  Ids from the load are what both take.
- **Then write**, as a proposal. → `mechanics/staging-changes.md`
- **Memory is a separate kind of writing** — a fact about the project that
  outlives the entities, rather than a fact *in* one. Do not infer it from a
  scene. → `model/story-memory.md`

## The tools, in one line each

*Parameters are in the schema. This is only what each one is for.*

| Tool | For |
|---|---|
| `story_describe` | what fields and sections a type has |
| `story_load` | what exists in the project, and one of five views |
| `story_retrieve` | one entity's fields and sections, batched |
| `story_search` | where a term is mentioned, across all prose |
| `story_draft` | propose, then commit, then discard |
| `story_memory` | add, remove or replace a memory entry |
| `story_admin` | create, list, restore, purge, delete a project |
| `story_backup` | copy the database |
| `story_export` | write the database out as Markdown |
| `story_import` | rebuild the database from Markdown — destructive |
| `story_dashboard` | open the visual view for the user |

**`story_describe` is the authority on fields and sections.** It is not to be
duplicated in a reference file; when a field is needed, it is asked for.

---

## References

*One aspect per file, all paths relative to the skill root. Read the one that
matches the task, not the folder.*

### `references/model/` — how the store thinks

*Load these before writing anything. They are the fundamentals.*

| File | Read when |
|---|---|
| `references/model/entity-sections.md` | choosing between a field and a section; what goes in a section |
| `references/model/value-system.md` | the story's value or a character's; the two tracks |
| `references/model/story-memory.md` | recording a decision; resolving a contradiction |

### `references/craft/` — the writing work

*One file per thing being made. The theory counterpart is listed because the
craft file is where the theory becomes a decision.*

| File | Read when | Theory |
|---|---|---|
| `references/craft/project-design.md` | shaping the premise, theme, or premise-vs-theme | — |
| `references/craft/plot-and-structure.md` | acts, sequences, plots, milestones | `references/theory/structure-and-plot.md` |
| `references/craft/character-and-arc.md` | creating or changing a character | `references/theory/character-and-arc.md` |
| `references/craft/character-and-arc/arc-beats.md` | a character's turn, in beats | `references/theory/character-and-arc.md` |
| `references/craft/character-and-arc/relationships.md` | who a character is bonded to | `references/theory/character-and-arc.md` |
| `references/craft/scene-design.md` | a scene's purpose, turn, and dramaturgy | `references/theory/scene-and-beat.md` |
| `references/craft/world-and-place.md` | a world or a location | `references/theory/world-and-place.md` |

### `references/mechanics/` — the tools

*Load these before calling. Most of the mistakes available are mechanical.*

| File | Read when |
|---|---|
| `references/mechanics/reading-the-project.md` | orienting, or choosing between the five views |
| `references/mechanics/staging-changes.md` | writing anything, and what a draft can and cannot do |
| `references/mechanics/ids-and-links.md` | naming an entity, or following a reference |
| `references/mechanics/screenplay-format.md` | writing a scene's `## Content` in Fountain |
| `references/mechanics/screenplay-format/samples/` | a worked example of the above, good and broken |
| `references/mechanics/dashboard.md` | the user asks what the dashboard can do |
| `references/mechanics/project-lifecycle.md` | creating, deleting, backing up, importing, exporting |

### `references/theory/` — why any of this

*Not part of the work. Read when the user asks why, or when a decision needs a
reason rather than a rule.*

| File | About |
|---|---|
| `references/theory/values.md` | what a value is, and what the ±1 means |
| `references/theory/character-and-arc.md` | why a character changes |
| `references/theory/structure-and-plot.md` | why acts and sequences are the units |
| `references/theory/scene-and-beat.md` | what a scene does |
| `references/theory/world-and-place.md` | what a world is for |

---

## Open questions

- [ ] The reference paths are written root-relative, with the `references/`
      prefix, so the linter can validate them — at the cost of a longer table.
      Worth it for the free check, or is the shorter form more readable to the
      agent?
- [ ] The pointer table is 22 rows and the theory column repeats the craft
      table's structure. Worth keeping the pairing explicit, or does the craft
      file link to its theory file and the column go?
- [ ] Rule 2 forbids inventing ids, but the user may want the agent to propose
      one for approval — which is a different thing. Worth distinguishing?
- [ ] `parse_frontmatter` in the linter is line-based and cannot nest, so its
      own `metadata.hermes.tags` check can never pass. The nested block is the
      documented convention and the warning is a false positive. Leave it, or
      flatten to silence it?
- [ ] The `name` must match the directory, so the working copy in
      `tasks/task_30/skill/` lints an error that will not exist at
      `skills/hermes-story-architect/`. Confirm against the real path before
      this goes live.
