# Build Plan — Implementation Phases

> Translate research decisions into working code. Each phase builds on the previous.

---

## Phase 1: Core Foundation (Task 2)

**Goal**: Build the index system — everything depends on this.

### Subtask 1.1: Plugin Skeleton
```
plugin/
├── __init__.py              # register(ctx) entry point
├── config.py                # load vault_path from Hermes config
├── constants.py             # VALID_ROLES, VALID_STATUSES, FUZZY_THRESHOLD, ENTITY_FOLDERS
└── core/
    ├── __init__.py
    ├── section_parser.py    # list_sections, get_section, replace_section
    ├── entity.py            # extract_entity, validate_entity, update_sections
    ├── screenplay.py        # extract_scenes, match_character, match_location
    └── index.py             # generate_index, write_index
```

### Subtask 1.2: Section Parser (`core/section_parser.py`)
- Regex-based `##` heading parser
- `list_sections(body)` → list of heading names
- `get_section(body, section)` → section content
- `replace_section(body, section, new_body)` → modified body

### Subtask 1.3: Entity Extraction (`core/entity.py`)
- `extract_entity(path, type)` → dict with frontmatter + sections
- `validate_entity(type, frontmatter)` → list of warnings
- `update_sections(path, sections)` → update frontmatter

### Subtask 1.4: Screenplay Integration (`core/screenplay.py`)
- `extract_scenes(content)` → list of scene dicts via screenplay-tools
- `extract_location(heading)` → location name from heading
- `match_character(name, characters)` → slug via rapidfuzz
- `match_location(heading_location, locations)` → slug via rapidfuzz

### Subtask 1.5: Index Generator (`core/index.py`)
- `generate_index(project_path)` → full index dict
- `write_index(index, path)` → YAML file
- Reference resolution + validation

### Subtask 1.6: Plugin Entry Point (`__init__.py` + `config.py`)
- `register(ctx)` — register all tools
- `load_plugin_config()` — read vault_path from Hermes config
- `check_fn` — gate on vault_path configured

---

## Phase 2: Tools (Tasks 3 + 4)

**Goal**: Register tools that use the core modules.

### Subtask 2.1: story_load Tool
- Schema: `{project: string}`
- Handler: resolve project → read index + memory → return confirmation
- Uses: core/index.py, core/entity.py

### Subtask 2.2: story_retrieve Tool
- Schema: `{entity_type, slug, sections}`
- Handler: read file → extract sections → return content
- Uses: core/section_parser.py, core/entity.py

### Subtask 2.3: story_index Tool
- Schema: `{project: string}`
- Handler: generate_index → write_index → return confirmation
- Uses: core/index.py

### Subtask 2.4: story_search Tool
- Schema: `{project: string, query: string}`
- Handler: search across project notes → return matches
- Uses: core/entity.py

---

## Phase 3: Action Protocol (Task 5)

**Goal**: Editing tools with review loop.

### Subtask 3.1: story_edit Tool
- Schema: `{action, target, changes, summary, continuity_checks}`
- Handler: apply edit via core modules → update index
- Uses: core/section_parser.py, core/entity.py, core/screenplay.py

### Subtask 3.2: story_create Tool
- Schema: `{entity_type, slug, frontmatter, body}`
- Handler: create note file → update index
- Uses: core/entity.py, core/index.py

---

## Phase 4: Skills (Tasks 3 + 5)

**Goal**: Bundle skills that guide LLM behavior.

### Subtask 4.1: story-loader Skill
- `plugin/skills/story-loader/SKILL.md`
- `plugin/skills/story-loader/references/index-format.md`

### Subtask 4.2: story-editor Skill
- `plugin/skills/story-editor/SKILL.md`
- `plugin/skills/story-editor/references/action-types.md`
- `plugin/skills/story-editor/references/continuity-checks.md`

---

## Phase 5: Dashboard (Task 6)

**Goal**: Interactive HTML dashboard.

### Subtask 5.1: Evaluate UI Designs
- Review Claude/DeepSeek outputs
- Pick-and-mix best ideas
- Finalize design

### Subtask 5.2: Implement Dashboard
- `src/dashboard/story-dashboard.html`
- Single file, embedded CSS/JS
- vis-network for character graph

---

## Phase 6: Integration (Task 7)

**Goal**: End-to-end testing.

### Subtask 6.1: Test Project
- Create a real story project in vault
- Multi-character, multi-scene, multi-plot

### Subtask 6.2: End-to-End Flow
- Load → query → retrieve → propose → approve → apply → index update
- Dashboard rendering

---

## Build Order

```
Phase 1 (Core) → Phase 2 (Tools) → Phase 3 (Actions) → Phase 4 (Skills) → Phase 5 (Dashboard) → Phase 6 (Integration)
```

**Start with Phase 1, Subtask 1.1: Plugin Skeleton.**
