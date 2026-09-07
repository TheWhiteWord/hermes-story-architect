# Hermes Story Architect — Main Tasks

> High-level implementation stages. Each stage is a self-contained research + build area.

---

## Plugin Structure

```
hermes-story-architect/                 # repo root (dev)
├── plugin/                             # → installed to ~/.hermes/plugins/hermes-story-architect/
│   ├── __init__.py                     # register(ctx) — entry point
│   ├── config.py                       # load vault_path from Hermes plugin config
│   ├── constants.py                    # VALID_ROLES, VALID_STATUSES, FUZZY_THRESHOLD
│   ├── core/                           # core operations (reusable by tools)
│   │   ├── section_parser.py           # list_sections, get_section, replace_section
│   │   ├── entity.py                   # extract_entity, validate_entity, update_sections
│   │   ├── screenplay.py               # extract_scenes, match_character, match_location
│   │   └── index.py                    # generate_index, write_index
│   ├── tools/                          # tool handlers (one per tool)
│   │   ├── story_load.py               # load project index + memory into context
│   │   ├── story_retrieve.py           # get specific sections from project notes
│   │   ├── story_edit.py               # propose + apply edits (action protocol)
│   │   ├── story_create.py             # create new entity
│   │   ├── story_index.py              # regenerate project index
│   │   └── story_search.py             # search within a project
│   └── skills/                         # bundled skills (loaded by tools)
│       ├── story-loader/SKILL.md
│       └── story-editor/SKILL.md
├── src/dashboard/story-dashboard.html  # preview pane dashboard
├── research/                           # STARC architecture reference
├── plan/                               # build plans
├── tasks/                              # task tracking
├── tests/                              # test suite
├── README.md
└── pyproject.toml                      # package config + dependencies
```

---

## Task 1: Schema & Vault Conventions — ✅ RESOLVED

**What**: Define the data model — entity types, fields, frontmatter schemas, standard body sections, vault folder structure, screenplay format.

**Decisions**: See `tasks/task_1/04_decisions.md`

Key outcomes:
- Standalone plugin, own vault at `~/story-vault/`
- Entity schemas: character, location, world, plot, project (layered: required + optional)
- Standard `##` sections per entity type
- Fountain parsing via `screenplay-tools`
- Dependencies: `screenplay-tools`, `python-frontmatter`, `rapidfuzz`

---

## Task 2: Project Index System — ✅ RESOLVED

OK**What**: Build the `.story/index.yaml` generator — the graph that makes section targeting possible.

**Decisions**: See `tasks/task_2/04_decisions.md`

Key outcomes:
- Index schema: scenes use number+heading, unidirectional relationships, story memory summary-only
- 4 core modules: `section_parser.py`, `entity.py`, `screenplay.py`, `index.py`
- Full regeneration strategy (projects are small)
- All three libraries fully utilized

---

## Task 3: Story Loader Skill

**What**: Hermes skill that loads a project's context (index + memory) into the LLM's context window.

**Research areas**:
- Skill trigger and project discovery (how to find projects in vault)
- What gets loaded: index always, memory always, content on demand
- Confirmation format (what Hermes reports after loading)
- Multi-project handling (can multiple projects be loaded?)

**Depends on**: Task 1 (schemas), Task 2 (index structure)

**Output**: `plugin/tools/story_load.py` + `plugin/skills/story-loader/SKILL.md`

---

## Task 4: Section Parser & Retrieval Engine

**What**: The retrieval loop that loads only the needed `##` sections.

**Research areas**:
- Retrieval loop: index identifies targets → parser extracts sections → content loaded into context
- Edge cases: missing sections, duplicate headings, malformed content
- Integration with Hermes `read_file` tool

**Depends on**: Task 2 (index structure, section_parser.py)

**Output**: `plugin/tools/story_retrieve.py`

---

## Task 5: Action Protocol & Review Loop

**What**: The full editing workflow — action types, proposal format, human review, apply, index update.

**Research areas**:
- Action type taxonomy (edit_note, create_entity, delete_entity, edit_screenplay, etc.)
- Proposal format: what Hermes shows the user before applying
- Review loop: propose → user approves/rejects → apply → update index
- Safety: recycle bin for deletions, no silent edits, continuity checks
- Frontmatter vs. body editing (different actions for YAML fields vs. prose sections)
- `screenplay-tools` Writer for round-trip Fountain editing

**Depends on**: Task 2 (core modules), Task 3 (loader), Task 4 (retrieval)

**Output**: `plugin/tools/story_edit.py` + `plugin/skills/story-editor/SKILL.md`

---

## Task 6: Preview Pane Dashboard

**What**: Interactive HTML dashboard for the Hermes preview pane — character map, scene list, timeline, continuity report.

**Research areas**:
- Dashboard views: project overview, character graph, scene list, timeline, continuity
- vis-network integration (CDN-loaded, force-directed character graph)
- Data source: reads `.story/index.yaml` for structure, vault for content
- Interaction model: click entity → see details, "Ask Hermes about this" buttons
- Refresh strategy (manual vs. file watcher)

**Depends on**: Task 2 (index structure)

**Output**: `src/dashboard/story-dashboard.html`

---

## Task 7: Integration & Real-Project Testing

**What**: Wire everything together and validate with a real story project end-to-end.

**Research areas**:
- Create a test project in the vault (multi-character, multi-scene, multi-plot)
- End-to-end flow: load → query → retrieve → propose → approve → apply → index update
- Token usage measurement (is section targeting actually saving tokens?)
- Dashboard rendering and interaction validation
- Edge cases: concurrent edits, large projects, malformed input

**Depends on**: All previous tasks

**Output**: Working demo + test project in vault

---

## Dependency Order

```
Task 1 (Schema) ✅
    ↓
Task 2 (Index System) ✅
    ↓
Task 3 (Loader) ←──→ Task 4 (Retrieval)
                          ↓
                    Task 5 (Action Protocol)
                          ↓
                    Task 6 (Dashboard)
                          ↓
                    Task 7 (Integration)
```

Tasks 3 and 4 can be researched in parallel (both depend on Task 2, not each other).
