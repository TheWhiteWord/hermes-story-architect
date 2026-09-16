# Task 16 — Plugin Profile Auto-Creation

## Problem

Plugin skills registered via `ctx.register_skill()` show empty descriptions in `skills_list()` 
and don't appear in the system prompt's `<available_skills>`. The agent can't discover them 
without knowing the qualified name (`hermes-story-architect:story-loader`) in advance.

## Reference: obsidian-vault's approach

Obsidian-vault solves this with a **setup script** (`scripts/setup.py`) that runs after 
`hermes plugins install`. It:

1. **Creates a profile** via `hermes profile create <name> --description <desc>` (subprocess)
2. **Symlinks skills** into the profile's `skills/` directory (so they're scanned as local skills 
   with full descriptions)
3. **Seeds config.yaml** from the default profile
4. **Enables the plugin** for the profile via `hermes --profile <name> plugins enable`
5. **Writes SOUL.md** with role-specific identity and instructions

Key functions in `scripts/vault_ops.py`:
- `_create_profile(name, description)` — subprocess call to `hermes profile create`
- `enable_plugin_for_profile(hermes_home, name, vault_root)` — symlinks plugin + enables via CLI
- `seed_profile_config(hermes_home, name)` — copies default config.yaml if missing
- `install_skills(profile_skills, role)` — symlinks skill bundles into profile's skills dir

## Proposed solution for story-architect

### Step 1: Create `scripts/setup.py`

A minimal setup script that:
1. Checks if profile `story-architect` exists
2. If not: `hermes profile create story-architect --description "Story Architect specialist agent"`
3. Seeds config.yaml from default
4. Enables the plugin for the profile
5. Writes a minimal SOUL.md that instructs the agent to load `hermes-story-architect:story-loader`

### Step 2: Profile naming

Options:
- `story-architect` — short, clear
- `hermes-story-architect` — matches plugin name exactly

### Step 3: SOUL.md content (minimal v1)

```markdown
# Story Architect

You are a story architect assistant. You help the user manage story projects 
(characters, locations, plots, scenes, sequences, acts, arcs) using the 
Hermes Story Architect plugin.

## Always Load

At the start of every conversation, load the story-architect skill:
`skill_view("hermes-story-architect:story-loader")`

This gives you the project index, memory, and entity schemas.
```

### Step 4: What the setup script needs to do

```python
# Pseudocode
profile_name = "story-architect"
hermes_home = Path.home() / ".hermes"
profile_dir = hermes_home / "profiles" / profile_name

if not profile_dir.exists():
    subprocess.run(["hermes", "profile", "create", profile_name, 
                    "--description", "Story Architect specialist agent"])
    
# Seed config from default
# Enable plugin for profile
# Write SOUL.md
```

### Step 5: When does setup run?

Two options:
- **Manual**: User runs `python scripts/setup.py` after `hermes plugins install`
- **Auto from register()**: Plugin's `register()` checks for a marker file, runs setup once

Recommendation: **Manual** (like obsidian-vault). More predictable, easier to debug.

## Open questions for the user

1. Profile name: `story-architect` or `hermes-story-architect`?
2. Manual setup script or auto-run from `register()`?
3. SOUL.md content — minimal (just "load the skill") or more elaborate?
4. Should the setup script also install skills (symlink to `~/.hermes/skills/`) or just 
   rely on `ctx.register_skill()` for now?
