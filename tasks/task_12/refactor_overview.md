# Refactor Overview: Scenes as First-Class Entities

**Created:** 2026-09-12
**Status:** Planning structure — research not yet started
**Source proposal:** `Claude_structure_refactor.md`

---

## Goal

Replace the current architecture where scenes are a parsed derivative of `screenplay.fountain` with one where scenes, sequences, and acts are first-class entities stored as individual files. The screenplay becomes an import/export format, not the working document.

**Core identity rule:** Scene identity = user-assigned slug describing dramatic function (e.g., `mara-discovers-files`), NOT the physical heading (`INT. PRECINCT BATHROOM - DAY`). Heading is metadata; slug is identity.

---

## Current State (what exists today)

| Component | File | Role |
|-----------|------|------|
| Entity extraction | `core/entity.py` | Generic frontmatter + section parser |
| Index generator | `core/index.py` | Scans folders, builds cross-references |
| Screenplay integration | `core/screenplay.py` | Wraps `fountain_lexer.py` to extract scenes from `screenplay.fountain` |
| Fountain lexer | `core/fountain_lexer.py` | Better Fountain port (~733 lines) |
| Constants/schemas | `core/constants.py` | Entity types, folders, validation rules |
| Section parser | `core/section_parser.py` | Zero-dependency `##` heading parser |
| Config | `core/config.py` | Plugin config loader |

**Tools:** `story_load`, `story_retrieve`, `story_index`, `story_search`, `story_edit`, `story_create`, `story_dashboard`, `story_resolve`

**Current data model:**
- Entity types: `character`, `location`, `world`, `plot`, `project`
- Scenes: extracted from `screenplay.fountain` at index time, stored as flat list in `index.yaml`
- No scene files, no sequence/act entities
- Plot setups/payoffs reference scenes by heading string (fragile — duplicate headings break it)

---

## Phases

Each phase follows the same workflow:

```
RESEARCH → IDENTIFY → CLARIFY → PLAN
```

- **RESEARCH:** Investigate the area, read code, understand dependencies
- **IDENTIFY:** List specific files/functions/schemas that need changes
- **CLARIFY:** Resolve open questions, define interfaces, confirm assumptions
- **PLAN:** Write implementation steps as tasks (in a phase folder)

We do NOT execute the research now. This document only defines what each phase must investigate.

---

### Phase 1: Data Model & Entity Foundation

**What:** Define the scene, sequence, and act entity types. Update core schemas and validation.

**Research areas:**

1. **Scene frontmatter schema**
   - Which fields from the proposal are needed at creation vs. filled later?
   - Nullable vs. required — what's the minimal viable scene?
   - How does `order` work within a sequence? (integer? float for insertions?)
   - What are the valid enums for `status`, `time_of_day`, `dramatic_role`, `value_open`, `value_close`?
   - Should `characters` and `plots` be frontmatter arrays or derived from content?

2. **Sequence & act frontmatter schemas**
   - What fields does a sequence need beyond `id`, `title`, `order`, `act_id`?
   - What fields does an act need beyond `id`, `title`, `order`?
   - How does `climax_scene_id` get validated (must reference existing scene)?

3. **Entity registration**
   - How do new types plug into `ENTITY_FOLDERS`, `ENTITY_SCHEMAS`, `REQUIRED_FIELDS`?
   - Does `validate_entity()` need new branches for scene/sequence/act?
   - Does `extract_entity()` need type-specific logic?

4. **Slug identity rules**
   - What characters are allowed in slugs?
   - How are slugs generated for scenes imported from screenplay (when that comes later)?
   - What happens on slug rename — how are references updated?

**Key files to investigate:**
- `core/constants.py` — add scene/sequence/act to all dicts
- `core/entity.py` — extend validation
- `core/section_parser.py` — verify it handles new body section names

**Open questions to clarify:**
- Should `act_id` be stored directly on scenes (denormalization for query speed) or derived via sequence?
- Should `location` be a free string or a slug reference to `locations/`?
- What's the canonical scene status workflow? (`planned` → `drafted` → `written` → `locked`)

---

### Phase 2: Index & Storage

**What:** Extend the index generator to walk `scenes/`, `sequences/`, `acts/` and produce the new index structure.

**Research areas:**

1. **Index structure for new types**
   - What does a scene index entry look like? (see proposal §6)
   - What does a sequence index entry look like?
   - What does an act index entry look like?
   - How are counts computed (`scene_count`, `sequence_count`)?

2. **Structure index sidecar (`.story/structure-index.yaml`)**
   - What's the exact schema for the sidecar?
   - How is it generated — full rebuild vs. incremental update?
   - What queries hit the sidecar vs. the main index?
   - How does `story_index` trigger sidecar regeneration?

3. **Cross-reference building**
   - How do we build `character.scenes` from scene files (not screenplay)?
   - How do we build `location.scenes` from scene files?
   - How do plot setups/payoffs reference scenes now (by slug, not heading)?
   - How do we derive `sequence.scenes_list` and `act.sequences_list`?

4. **Index regeneration triggers**
   - When a scene file changes, what needs updating?
   - When a sequence changes, what cascades?
   - Can we do incremental updates or must we rebuild everything?

**Key files to investigate:**
- `core/index.py` — extend `generate_index()`, add new `_parse_*` functions, update `_enrich_*` functions
- `core/entity.py` — verify `extract_entity()` works for new types

**Open questions to clarify:**
- Should the structure index be a separate file or a section in the main index?
- How do we handle scenes that exist in files but have no screenplay content yet?
- What's the performance characteristics for a 94-scene story?

---

### Phase 3: Tool Surface

**What:** Create `story_structural` tool and update existing tools to handle the new entity types.

**Research areas:**

1. **`story_structural` tool design**
   - What's the exact schema? (action, type, id, sections, data)
   - How does `reorder` work — batch update of `order` fields?
   - How does `delete` handle cascading references?
   - How does `create` generate the initial file with frontmatter + body sections?

2. **Integration with existing tools**
   - Does `story_edit` need to handle scene/sequence/act, or does `story_structural` replace it for these types?
   - Does `story_create` need to handle scene/sequence/act?
   - Does `story_retrieve` need type-specific section handling?
   - Does `story_search` need to walk new folders?

3. **File I/O patterns**
   - How do we create a scene file with the right frontmatter defaults?
   - How do we update a scene's `order` field atomically?
   - How do we handle the `## Content` section — is it treated specially?

4. **Plugin registration**
   - How does `story_structural` get registered in `__init__.py` and `plugin.yaml`?
   - What emoji, schema, check function does it need?

**Key files to investigate:**
- `tools/story_edit.py` — understand current edit patterns
- `tools/story_create.py` — understand current create patterns
- `tools/story_retrieve.py` — understand current retrieve patterns
- `__init__.py` — understand registration pattern
- `plugin.yaml` — understand tool declaration

**Open questions to clarify:**
- Should `story_structural` be the only tool for scenes/sequences/acts, or should `story_edit` handle them too?
- How does the LLM discover what sections a scene has — from the index or from the file?
- What's the error handling for invalid operations (e.g., deleting a sequence that has scenes)?



### Phase 4: Dashboard & Frontend

**What:** Update the dashboard to display and interact with scenes, sequences, and acts.

**Research areas:**

1. **Dashboard data injection**
   - How does `story_dashboard` inject scene/sequence/act data into the HTML?
   - What new `window.__*__` variables are needed?
   - How does the dashboard handle the structure index sidecar?

2. **Script view assembly**
   - How does the script view render scene files in order?
   - What does the script view show for scenes without content?
   - How does the script view handle act/sequence boundaries?

3. **Entity panels**
   - How are scene/sequence/act panels rendered?
   - What CRUD operations are available from the UI?
   - How does reordering work in the UI?

**Key files to investigate:**
- `src/dashboard/story-dashboard.html` — understand current rendering
- `tools/story_dashboard.py` — understand data injection

**Open questions to clarify:**
- Should the dashboard regenerate the structure index on open?
- How much structure analysis happens client-side vs. server-side?
- What's the UX for creating a new scene from the dashboard?



```
Phase 1 (Data Model)
    ↓
Phase 2 (Index & Storage)
    ↓
Phase 3 (Tool Surface)
    ↓
Phase 4 (Dashboard)
```

Phases 1-3 are the critical path. Phase 4 depends on Phase 3.

---

## Separate Jobs (Not Part of This Refactor)

These are intentionally excluded — they depend on this refactor being complete but are separate undertakings:

- **Screenplay Integration** — Reimporting scenes from `screenplay.fountain` into the new scene-file architecture. This is the opposite direction of what we're building (scenes-first, screenplay-as-export). It should be its own job after Phases 1-3 + 5 are done.
- **Advanced Features** — Character arcs, value turn analysis, structural validation. These need the data model to be stable and the tool surface complete. Future work.

---

## Research Workflow (per phase)

For each phase, the work session should:

1. **RESEARCH** — Read all key files listed. Trace the full flow end-to-end. Don't write code.
2. **IDENTIFY** — List every function, schema, constant, and file that needs changes. Be specific.
3. **CLARIFY** — Answer the open questions. If a question needs user input, flag it.
4. **PLAN** — Write implementation tasks in a phase folder (e.g., `tasks/task_12/phase_1/`).

The output of each phase is a **plan document** and **task files** — not code.

---

## Out of Scope (for now)

- Backward compatibility with existing projects (none exist except tests)
- Full feature parity with current screenplay scene retrieval
- Character arc system
- Value turn analysis
- Structural validation / LLM-driven analysis
- Multi-project support changes
- Performance optimization for large projects

---

## Success Criteria

- [ ] Scenes can be created, retrieved, edited, reordered, and deleted as files
- [ ] Sequences and acts can be created and managed
- [ ] The index correctly reflects scene/sequence/act relationships
- [ ] The dashboard displays the new entity types
- [ ] All existing tests still pass (or are updated intentionally)
- [ ] The plugin registers `story_structural` as a new tool
