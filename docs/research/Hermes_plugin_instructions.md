# Plugin Tool Registration — Official Reference

Source: [hermes-agent.nousresearch.com/docs/developer-guide/plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins) + `hermes-plugin-guide` skill (verified against live docs).

---

## The 4 Files You Need

```
~/.hermes/plugins/my-plugin/
├── plugin.yaml      # manifest — declares what you provide
├── __init__.py      # register(ctx) — wires schemas to handlers
├── schemas.py       # what the LLM sees (descriptions + params)
└── tools.py         # what runs when the tool is called
```

---

## 1. `plugin.yaml` — The Manifest

```yaml
name: my-plugin
version: 1.0.0
description: One-line description shown in listings

# REQUIRED — declare every tool you register
provides_tools:
  - my_tool
  - another_tool

# REQUIRED for skills to appear in <available_skills>
provides_skills:
  - my-skill

# Declare hooks you register
provides_hooks:
  - post_tool_call

# Optional
author: Your Name
license: MIT
homepage: https://github.com/...
requires_env:
  - name: MY_API_KEY
    description: "API key for My Service"
    url: "https://my.service/keys"
    secret: true
capabilities:
  - tools.override      # to override built-in tools
python_dependencies:
  - "requests>=2.0,<3"  # declare-only, never auto-installed
config_schema:
  api_url:
    type: str
    default: ""
    description: "Service endpoint"
```

**Key:** `provides_skills:` is REQUIRED for skills to load into the agent's context. Without it, skill files exist but are invisible.

---

## 2. `schemas.py` — What the LLM Sees

```python
MY_TOOL = {
    "name": "my_tool",
    "description": (          # THIS IS HOW THE LLM DECIDES WHEN TO CALL YOU
        "What this tool does and when to use it. "
        "Be specific — vague descriptions = model never routes to you."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "What this arg means (e.g., '2**10', 'sqrt(144)')",
            },
        },
        "required": ["expression"],
    },
}
```

---

## 3. `tools.py` — The Handler

```python
import json

def my_handler(args: dict, **kwargs) -> str:
    """Do the work. Always return JSON string."""
    try:
        result = do_work(args)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})
```

**Four hard rules:**
1. **Signature:** `def my_handler(args: dict, **kwargs) -> str`
2. **Return:** Always a JSON string. Success and errors alike.
3. **Never raise:** Catch all exceptions, return error JSON instead.
4. **Accept `**kwargs`:** Hermes may pass additional context in the future.

---

## 4. `__init__.py` — The Registration

```python
from . import schemas, tools
from pathlib import Path

# --- Skills (if you have them) ---
_SKILL_DIR = Path(__file__).parent / "skills"

def register(ctx):
    # Register tools
    ctx.register_tool(
        name="my_tool",
        toolset="my-plugin",
        schema=schemas.MY_TOOL,
        handler=tools.my_handler,
        check_fn=lambda: True,   # optional: False = tool hidden
        emoji="🔧",              # optional display emoji
    )

    # Register skills (BOTH provides_skills: AND this call required)
    for child in _SKILL_DIR.iterdir():
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)

    # Register hooks
    ctx.register_hook("post_tool_call", my_hook)
```

---

## `ctx.register_tool()` — Full Signature

```python
ctx.register_tool(
    name="tool_name",           # unique identifier
    toolset="toolset_name",     # groups tools (shown in banner)
    schema={...},               # OpenAI function schema dict
    handler=func,               # (args: dict, **kwargs) -> str
    check_fn=lambda: True,      # optional availability gate
    emoji="🔧",                 # optional display emoji
    override=False,             # True to shadow a built-in (needs consent)
)
```

**Override a built-in:**
- `override=True` in `register_tool()`
- Plus `plugins.entries.<plugin_id>.allow_tool_override: true` in config.yaml
- Or declare `capabilities: [tools.override]` in plugin.yaml

---

## Conditional Availability

```python
ctx.register_tool(
    name="my_tool",
    schema={...},
    handler=my_handler,
    check_fn=lambda: _has_credentials(),  # False = tool hidden from model
)
```

---

## Settings vs State

```python
# Settings — user-visible behavior in config.yaml
endpoint = ctx.get_config("endpoint", default="https://example.com")
ctx.set_config("endpoint", endpoint)

# State — plugin-owned runtime data, profile-scoped, 10 MiB limit
cursor = ctx.state.get("cursor", default={"page": 0})
ctx.state.set("cursor", {"page": cursor["page"] + 1})
```

---

## Hooks

```python
def my_hook(tool_name, args, result, task_id, **kwargs):
    """Runs after every tool call (not just yours)."""
    pass

ctx.register_hook("post_tool_call", my_hook)
```

---

## Commands

```python
# In-session slash command (/scan)
ctx.register_command("scan", lambda raw: handle_scan(ctx, raw), description="...")

# CLI subcommand (hermes myplugin <subcommand>)
ctx.register_cli_command("myplugin", my_handler, description="...")

# Dispatch any tool from a slash command
result = ctx.dispatch_tool("terminal", {"command": "find . -name '*.py'"})
```

---

## Data Files & Durable State

```python
# Ship data files — read at import time
from pathlib import Path
_PLUGIN_DIR = Path(__file__).parent
_DATA_FILE = _PLUGIN_DIR / "data" / "languages.yaml"

# Durable state — use plugin_data_dir, never write to install tree
from plugins.plugin_storage import plugin_data_dir, plugin_db
state_file = plugin_data_dir("my-plugin") / "state.json"
conn = plugin_db("my-plugin")  # SQLite WAL mode
```

---

## Lazy Singletons

```python
from plugins.plugin_utils import lazy_singleton

@lazy_singleton
def get_client():
    return ExpensiveClient()  # runs exactly once
```

---

## Lazy-Install Optional Deps

```python
from tools.lazy_deps import ensure, FeatureUnavailable

def my_handler(args, **kwargs):
    try:
        ensure("my-plugin.my-backend")  # key must be in LAZY_DEPS
    except FeatureUnavailable as exc:
        return json.dumps({"error": str(exc)})
```

---

## Python Dependencies — The Reality

**There is no automatic install for native directory plugins.** `python_dependencies` is a **declaration seam only** — Hermes validates and surfaces with `pip install` hint, but **never auto-installs**.

| Method | How deps install |
|---|---|
| **Native dir** (`~/.hermes/plugins/`) | Manual — user runs `pip install` into Hermes venv |
| **Pip-distributed** (`pip install ...`) | Automatic — standard pip resolution |
| **Bundled** (in Hermes tree) | Lazy via `tools.lazy_deps.ensure()` |

---

## Validation & Debugging

```bash
hermes plugins doctor <path> --ci     # validate manifest + registration
hermes plugins list                   # show all discovered plugins
hermes plugins enable <name>          # opt-in enable
hermes plugins capabilities           # show declared capabilities
```

```bash
# Debug discovery
HERMES_PLUGINS_DEBUG=1 hermes plugins list

# Check logs
hermes logs --level WARNING | grep -i plugin
```

---

## Common Mistakes (from official docs)

| Mistake | Fix |
|---|---|
| Handler returns dict | Return `json.dumps(...)` |
| Missing `**kwargs` | Add `**kwargs` to handler signature |
| Handler raises | Catch all exceptions, return error JSON |
| Vague description | Be specific about what + when |
| Plugin not enabled | `hermes plugins enable <name>` |
| Wrong directory | Native: `~/.hermes/plugins/<name>/plugin.yaml` |
| Missing `__init__.py` | Native packages need both `plugin.yaml` + `__init__.py` |
| `register()` crashes | Plugin disabled, Hermes continues — check `~/.hermes/logs/errors.log` |
| Skills not loading | Need BOTH `provides_skills:` in plugin.yaml AND `ctx.register_skill()` |

---

## Critical Rules

1. **Restart required** — new tools bind at startup; a tool created mid-session is not visible until restart.
2. **A plugin load failure silently drops ALL its tools** — check `~/.hermes/logs/errors.log` FIRST.
3. **`register()` called exactly once at startup** — if it crashes, plugin is disabled but Hermes continues.
4. **`provides_skills:` + `ctx.register_skill()`** — both required for skills to appear in `<available_skills>`.
5. **Handler returns JSON string, never dict** — most common failure.
6. **Handler never raises** — catch all exceptions, return error JSON.
7. **Accept `**kwargs`** — Hermes may pass additional context in the future.
8. **Be specific in schema descriptions** — the LLM decides when to call your tool based on this.