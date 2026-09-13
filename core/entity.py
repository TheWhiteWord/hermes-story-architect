"""Entity extraction — parse story entity notes."""
import frontmatter
from pathlib import Path
from .constants import (
    REQUIRED_FIELDS, VALID_ROLES, VALID_STATUSES,
    SCENE_STATUSES, SEQUENCE_STATUSES, ACT_STATUSES,
    SCENE_TIMES_OF_DAY, SCENE_DRAMATIC_ROLES,
    VALUE_CHARGES, STRUCTURE_TYPES,
)
from .section_parser import list_sections


def extract_entity(note_path: Path, entity_type: str) -> dict:
    """Extract entity data from a note file.
    
    Returns dict with:
    - id: note stem (slug)
    - all frontmatter fields
    - sections: list of ## headings in body
    """
    post = frontmatter.load(note_path)
    body = post.content
    sections = list_sections(body)
    return {
        "id": note_path.stem,
        **dict(post.metadata),
        "sections": sections,
    }


def validate_entity(entity_type: str, frontmatter: dict) -> list[str]:
    """Validate entity frontmatter. Return list of warnings."""
    warnings = []

    for field in REQUIRED_FIELDS.get(entity_type, []):
        if field not in frontmatter:
            warnings.append(f"Missing required field: {field}")

    if entity_type == "character" and "story_role" in frontmatter:
        if frontmatter["story_role"] not in VALID_ROLES:
            warnings.append(f"Invalid story_role: {frontmatter['story_role']}")

    if entity_type == "plot" and "status" in frontmatter:
        if frontmatter["status"] not in VALID_STATUSES:
            warnings.append(f"Invalid status: {frontmatter['status']}")

    if entity_type == "scene":
        _validate_enum(frontmatter, "status", SCENE_STATUSES, warnings)
        _validate_enum(frontmatter, "time_of_day", SCENE_TIMES_OF_DAY, warnings, empty_ok=True)
        _validate_enum(frontmatter, "dramatic_role", SCENE_DRAMATIC_ROLES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "sequence":
        _validate_enum(frontmatter, "status", SEQUENCE_STATUSES, warnings)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    if entity_type == "act":
        _validate_enum(frontmatter, "status", ACT_STATUSES, warnings)
        _validate_enum(frontmatter, "value_open", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "value_close", VALUE_CHARGES, warnings, empty_ok=True)
        _validate_enum(frontmatter, "structure_type", STRUCTURE_TYPES, warnings, empty_ok=True)
        _validate_numeric(frontmatter, "order", warnings)

    return warnings


def _validate_enum(frontmatter: dict, field: str, valid: list[str], warnings: list[str], empty_ok: bool = False) -> None:
    """Append warning if frontmatter[field] is present and not in valid (unless empty_ok and empty)."""
    if field not in frontmatter:
        return
    val = frontmatter[field]
    if empty_ok and val == "":
        return
    if val not in valid:
        warnings.append(f"Invalid {field}: {val}")


def _validate_numeric(frontmatter: dict, field: str, warnings: list[str]) -> None:
    """Append warning if frontmatter[field] is present and not int/float."""
    if field not in frontmatter:
        return
    if not isinstance(frontmatter[field], (int, float)):
        warnings.append(f"Field {field} must be a number, got {type(frontmatter[field]).__name__}")


def update_sections(note_path: Path, sections: list[str]) -> None:
    """Update the sections field in a note's frontmatter."""
    post = frontmatter.load(note_path)
    post["sections"] = sections
    with open(note_path, 'w') as f:
        frontmatter.dump(post, f)
