# Task 16 — Plugin Tool Surface Audit

## Task: Create a new project named "hermes_tests"

---

## Finding 1: No tool to create a project

`story_create` enum at `tools/story_create.py:56`:
```python
"enum": ["character", "location", "world", "plot", "scene", "sequence", "act", "arc"]
```
**No `"project"`** in the enum. Agent cannot create a project through the plugin tool surface.

**Impact:** Agent must use terminal/write_file to create folder + `project.md`, then call `story_index`. Bypasses all plugin validation, path resolution, and schema defaults.

---

## Finding 2: Two-step initialization required

`story_load` returned: `"No index found. Run story_index first."`

**Impact:** Agent must know to call `story_index` before `story_load`. Not discoverable from tool descriptions.

---

## Finding 3: `tool_describe` returns empty schemas

`tool_describe` for `story_create`, `story_load`, `story_dashboard` all returned:
```json
{"type": "object", "properties": {}}
```

**Impact:** Agent cannot discover parameters from tool definitions. Must read source code or skill docs to understand what fields to pass.

---

## Finding 4: Plugin skills not discoverable

### Symptoms
- `skills_list()` does NOT include `hermes-story-architect:story-loader`, `hermes-story-architect:story-editor`, or `hermes-story-architect:story-theory`
- `skill_view(name="story-loader")` fails with "Skill not found"
- `skill_view(name="hermes-story-architect:story-loader")` WORKS

### Root Cause
Plugin skills are registered via `ctx.register_skill(name, path)` in `__init__.py:84`. Per Hermes plugin docs, these are **namespaced as `plugin:skill`** and loaded via `skill_view("plugin:skill")`.

However:
1. They don't appear in `skills_list()` output
2. They don't appear in the system prompt's `<available_skills>` section
3. The main `hermes-story-architect` skill does NOT explicitly direct the agent to load the sub-skills

**Impact:** Agent has no way to discover that `story-loader` and `story-editor` exist. Must either:
- Guess the naming convention (`hermes-story-architect:<name>`)
- Read the source code (`__init__.py` to see `ctx.register_skill()` calls)
- Hope the main skill mentions them (it doesn't, currently)

### Fix
The main `hermes-story-architect` skill should explicitly direct the agent to load the qualified skill names for each task type. Example addition:

```markdown
## Skill Routing

| Task | Load This Skill |
|------|----------------|
| Loading a project, creating a new project | `hermes-story-architect:story-loader` |
| Editing entities, creating entities, reordering | `hermes-story-architect:story-editor` |
| Narrative theory, value arcs, plot structure | `hermes-story-architect:story-theory` |
```

---

## Finding 5: `story_index` auto-creates incomplete `project.md`

At `tools/story_index.py:32-42`, if `project.md` is missing, `story_index` creates one with only `name`:
```python
f"name: {project_path.name}\n"
```
Missing required `logline` and all optional fields per `REQUIRED_FIELDS["project"]`.

**Impact:** Auto-created project doesn't satisfy its own schema.

---

## Summary

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | Can't create project via tools | `story_create` enum missing `"project"` | Add project creation to `story_create` or create `story_create_project` |
| 2 | `story_load` fails without `story_index` | No auto-index on load | Auto-run `story_index` in `story_load` if index missing |
| 3 | Tool schemas empty | `tool_describe` returns `{}` for deferred tools | Investigate deferred tool schema registration |
| 4 | Skills not loading | Plugin skills namespaced but not discoverable | Add skill routing table to main skill |
| 5 | Auto-created project incomplete | `story_index` writes minimal frontmatter | Use `ENTITY_SCHEMAS["project"]` defaults in `story_index` |

All findings from a single task: "create a new project named hermes_tests".
