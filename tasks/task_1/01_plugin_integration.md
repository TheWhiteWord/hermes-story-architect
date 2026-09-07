# Subtask: Plugin Architecture — Standalone Vault

> **DECIDED**: Story Architect is a **standalone Hermes plugin** with its own vault. No integration with obsidian-vault's tools, config system, or grants. We borrow *concepts* that genuinely fit, not code.

---

## Decisions (confirmed)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Vault location | `~/story-vault/`, configurable |
| 2 | Plugin config | Hermes plugin config |
| 3 | Plugin registration | Standard Hermes plugin API |
| 4 | Multiple projects | One vault, multiple project folders |

---

## Architecture

**Standalone plugin** — registers its own tools, manages its own vault, no coupling to obsidian-vault.

**Borrowed concepts** (ideas, not code):
- Three-stage retrieval (index → target → load)
- Frontmatter → body mapping
- Standard `##` sections for targeting
- Always-loaded project index
- Zero-dependency regex section parser

**Not borrowed**:
- `.vault/config.yaml` schema DSL → Python validation
- `obsidian_*` tools → raw file I/O + our own tools
- Grant/role system → single-user, no grants needed
- `INDEX.md` generation → our own if needed

---

## Vault structure

```
~/story-vault/                          # Configurable
├── .story/
│   ├── index.yaml                      # Project graph (always-loaded)
│   ├── memory.md                       # Story memory (continuity map)
│   └── history.md                      # Edit history (gitignored)
├── projects/
│   └── <project-slug>/
│       ├── project.md                  # Project metadata
│       ├── synopsis.md
│       ├── treatment.md
│       ├── screenplay.md               # Fountain syntax
│       ├── characters/
│       │   ├── mara.md
│       │   └── _index.md
│       ├── locations/
│       ├── worlds/
│       └── plots/
```

No `.vault/` folder. No `.state/`. No grants. No roles. Just `.story/` for plugin machinery.

---

## Plugin tools

| Tool | What it does |
|------|-------------|
| `story_load` | Load project index + memory into context |
| `story_retrieve` | Get specific sections from project notes |
| `story_edit` | Propose + apply edits (action protocol) |
| `story_create` | Create new entity |
| `story_index` | Regenerate project index |
| `story_search` | Search within a project |

Simpler than `obsidian_*` — no grants, no schema validation, no conventions.

---

## Config (Hermes plugin config)

```yaml
# Hermes plugin config
story_architect:
  vault_path: ~/story-vault
  projects_dir: projects
```

No `.story/config.yaml` — Hermes plugin config is the single source of truth.

---

## Validation

Python functions, not config DSL:

```python
def validate_character_frontmatter(fm: dict) -> list[str]:
    errors = []
    if "name" not in fm:
        errors.append("Missing required field: name")
    if "story_role" not in fm:
        errors.append("Missing required field: story_role")
    return errors
```

---

## What this means for other subtasks

- **02_entity_schemas.md**: Schemas defined in Python, not config
- **03_screenplay_format.md**: Independent — no change
- **04_decisions.md**: Plugin integration decisions resolved

---

## Status: RESOLVED

All open questions answered. Ready to proceed to entity schemas (02).
