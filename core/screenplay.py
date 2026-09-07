"""Screenplay integration — Fountain parsing via screenplay-tools."""
import re
from .constants import FUZZY_THRESHOLD

LOCATION_RE = re.compile(
    r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$'
)


def extract_scenes(screenplay_content: str) -> list[dict]:
    """Extract scenes from screenplay content using screenplay-tools."""
    from screenplay_tools.fountain.parser import Parser
    
    parser = Parser()
    parser.add_text(screenplay_content)
    script = parser.script
    scenes = []
    current_scene = None
    
    for element in script.elements:
        if element.type.value == "HEADING":
            if current_scene:
                scenes.append(current_scene)
            current_scene = {
                "heading": element.text,
                "scene_number": getattr(element, "scene_number", ""),
                "characters": [],
                "location": extract_location(element.text),
            }
        elif element.type.value == "CHARACTER" and current_scene:
            name = element.name if hasattr(element, 'name') else ""
            if name and name not in current_scene["characters"]:
                current_scene["characters"].append(name)
    
    if current_scene:
        scenes.append(current_scene)
    
    for i, scene in enumerate(scenes, 1):
        scene["id"] = i
    
    return scenes


def extract_location(heading: str) -> str | None:
    """Extract location from scene heading: 'INT. KITCHEN - NIGHT' → 'KITCHEN'."""
    match = LOCATION_RE.match(heading)
    return match.group(1).strip() if match else None


def match_character(name: str, characters: list[dict]) -> str | None:
    """Match dialogue character name to character slug."""
    from rapidfuzz import fuzz, process
    
    slug_to_name = {c["id"]: c["name"] for c in characters}
    
    # Exact match (case-insensitive)
    for slug, char_name in slug_to_name.items():
        if name.lower() == char_name.lower():
            return slug
    
    # Check if cue is contained in name or vice versa (handles "MARA" vs "Mara Chen")
    for slug, char_name in slug_to_name.items():
        if name.lower() in char_name.lower() or char_name.lower() in name.lower():
            return slug
    
    # Fuzzy match with token_set_ratio (handles partial matches better)
    result = process.extractOne(name, slug_to_name.values(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= FUZZY_THRESHOLD:
        matched_name = result[0]
        for slug, char_name in slug_to_name.items():
            if char_name == matched_name:
                return slug
    
    return None


def match_location(heading_location: str, locations: list[dict]) -> str | None:
    """Match extracted location to location slug."""
    from rapidfuzz import fuzz, process
    
    if not heading_location:
        return None
    
    slug_to_name = {l["id"]: l["name"] for l in locations}
    
    # Exact match
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() == loc_name.lower():
            return slug
    
    # Check if one contains the other (handles "KITCHEN" vs "The Kitchen")
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() in loc_name.lower() or loc_name.lower() in heading_location.lower():
            return slug
    
    # Fuzzy match with token_set_ratio
    result = process.extractOne(heading_location, slug_to_name.values(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= FUZZY_THRESHOLD:
        matched_name = result[0]
        for slug, loc_name in slug_to_name.items():
            if loc_name == matched_name:
                return slug
    
    return None
