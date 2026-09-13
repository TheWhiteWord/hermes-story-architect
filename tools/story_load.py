"""story_load tool — load a project's index and memory into context."""
import json
from pathlib import Path

import yaml


SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        },
        "structure_only": {
            "type": "boolean",
            "description": "Load only structure-index.yaml (story arc, dramatic metadata), skip index.yaml. Default false."
        }
    },
    "required": ["project"]
}


def handler(args: dict, **kwargs) -> str:
    """Load project index and memory into context."""
    from core.config import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    # Resolve project
    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    # Lazy mode: include_structure=true skips re-sending the index —
    # the LLM already has it from the initial story_load. Returns only structure.
    if args.get("structure_only", False):
        structure_index = {}
        structure_path = project_path / ".story" / "structure-index.yaml"
        if structure_path.exists():
            with open(structure_path) as f:
                structure_index = yaml.safe_load(f)
        return _response(
            confirmation=f"{project_path.name} — structure-index only",
            structure_index=structure_index,
        )

    # Read index
    index_path = project_path / ".story" / "index.yaml"
    if not index_path.exists():
        return json.dumps({"error": "No index found. Run story_index first."})

    with open(index_path) as f:
        index = yaml.safe_load(f)

    # Build confirmation
    confirmation = (
        f"Loaded {index['project']['name']} — "
        f"{len(index.get('scenes', []))} scenes, "
        f"{len(index.get('sequences', []))} sequences, "
        f"{len(index.get('acts', []))} acts, "
        f"{len(index.get('characters', []))} characters, "
        f"{len(index.get('locations', []))} locations, "
        f"{len(index.get('plots', []))} plots."
    )

    # Read memory
    memory_path = project_path / ".story" / "memory.md"
    memory = ""
    if memory_path.exists():
        memory = memory_path.read_text()

    return _response(
        confirmation=confirmation,
        project=index["project"],
        index=index,
        memory=memory,
    )


def _response(**kwargs) -> str:
    """Wrap kwargs with loaded:true."""
    return json.dumps({"loaded": True, **kwargs})
