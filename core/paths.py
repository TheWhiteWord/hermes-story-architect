"""Path builder/resolver — flat and nested entity paths."""
from pathlib import Path
from core.constants import ENTITY_FOLDERS, NESTED_ENTITIES


def build_entity_path(project_path: Path, entity_type: str, slug: str, frontmatter: dict = None) -> Path:
    """Build file path for any entity type.

    Nested entities (e.g. arc): project_path / folder / {parent_field} / {slug}.md
    Flat entities: project_path / folder / {slug}.md
    """
    folder = ENTITY_FOLDERS.get(entity_type, "")
    if entity_type in NESTED_ENTITIES:
        parent_id = (frontmatter or {}).get(NESTED_ENTITIES[entity_type], "")
        return project_path / folder / parent_id / f"{slug}.md"
    return project_path / folder / f"{slug}.md"


def find_entity_path(project_path: Path, entity_type: str, slug: str) -> Path | None:
    """Find existing file path for any entity type.

    For nested entities, searches subfolders. Returns None if not found.
    """
    folder = ENTITY_FOLDERS.get(entity_type, "")
    flat = project_path / folder / f"{slug}.md"
    if entity_type not in NESTED_ENTITIES:
        return flat if flat.exists() else None
    # Nested: check flat first, then search subfolders
    if flat.exists():
        return flat
    base = project_path / folder
    if not base.exists():
        return None
    for parent_dir in sorted(base.iterdir()):
        if parent_dir.is_dir() and not parent_dir.name.startswith("_") and not parent_dir.name.startswith("."):
            candidate = parent_dir / f"{slug}.md"
            if candidate.exists():
                return candidate
    return None
