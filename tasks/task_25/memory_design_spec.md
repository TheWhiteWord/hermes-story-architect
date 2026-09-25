# Story Memory — Hermes-lite design spec

**Status:** Draft design for progressive refinement. No implementation is implied until this spec is accepted.

**Scope:** A small, curated, project-level memory sidecar for Story Architect. It is modelled on Hermes Agent's built-in memory, but its semantics are creative guidance for future story work — not a continuity engine, not a canon database, and not a full state-tracking system.

**Explicitly out of scope for v1:**

- full continuity tracking;
- temporal entity-state modelling;
- automatic extraction of canon from scenes;
- automatic promotion/demotion between memory tiers;
- confidence scoring;
- memory per entity;
- a new retrieval or indexing system;
- automatic memory-driven story repair.

---

## 1. Purpose

Story Architect needs a persistent place for a small number of durable, cross-entity facts and creative constraints that materially affect future story work.

Memory should answer:

> What must the writer keep in mind when working on this project that is not already captured by the project structure or by a single entity?

It should not attempt to remember everything that happened in the story.

## 2. Design decisions

**Adopt Readaptation 1: Hermes-lite.**

The implementation remains:

```text
.story/memory.md
```

The file stays user-facing and human-editable.

**Storage representation:** frontmatter only for the v1 memory content. The file contains no Markdown body.

Conceptually:

```yaml
---
decisions:
  - "The mystery is not resolved before the midpoint."
directions:
  - "Explore the Mara–Victor alliance through professional obligation."
open_questions:
  - "Whether Victor altered the ledger remains unresolved."
continuity_warnings:
  - "The ferry departure time is inconsistent between the harbour scene and the Act 3 outline."
---
```

These four categories are the confirmed v1 functional categorization:

- `decisions` — durable authorial constraints;
- `directions` — current creative intent that is not yet a hard decision;
- `open_questions` — deliberate uncertainty that must not be silently resolved;
- `continuity_warnings` — known continuity risks that must be surfaced, not silently repaired.

Entries remain plain strings. No IDs, numbering, types, statuses, sources, confidence values, or automatic lifecycle fields are introduced in v1.

Entries are ordered, with newer entries appended last, but order is not treated as a history or identity mechanism. Operations target a complete entry within a category. Exact duplicate entries are rejected.

**Storage authority:** the project DB is authoritative for story memory. `.story/memory.md` is a user-facing projection/export, not an application read source.

The memory payload lives in the project entity's `extra` JSON under `memory`, with the four confirmed arrays. The file is generated from the DB by `story_export`; the application does not read memory from the file for normal operations.

**Read exposure:** `story_load` returns the current bounded memory block, not only an outline.

**Write interface:** memory has a dedicated `story_memory` tool. It is not an alias for `story_edit`, because memory is advisory and semantically different from authoritative entity data.

**Limit:** a fixed implementation constant of **3,000 serialized frontmatter characters**, not user configuration. This is a practical v1 ceiling for roughly 8–12 useful entries across all four categories. The budget is counted over the serialized frontmatter, not the Markdown wrapper.

**Per-entry limit:** a single memory entry may be at most **300 characters**. This prevents one verbose entry from crowding out the rest of memory. The tool rejects an overlong entry and asks the model to express it in its shortest accurate form. It does not automatically split an entry.

**Category distribution:** no hard per-category quota. The four categories have different natural volumes, so equal quotas would be arbitrary. The tool returns per-category counts with usage, and the agent should keep memory balanced by purpose rather than letting one category crowd out the others unless the story genuinely requires it.

## 3. Exposure model

Hermes memory is injected into the system prompt on every request. Story Architect memory is not.

```text
Hermes:
  system prompt → memory visible every request

Story Architect:
  story_load → memory visible once at project start
  conversation → memory remains in context until compaction/session end
```

Consequences:

- the agent must call `story_load` before beginning work on a project;
- the agent only becomes aware that memory exists when `story_load` exposes it;
- memory is not a reminder injected on every turn;
- after context loss or a new session, `story_load` must be called again to restore it.

The Story Architect skill must make the project-entry sequence explicit:

> Always call `story_load` before working on a story project. It contains the project structure and story memory.

`story_load` should label the memory clearly in its response so the agent understands that it is project context, not an unrelated file listing.

## 4. Ownership rule

> Memory stores information that cannot be reliably recovered from a single entity, scene, or relationship, but that materially affects future story work.

If information belongs cleanly in one place, it belongs there — not in memory.

### Examples that belong in memory

- a fact established across multiple characters or scenes;
- a deliberate unresolved question;
- a continuity warning that affects several parts of the story;
- a stable creative rule or constraint that governs the project;
- an intentional ambiguity that must not be accidentally resolved.

### Examples that do not belong in memory

- a character's eye colour → the character entity;
- a scene's location → the scene entity;
- an act title → the act entity;
- a character relationship → the relationship entity;
- a plot structure fact → the plot entity;
- a database relation → the DB;
- a completed-work log or session transcript → history/session record.

## 5. Core principle

> If a fact is not important enough to occupy the deliberately small memory budget, it does not belong in story memory.

Memory is selective. It is not a complete record of the project.

A hard size limit is intentional. It forces a decision about what deserves to survive across sessions. A memory system that can grow without bound will eventually dilute the context it is meant to improve.

The exact character budget remains an open implementation decision, but the budget must be enforced rather than advisory.

## 6. Memory file format

Keep the existing file location and a human-readable Markdown file.

For v1:

- memory entries live in frontmatter values;
- the file contains no Markdown body;
- no custom Markdown section parser is required for memory.

The frontmatter representation should reuse the plugin's existing frontmatter conventions and the project import/export path. The goal is to reuse established structured-data machinery rather than invent a second memory parser.

The confirmed key names are `decisions`, `directions`, `open_questions`, and `continuity_warnings`. Entries are plain strings. Do not add IDs, types, statuses, sources, or confidence fields speculatively.

## 7. Write rules

> A memory write is a deliberate creative decision, not an automatic side effect of editing.

The agent may propose a memory change, but it must not silently add inferred canon.

### Allowed

- record a fact explicitly established by the user or the project;
- record a user-confirmed interpretation of an existing scene;
- record a deliberate unresolved question;
- record a known continuity warning;
- record a stable creative rule;
- remove or rewrite an entry that is no longer accurate.

### Not allowed in v1

- infer a character's knowledge from tone or implication;
- infer a psychological state from dialogue;
- infer object movement or location state without explicit confirmation;
- automatically record every scene event;
- silently delete or rewrite continuity information.

The operative rule is:

> Automatic memory may draft a proposal. It must not silently create canon.

## 8. Read rules

> `story_load` exposes the current bounded memory once at project start; it is not injected into every request.

The returned memory should be complete enough for the agent to use directly. Because the store is intentionally bounded, the system should show the whole memory rather than an outline that requires another retrieval decision immediately after loading the project.

The memory file is not a substitute for entity retrieval. If the answer belongs to a character, scene, plot, or relationship, retrieve that entity.

## 9. Dedicated memory tool

Memory must not be written through the general authoritative-data editing surface.

A dedicated tool preserves the semantic boundary:

```text
story_load    → read project structure and memory
story_edit    → authoritative entity and structure edits
story_memory  → advisory memory mutations
```

The tool's v1 operation set is:

```text
add(category, entry)
remove(category, entry)
replace(category, old_entry, new_entry)
```

`add` appends a new entry to the selected category. `remove` deletes the complete entry from the selected category. `replace` replaces the complete matching entry. Operations do not accept an entry number; targeting is by full entry text within the category.

No automatic promotion, automatic demotion, or automatic deletion belongs in v1.

### Response contract

Successful operations return a compact confirmation:

```json
{
  "success": true,
  "operation": "add",
  "category": "decisions",
  "entry": "The mystery is not resolved before the midpoint.",
  "usage": "312/3000"
}
```

`replace` returns the replacement entry; `remove` returns no entry value. The response does not echo the complete memory.

Rejected operations return a compact error with the reason, current usage, and the inventory of the affected category:

```json
{
  "success": false,
  "error": "Memory is full.",
  "usage": "2980/3000",
  "category": "decisions",
  "current_entries": [
    "The mystery is not resolved before the midpoint.",
    "The ending preserves Daniel's death as genuinely irreversible."
  ],
  "action_required": "Replace, merge, or drop an existing entry before retrying."
}
```

This is enough for the model to make the next decision without flooding the context with the entire memory file.

The tool must enforce the character budget and return current usage.

## 10. Editing and replacement rules

> Memory is bounded, so adding an entry may require replacing a less important one.

The tool does not decide which memory is more important. When an add would exceed the budget, it rejects the write and tells the model exactly what decision is required.

The model must consider, in order:

- whether the new memory is more important than an existing entry;
- whether the new memory can be integrated into an existing entry;
- whether several existing entries can be merged into one shorter entry;
- whether the new memory is not important enough to keep;
- whether the new memory can be simplified to its shortest accurate form.

The tool only enforces the character budget. Importance, integration, replacement, and summarization are model decisions.

No automatic eviction policy is required.

Recommended policy:

- routine, clearly supported memory operations may be applied directly;
- confirmation is reserved for absolutely critical operations, especially destroying a durable decision or resolving a contradiction;
- when an operation is ambiguous, destructive, or changes a user-established rule, ask before applying it;
- do not ask for confirmation for routine add/remove/replace work solely because the system is being cautious;
- a future UI can expose the current memory and changes for verification and self-assurance.

The point of the instruction is to make the model capable of maintaining memory without constant user interruption, not to remove the user's authority over critical creative decisions.

## 11. Relationship to other Story Architect data

Memory is supplementary. It must not become a shadow database.

| Information | Authoritative home |
|---|---|
| Entity description and traits | Entity note / DB |
| Entity relationships | `relations` |
| Scene content | Scene note / DB |
| Structural position and counts | DB / `story_load` |
| Project metadata | Project entity |
| Durable cross-entity creative guidance | Project DB / `project.extra.memory` |
| User-facing memory export | `.story/memory.md` |
| Prior conversation history | Session history, not `.story/memory.md` |

> Memory is a small project-level context, not a second representation of project data.

> The DB is authoritative for story memory. `.story/memory.md` is a human-facing export/projection, not an application read source.

## 12. Agent-facing rules

These rules are intended to become the basis of the plugin skill documentation later.

> Always call `story_load` before working on a story project. It contains the project structure and story memory.

> Memory stores information that cannot be reliably recovered from a single entity, scene, or relationship, but that materially affects future story work.

> If a fact is not important enough to occupy the deliberately small memory budget, it does not belong in story memory.

> Keep memory balanced by purpose. Do not let one category crowd out the others unless the story genuinely requires it.

> A memory entry must be compact: one entry expresses one rule, fact, direction, question, or warning.

> Persistent memory contains only facts and creative constraints that remain relevant beyond the current working session.

> Automatic memory may draft a proposal. It must not silently create canon.

> A character may know something, believe something, or misbelieve something. Preserve that distinction unless the user explicitly resolves it.

> An unresolved question is valid memory. Do not invent an answer merely because a continuation needs one.

> A continuity warning is not a request to silently fix the story. Surface it and let the user decide.

> Memory is advisory. It is never a replacement for authoritative project data.

> `story_load` exposes the current bounded memory once; it is not injected into every request.

> Do not use memory as a substitute for entity retrieval. Retrieve the entity when the question belongs to the entity.

> Do not add a fact to memory merely because it appeared in a scene. Add it when it is established, deliberately unresolved, or explicitly confirmed as important for future work.

> When a memory entry conflicts with the authoritative entity data, do not merge them silently. Report the conflict.

## 13. Failure and conflict handling

Memory is advisory. It is never a replacement for authoritative project data.

When memory conflicts with an entity or scene:

1. treat the entity/scene data as authoritative for the entity's current definition;
2. do not rewrite the entity automatically;
3. surface the conflict to the user;
4. let the user decide whether the memory entry is stale, the entity is stale, or the story intentionally contains a contradiction.

When memory is internally contradictory, preserve the conflict until the user resolves it.

## 14. Explicit non-goals

These are rejected for v1:

- a full continuity engine;
- per-entity state tracking;
- automatic fact extraction from scenes;
- automatic promotion/demotion;
- confidence scores;
- a separate memory database;
- a memory file per entity;
- automatic deletion of stale entries;
- a truth/canon validator;
- automatic inference of character knowledge or psychology.

## 15. Current implementation surface

The current implementation already has most of the required read/write surface.

Expected v1 behaviour after the design is accepted:

- `story_create` ensures the DB project record has the initial memory arrays;
- `story_load` returns a full bounded `memory` block sourced from the DB;
- `story_memory` mutates `project.extra.memory` in the DB;
- `story_dashboard` includes DB memory in its injected payload for the read-only popup;
- `story_export` projects the DB memory into user-facing frontmatter-only `.story/memory.md`;
- the file remains plain Markdown and human-editable;
- existing frontmatter parsing/serialization is reused for export where possible;
- no custom Markdown memory parser is introduced;
- the DB is the source of truth for memory; `.story/memory.md` is a projection/export.

Likely implementation work:

1. add the DB memory structure and initial arrays;
2. replace `memory_outline` with a bounded memory block in `story_load`;
3. add and register `story_memory` against the DB;
4. include memory in the dashboard payload and add the read-only popup;
5. add memory projection to `story_export`;
6. document the project-entry and memory rules in the Story Architect skill;
7. add focused tests for DB memory creation, loading, budget enforcement, add/remove/replace, dashboard injection, and export;
8. remove obsolete placeholder wording once the design is accepted.

## 16. Dashboard UI

The dashboard exposes memory through a small, closable informational dialog. It is intentionally not a full view, panel, or editor.

### Placement

Add a **Memory** utility action to the sidebar immediately above the existing Refresh action. It is not a navigation view and does not replace the current view.

The collapsed sidebar shows a distinct memory/bookmark-style icon with the tooltip/label `Memory`. The expanded sidebar shows the label `Memory`.

The icon and styling reuse the existing sidebar/button/icon language wherever possible.

### Data source

The dialog reads memory from the existing DB-derived dashboard payload:

```text
get_dashboard_data(project_path)
  → story_data.story_memory
  → DASH.story.story_memory
  → memory dialog
```

The dialog must not fetch or parse `.story/memory.md` directly. The DB is authoritative; the Markdown file is a human-facing export/projection.

### Dialog character

Use a compact About-style dialog:

- approximately 380–440px wide on the normal desktop layout;
- compact enough not to obscure the current dashboard view;
- centered over the dashboard or anchored near the sidebar action;
- max-height with internal scrolling when entries exceed the available space;
- a visible close button;
- Escape and backdrop click close it;
- no navigation change and no layout reflow when opened.

The dialog should feel like the app's existing informational surfaces, not a new full-screen feature. Reuse existing tokens (`var(--card)`, `var(--border)`, `var(--foreground)`, `var(--muted-foreground)`, `var(--accent)`, `--radius`) and existing button/icon styles.

### Dialog content

The dialog displays:

- the title `Story Memory`;
- overall usage in the form `x/3000` serialized frontmatter characters;
- a simple total-usage bar;
- the four categories in fixed order:
  1. `decisions`
  2. `directions`
  3. `open_questions`
  4. `continuity_warnings`
- the count of entries in each category;
- every entry in each category;
- empty-category state (`No entries.`) rather than hiding an empty category;
- a read-only notice.

Conceptually:

```text
Story Memory                         ×

1842 / 3000 characters used
[████████░░░░░░░░░░░░]

Decisions · 4
• The mystery is not resolved before the midpoint.

Directions · 3
• Explore the Mara–Victor alliance through professional obligation.

Open questions · 2
• Whether Victor altered the ledger remains unresolved.

Continuity warnings · 3 ⚠
• The ferry departure time is inconsistent between the harbour scene and Act 3.

Read-only view. Use story_memory to add, remove, or replace entries.
```

### Visual rules

- use the existing dashboard theme and components;
- show one usage bar for the total budget;
- use the existing accent/border/background tokens;
- use a restrained warning accent only for `continuity_warnings`;
- keep all other categories typographically neutral;
- use the existing small type scale and spacing rhythm;
- do not use per-category progress bars or per-category quotas;
- do not introduce a new color system or decorative animation;
- keep the dialog scrollable when the memory grows.

### Excluded from v1 UI

- edit controls;
- add/remove/replace buttons;
- timestamps;
- entry IDs;
- per-category quotas;
- per-category character budgets;
- automatic conflict resolution.

The dialog is a human verification surface, not a second mutation surface. Mutations remain on the dedicated `story_memory` tool.

## 17. Open decisions

The behavioral and visual UI contract is settled. Pixel-level implementation details may follow the existing dashboard conventions when the UI is implemented.

## 18. Design summary

Story Architect's memory is a small, explicit, project-level creative brief.

It borrows from Hermes the useful mechanics:

- a small bounded store;
- explicit writes;
- project-start exposure rather than global system-prompt injection;
- human-visible storage;
- deliberate curation.

It rejects Hermes' assumption that flat notes are always sufficient for every domain, and it does not copy Hermes' memory semantics into a story context.

The governing sentences are:

> Memory stores information that cannot be reliably recovered from a single entity, scene, or relationship, but that materially affects future story work.

> Automatic memory may draft a proposal. It must not silently create canon.

> `story_load` is the project-entry point. It exposes the current bounded memory once; it is not injected into every request.

