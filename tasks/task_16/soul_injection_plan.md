# Task 16 — SOUL.md Injection on Plugin Enable/Disable

## Approach

**Hook into plugin lifecycle by checking enabled state at `register()` time.**

Since disabled plugins never call `register()`, we can only reliably detect "enabled" state from within the plugin. Disablement requires an external cleanup mechanism.

## Implementation Plan

### 1. At `register()` time (every Hermes startup)

```python
def register(ctx):
    # ... existing tool/skill registration ...
    
    # Inject SOUL.md block if plugin is enabled
    _manage_soul_block()

def _manage_soul_block():
    """Ensure SOUL.md has the managed block if plugin is enabled."""
    from hermes_constants import get_hermes_home
    import yaml
    
    config = yaml.safe_load(get_hermes_home().joinpath("config.yaml").read_text())
    enabled = "hermes-story-architect" in config.get("plugins", {}).get("enabled", [])
    
    if enabled:
        _ensure_soul_block()
    # Note: if disabled, we can't remove the block here because register() doesn't run


SOUL_ANCHOR = "<!-- story-architect: managed by plugin; do not edit -->"

def _ensure_soul_block():
    """Append the managed block to SOUL.md (idempotent)."""
    from hermes_constants import get_hermes_home
    
    soul_path = get_hermes_home() / "SOUL.md"
    block = f"""{SOUL_ANCHOR}
## Story Architect

When the user asks about story projects (characters, locations, plots, scenes, 
sequences, acts, arcs, screenplays, value arcs), load the story architect skill:
`skill_view("hermes-story-architect")`

This gives you the full project context, index format, and entity schemas.
{SOUL_ANCHOR}"""
    
    if not soul_path.exists():
        soul_path.write_text(block)
        return
    
    text = soul_path.read_text()
    if SOUL_ANCHOR in text:
        # Already managed — replace the block in place
        start = text.index(SOUL_ANCHOR)
        end = text.index(SOUL_ANCHOR, start + 1) + len(SOUL_ANCHOR)
        text = text[:start] + block + text[end:]
    else:
        # Append
        text = text.rstrip() + "\n\n" + block
    
    soul_path.write_text(text)


def _remove_soul_block():
    """Remove the managed block from SOUL.md (for cleanup script)."""
    from hermes_constants import get_hermes_home
    
    soul_path = get_hermes_home() / "SOUL.md"
    if not soul_path.exists():
        return
    
    text = soul_path.read_text()
    if SOUL_ANCHOR not in text:
        return
    
    start = text.index(SOUL_ANCHOR)
    end = text.index(SOUL_ANCHOR, start + 1) + len(SOUL_ANCHOR)
    text = text[:start] + text[end:].lstrip()
    
    soul_path.write_text(text)
```

### 2. Cleanup script for disable

`scripts/cleanup_soul.py`:
```python
"""Remove story-architect block from SOUL.md (run before disabling plugin)."""
from hermes_constants import get_hermes_home

SOUL_ANCHOR = "<!-- story-architect: managed by plugin; do not edit -->"

soul_path = get_hermes_home() / "SOUL.md"
if soul_path.exists():
    text = soul_path.read_text()
    if SOUL_ANCHOR in text:
        start = text.index(SOUL_ANCHOR)
        end = text.index(SOUL_ANCHOR, start + 1) + len(SOUL_ANCHOR)
        text = text[:start] + text[end:].lstrip()
        soul_path.write_text(text)
        print("Removed story-architect block from SOUL.md")
    else:
        print("No story-architect block found in SOUL.md")
else:
    print("No SOUL.md found")
```

### 3. Single combined skill

Rename `hermes-story-architect:story-loader` → `hermes-story-architect` (one skill to rule them all).

The existing `hermes-story-architect` skill (the main skill loaded by the agent at dev time) becomes the only skill. The sub-skills (`story-loader`, `story-editor`, `story-theory`) become references within it.

### 4. Updates needed

- `__init__.py`: Add `_manage_soul_block()` call in `register()`
- `__init__.py`: Register only one skill: `ctx.register_skill("hermes-story-architect", skill_md)`
- `plugin.yaml`: Update `provides_skills` to `["hermes-story-architect"]`
- `skills/` directory: Replace 3 skills with 1 combined `hermes-story-architect/SKILL.md`
- `scripts/cleanup_soul.py`: New file for SOUL.md cleanup

## Key Design Decisions

1. **Idempotent**: Adding the block multiple times is safe — anchor-based replacement
2. **Non-destructive**: User content is preserved; only the managed block is touched
3. **Graceful degradation**: If user manually removes the block, it stays removed until next plugin enable+restart
4. **Disable cleanup**: Requires manual script run OR user can ignore (block just sits there inert)

## Questions for User

1. **Single skill structure**: What should the initial empty/minimal `hermes-story-architect` skill contain?
   - Option A: Empty body, just frontmatter
   - Option B: Minimal "load this when asked about stories" trigger
   
2. **Sub-skills as references**: Should `story-loader`, `story-editor`, `story-theory` become reference files under the new combined skill, or be removed entirely?

3. **Cleanup script naming**: `scripts/cleanup_soul.py` or `scripts/uninstall.py` or something else?
