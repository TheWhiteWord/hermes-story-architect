# Task 16 — Centralized Project Creation

## Problem

| File | Created by | Problem |
|------|-----------|---------|
| `project.md` | `story_index.py:32-42` | Missing all optional fields |
| `.story/memory.md` | `story_index.py:44-50` | Just `# Story Memory\n\n` |
| `.story/index.yaml` | `story_index.py:52-58` | OK, but depends on above |
| Entity folders | `story_create.py:139` | Created on demand per entity |

`story_index` is a "patch everything" tool that creates missing files with minimal content. This means `story_load` fails without `story_index` first, and `story_index` creates incomplete scaffolding.

## Solution

Add `entity_type: "project"` to `story_create`. Project creation initializes everything:
- `project.md` with full `ENTITY_SCHEMAS["project"]` frontmatter
- `.story/memory.md` with a useful header
- Entity folders (`characters/`, `locations/`, `worlds/`, `plots/`, `scenes/`, `sequences/`, `acts/`, `arcs/`)
- `.story/index.yaml` via `generate_index` + `write_index`

Then remove auto-creation from `story_index` — it should just error if files are missing.

## Implementation

### Project Schema Defaults

In `core/constants.py`, change `"default": ""` to `"default": "not set"` for core project fields that should show visibility when empty in the dashboard. Title page fields (screenplay_title, credit, author, etc.) keep `""` since they're output-only.

Fields to change:
- `logline`: `"not set"`
- `genre`: `"not set"`
- `setting`: `"not set"`
- `spine`: `"not set"`
- `controlling_idea`: `"not set"`
- `value`: `"not set"`
- `value_at_open`: `"not set"`
- `value_at_close`: `"not set"`
- `structure_type`: `"not set"`
- `inciting_incident_scene_id`: `"not set"`
- `story_climax_scene_id`: `"not set"`

Fields to keep `""`:
- `screenplay_title`, `credit`, `author`, `contact`, `draft_date`, `draft` (output-only, empty hides them)

Fields unchanged:
- `status`: `"active"` (already has non-empty default)
- `act_count`: `3` (already has non-zero default)

### `tools/story_create.py`

Add project branch in `handler()`:

```python
def handler(args, **kwargs):
    entity_type = args["entity_type"]
    slug = args["slug"]
    frontmatter_data = args["frontmatter"]
    
    if entity_type == "project":
        return _create_project(slug, frontmatter_data)
    
    # ... existing entity creation ...


def _create_project(slug, frontmatter_data):
    # Validate required fields
    schema = ENTITY_SCHEMAS.get("project", {})
    required = [f for f, meta in schema.items() if not meta.get("optional", True)]
    missing = [f for f in required if not frontmatter_data.get(f)]
    if missing:
        return json.dumps({
            "error": f"Missing required fields for project: {', '.join(missing)}"
        })
    
    # Build project path
    project_path = vault_path / "projects" / slug
    if project_path.exists():
        return json.dumps({"error": f"Project already exists: {slug}"})
    
    # Merge frontmatter over schema defaults
    merged = {field: frontmatter_data.get(field, meta["default"]) for field, meta in schema.items()}
    
    project_path.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post("", **merged)
    with open(project_path / "project.md", 'w') as f:
        frontmatter.dump(post, f)
    
    # Create .story/memory.md
    memory_dir = project_path / ".story"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "memory.md").write_text("# Story Memory\n\nContinuity notes for this project.\n")
    
    # Create entity folders
    for folder in ["characters", "locations", "worlds", "plots", "scenes", "sequences", "acts", "arcs"]:
        (project_path / folder).mkdir(exist_ok=True)
    
    # Generate initial index
    from core.index import generate_index, write_index
    index = generate_index(project_path)
    write_index(index, memory_dir / "index.yaml")
    
    return json.dumps({
        "success": True,
        "message": f"Created project: {slug}",
        "file": str(project_path / "project.md")
    })
```

### `tools/story_index.py`

Remove auto-creation of `project.md` and `memory.md`:

```python
def handler(args, **kwargs):
    # ... resolve project ...
    
    # Check required files exist (don't auto-create)
    project_md = project_path / "project.md"
    if not project_md.exists():
        return json.dumps({"error": f"project.md not found. Create with story_create(entity_type='project', slug='{project_path.name}')"})
    
    memory_path = project_path / ".story" / "memory.md"
    if not memory_path.exists():
        return json.dumps({"error": f".story/memory.md not found. Create with story_create(entity_type='project', slug='{project_path.name}')"})
    
    # Generate index
    index = generate_index(project_path)
    write_index(index, project_path / ".story" / "index.yaml")
    
    return json.dumps({
        "success": True,
        "message": f"Index regenerated for {index['project']['name']}",
        "index": index
    })
```

### `core/index.py`

No changes needed — `generate_index` already handles empty folders.

### `tools/story_load.py`

No changes needed — it already reads index.yaml and memory.md.

### `tools/story_retrieve.py`

No changes needed.

### `tools/story_search.py`

No changes needed.

### `tools/story_edit.py`

No changes needed.

### `tools/story_dashboard.py`

No changes needed.

## Files Changed

| File | Change |
|------|--------|
| `core/constants.py` | Change `logline` in `ENTITY_SCHEMAS["project"]` to `optional: True`; update defaults for core project fields to `"not set"` |
| `tools/story_create.py` | Add `_create_project()` function; branch in `handler()` |
| `tools/story_index.py` | Remove auto-creation of `project.md` and `memory.md` |

## Test Plan

1. Create a new project via `story_create(entity_type='project', slug='test', frontmatter={name: 'Test', logline: '...'})`
2. Verify `project.md` has all schema fields
3. Verify `.story/memory.md` has content
4. Verify entity folders exist
5. Verify `.story/index.yaml` exists and is valid
6. Run `story_load` on the new project — should succeed without prior `story_index`
7. Run `story_index` — should regenerate from existing files
