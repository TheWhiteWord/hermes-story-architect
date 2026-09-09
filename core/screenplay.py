"""Screenplay integration — Fountain parsing via Better Fountain port.

Single source of truth — no screenplay-tools dependency.
"""
import re
from .constants import FUZZY_THRESHOLD
from .fountain_lexer import parse as fountain_parse, tokens_to_html, trim_character_extension

LOCATION_RE = re.compile(
    r'^(?:INT\.|EXT\.|EST\.|INT\./EXT\.|I/E\.)\s+(.+?)(?:\s*-\s*(?:DAY|NIGHT|DUSK|DAWN|LATER|CONTINUOUS|MOMENTS LATER))?$'
)


def extract_scenes(screenplay_content: str) -> list[dict]:
    """Extract scenes from Fountain content using our Better Fountain port."""
    result = fountain_parse(screenplay_content)
    scenes = []
    current = None
    
    for token in result['tokens']:
        if token['type'] == 'scene_heading':
            if current:
                scenes.append(current)
            current = {
                'heading': token.get('text') or '',
                'number': token.get('number'),
                'characters': [],
                'location': '',
                'content': token.get('text') or '',
                'content_html': '',
            }
        elif current is not None:
            text = token.get('text') or ''
            if text:
                current['content'] += '\n' + text
            
            if token['type'] == 'character':
                name = (token.get('character') or '').strip()
                if not name:
                    name = text  # Use raw text (preserves extensions like (V.O.))
                if name and name not in current['characters']:
                    current['characters'].append(name)
    
    if current:
        scenes.append(current)
    
    for i, scene in enumerate(scenes, 1):
        scene['id'] = i
        scene['content_html'] = tokens_to_html(result['tokens'])
    
    return scenes


def extract_location(heading: str) -> str | None:
    """Extract location from scene heading: 'INT. KITCHEN - NIGHT' → 'KITCHEN'."""
    match = LOCATION_RE.match(heading)
    return match.group(1).strip() if match else None


def match_character(name: str, characters: list[dict]) -> str | None:
    """Match dialogue character name to character slug."""
    from rapidfuzz import fuzz, process
    
    slug_to_name = {c['id']: c['name'] for c in characters}
    
    for slug, char_name in slug_to_name.items():
        if name.lower() == char_name.lower():
            return slug
    
    for slug, char_name in slug_to_name.items():
        if name.lower() in char_name.lower() or char_name.lower() in name.lower():
            return slug
    
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
    
    slug_to_name = {l['id']: l['name'] for l in locations}
    
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() == loc_name.lower():
            return slug
    
    for slug, loc_name in slug_to_name.items():
        if heading_location.lower() in loc_name.lower() or loc_name.lower() in heading_location.lower():
            return slug
    
    result = process.extractOne(heading_location, slug_to_name.values(), scorer=fuzz.token_set_ratio)
    if result and result[1] >= FUZZY_THRESHOLD:
        matched_name = result[0]
        for slug, loc_name in slug_to_name.items():
            if loc_name == matched_name:
                return slug
    
    return None
