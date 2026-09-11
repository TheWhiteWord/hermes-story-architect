"""Index generator — produce .story/index.yaml from vault notes."""
import yaml
from pathlib import Path
from .entity import extract_entity, validate_entity
from .screenplay import extract_scenes, match_character, match_location


def generate_index(project_path: Path) -> dict:
    """Main entry point: scan project folder, produce index dict."""
    characters = _parse_entities(project_path / "characters", "character")
    locations = _parse_entities(project_path / "locations", "location")
    worlds = _parse_entities(project_path / "worlds", "world")
    plots = _parse_entities(project_path / "plots", "plot")
    
    index = {
        "project": _parse_project(project_path, characters, locations, worlds, plots),
        "characters": characters,
        "locations": locations,
        "worlds": worlds,
        "plots": plots,
    }
    
    # Sync screenplay
    screenplay_path = project_path / "screenplay.fountain"
    if screenplay_path.exists():
        raw_scenes = extract_scenes(screenplay_path.read_text())
        scenes = []
        for scene in raw_scenes:
            # Match characters
            matched_chars = []
            for char_name in scene["characters"]:
                slug = match_character(char_name, index["characters"])
                if slug and slug not in matched_chars:
                    matched_chars.append(slug)
            # Match location
            loc_slug = match_location(scene.get("location", ""), index["locations"]) if scene.get("location") else ""
            # Only keep what the index needs (summary graph, not full content)
            scenes.append({
                "id": scene["id"],
                "heading": scene["heading"],
                "number": scene["number"],
                "characters": matched_chars,
                "location": loc_slug or "",
            })
        index["scenes"] = scenes
    
    # Update project with scene count
    index["project"]["scene_count"] = len(index.get("scenes", []))
    
    # Build cross-references (character scenes from screenplay)
    _enrich_from_screenplay(index)
    
    # Add labels to relationships
    _enrich_relationships(index)
    
    # Add descriptions to setups/payoffs
    _enrich_plots(index)
    
    # Validate
    _validate_index(index)
    
    return index


def _parse_project(project_path: Path, characters, locations, worlds, plots, scenes_count=0) -> dict:
    """Parse project.md and add count fields."""
    fm = project_path / "project.md"
    project = extract_entity(fm, "project") if fm.exists() else {}
    project["scene_count"] = scenes_count
    project["character_count"] = len(characters)
    project["location_count"] = len(locations)
    project["world_count"] = len(worlds)
    project["plot_count"] = len(plots)
    return project


def _enrich_relationships(index: dict) -> None:
    """Add label field to relationships (defaults to empty string, user fills in editor)."""
    for char in index.get("characters", []):
        for rel in char.get("relationships", []):
            if "label" not in rel:
                rel["label"] = ""


def _enrich_plots(index: dict) -> None:
    """Normalize plot setups/payoffs to {scene: heading, description: text}."""
    for plot in index.get("plots", []):
        plot["setups"] = [_normalize_beat(s) for s in plot.get("setups", [])]
        plot["payoffs"] = [_normalize_beat(p) for p in plot.get("payoffs", [])]


def _normalize_beat(beat):
    """Extract {scene, description} from note format {number, heading, description}."""
    if isinstance(beat, dict):
        heading = beat.get("heading") or beat.get("scene") or ""
        return {"scene": str(heading), "description": beat.get("description", "")}
    return {"scene": str(beat), "description": ""}


def _parse_entities(folder: Path, entity_type: str) -> list[dict]:
    """Parse all entities in a folder."""
    if not folder.exists():
        return []
    entities = []
    for note in sorted(folder.glob("*.md")):
        if note.name.startswith("_"):
            continue
        entity = extract_entity(note, entity_type)
        warnings = validate_entity(entity_type, entity)
        if warnings:
            print(f"Warnings for {note}: {warnings}")
        entities.append(entity)
    return entities


def _enrich_from_screenplay(index: dict) -> None:
    """Update character and location scenes from screenplay data."""
    char_scenes = {c["id"]: [] for c in index["characters"]}
    loc_scenes = {l["id"]: [] for l in index["locations"]}
    for scene in index.get("scenes", []):
        for char_id in scene["characters"]:
            if char_id in char_scenes:
                char_scenes[char_id].append({
                    "number": scene["id"],
                    "heading": scene["heading"],
                })
        loc_id = scene.get("location", "")
        if loc_id and loc_id in loc_scenes:
            loc_scenes[loc_id].append({
                "number": scene["id"],
                "heading": scene["heading"],
            })
    for char in index["characters"]:
        if char_scenes.get(char["id"]):
            char["scenes"] = char_scenes[char["id"]]
    for loc in index["locations"]:
        if loc_scenes.get(loc["id"]):
            loc["scenes"] = loc_scenes[loc["id"]]


def _validate_index(index: dict) -> None:
    """Validate cross-references."""
    char_ids = {c["id"] for c in index["characters"]}
    loc_ids = {l["id"] for l in index["locations"]}
    plot_ids = {p["id"] for p in index["plots"]}
    
    for char in index["characters"]:
        for rel in char.get("relationships", []):
            if rel["id"] not in char_ids:
                print(f"Warning: {char['id']} references unknown character {rel['id']}")
    
    for plot in index["plots"]:
        for char_id in plot.get("characters", []):
            if char_id not in char_ids:
                print(f"Warning: {plot['id']} references unknown character {char_id}")


def write_index(index: dict, output_path: Path) -> None:
    """Write index to YAML."""
    with open(output_path, 'w') as f:
        yaml.dump(index, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
