"""story_dashboard tool — open project dashboard in preview pane."""
import json
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "project": {
            "type": "string",
            "description": "Project slug or name"
        }
    },
    "required": ["project"],
    "description": "Open the story dashboard in the preview pane. After calling this tool, pass the returned dashboard_url to desktop_preview(action=open, url=...) so the user can see it."
}


def _compute_screenplay_stats(screenplay_text):
    """Compute screenplay statistics from fountain text using fountain_lexer.

    Returns a dict suitable for JSON injection as window.__SCREENPLAY_STATS__.
    Returns None on any error — dashboard still works without stats.
    """
    try:
        from ..core.fountain_lexer import parse as fountain_parse
    except ImportError:
        from core.fountain_lexer import parse as fountain_parse

    parsed = fountain_parse(screenplay_text)
    tokens = parsed.get('tokens', [])

    # ── Length stats ──
    lines = screenplay_text.split('\n')
    words = screenplay_text.split()
    scenes = [t for t in tokens if t['type'] == 'scene_heading']
    length_stats = {
        'pagesWhole': max(1, len(lines) // 52),
        'scenes': len(scenes),
        'words': len(words),
        'characters': len(screenplay_text),
        'lines': len(lines),
    }

    # ── Duration stats ──
    length_action = parsed.get('lengthAction', 0)
    length_dialogue = parsed.get('lengthDialogue', 0)

    # Build 20-bucket duration charts
    BUCKETS = 20
    bucket_size = max(1, len(tokens) // BUCKETS)
    lchart_action = []
    lchart_dialogue = []
    for b in range(BUCKETS):
        start = b * bucket_size
        end = min(len(tokens), (b + 1) * bucket_size)
        slice_tokens = tokens[start:end]
        a = sum((len(t['text'].split()) / 200) * 60 for t in slice_tokens if t['type'] == 'action')
        d = sum((len(t['text'].split()) / 200) * 60 for t in slice_tokens if t['type'] == 'dialogue')
        lchart_action.append(round(a, 1))
        lchart_dialogue.append(round(d, 1))

    duration_stats = {
        'total': length_action + length_dialogue,
        'action': length_action,
        'dialogue': length_dialogue,
        'lengthchart_action': lchart_action,
        'lengthchart_dialogue': lchart_dialogue,
    }

    # ── Character stats ──
    char_map = {}
    for t in tokens:
        if t['type'] == 'dialogue' and t.get('character'):
            name = t['character']
            if name not in char_map:
                char_map[name] = {
                    'name': name,
                    'color': _hsl_from_name(name),
                    'speakingParts': 0,
                    'secondsSpoken': 0,
                    'wordsSpoken': 0,
                    'monologues': 0,
                }
            char_map[name]['speakingParts'] += 1
            char_map[name]['secondsSpoken'] += t.get('time', 0)
            char_map[name]['wordsSpoken'] += len(t['text'].split())
            if (t.get('time', 0) or 0) > 30:
                char_map[name]['monologues'] += 1

    char_list = sorted(char_map.values(), key=lambda c: c['secondsSpoken'], reverse=True)
    # Round seconds for clean JSON
    for c in char_list:
        c['secondsSpoken'] = round(c['secondsSpoken'], 1)

    character_stats = {
        'characterCount': len(char_list),
        'monologues': sum(c['monologues'] for c in char_list),
        'characters': char_list,
    }

    # ── Location stats ──
    loc_map = {}
    for s in scenes:
        loc = _parse_scene_location(s['text'])
        if loc:
            name = loc['name']
            if name not in loc_map:
                loc_map[name] = {
                    'name': name,
                    'color': _hsl_from_name(name),
                    'number_of_scenes': 0,
                    'interior_exterior': set(),
                    'times_of_day': set(),
                }
            loc_map[name]['number_of_scenes'] += 1
            if loc.get('interior'):
                loc_map[name]['interior_exterior'].add('int')
            if loc.get('exterior'):
                loc_map[name]['interior_exterior'].add('ext')
            if loc.get('time_of_day'):
                loc_map[name]['times_of_day'].add(loc['time_of_day'].lower())

    location_stats = {
        'locationsCount': len(loc_map),
        'locations': [
            {
                'name': v['name'],
                'color': v['color'],
                'number_of_scenes': v['number_of_scenes'],
                'interior_exterior': sorted(v['interior_exterior']),
                'times_of_day': sorted(v['times_of_day']),
            }
            for v in sorted(loc_map.values(), key=lambda l: l['number_of_scenes'], reverse=True)
        ],
    }

    # ── Scene stats ──
    type_counts = {'int': 0, 'ext': 0, 'mixed': 0}
    time_counts = {}
    scene_list = []
    for s in scenes:
        loc = _parse_scene_location(s['text'])
        loc_type = 'mixed' if (loc and loc.get('interior') and loc.get('exterior')) else \
                   'int' if (loc and loc.get('interior')) else \
                   'ext' if (loc and loc.get('exterior')) else 'other'
        loc_time = (loc.get('time_of_day') or 'unspecified').lower() if loc else 'unspecified'

        type_counts[loc_type] = type_counts.get(loc_type, 0) + 1
        time_counts[loc_time] = time_counts.get(loc_time, 0) + 1

        scene_list.append({
            'text': s['text'],
            'number': s.get('number', ''),
            'locType': loc_type,
            'locTime': loc_time,
        })

    scene_stats = {
        'scenes': scene_list,
        'typeCounts': type_counts,
        'timeCounts': time_counts,
    }

    # ── Title page ──
    title_page = parsed.get('title_page', {'tl': [], 'tc': [], 'tr': [], 'cc': [], 'bl': [], 'br': []})

    # ── Pre-rendered HTML ──
    script_html = parsed.get('scriptHtml', '')

    return {
        'lengthStats': length_stats,
        'durationStats': duration_stats,
        'characterStats': character_stats,
        'locationStats': location_stats,
        'sceneStats': scene_stats,
        'titlePage': title_page,
        'scriptHtml': script_html,
    }


def _hsl_from_name(name):
    """Generate a deterministic HSL color from a name string."""
    h = 0
    for c in name:
        h = (h * 31 + ord(c)) % 360
    return f'hsl({h}, 60%, 65%)'


def _parse_scene_location(heading):
    """Parse scene heading text into location info. Minimal version of fountain_lexer.parse_location."""
    import regex as re
    match = re.match(r'^[ \t]*([.](?![.])|(?:[*]{0,3}_?)(?:int[.]?\/ext|int[.]?\/e|ext|est|int|i[.]?\/e)[. ])(.+?)(#[-.0-9a-z]+#)?$', heading, re.IGNORECASE)
    if not match:
        return None
    location_text = match.group(2)
    split = re.search(r'(.*)[-–—−](.*)', location_text)
    return {
        'name': split.group(1).strip() if split else location_text.strip(),
        'interior': 'I' in match.group(1),
        'exterior': 'EX' in match.group(1) or 'E.' in match.group(1),
        'time_of_day': split.group(2).strip() if split else '',
    }


def handler(args: dict, **kwargs) -> str:
    """Open project dashboard in the preview pane."""
    import tempfile
    import yaml

    from .. import load_plugin_config
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    index_path = project_path / ".story" / "index.yaml"
    if not index_path.exists():
        return json.dumps({"error": "Index not found. Run story_index first."})

    dashboard_src = Path(__file__).parent.parent / "src" / "dashboard" / "story-dashboard.html"
    if not dashboard_src.exists():
        return json.dumps({"error": "Dashboard file not found in plugin"})

    screenplay_css_src = dashboard_src.parent / "screenplay.css"
    if not screenplay_css_src.exists():
        return json.dumps({"error": "Screenplay CSS file not found in plugin"})

    # Read index.yaml, convert to JSON, inject inline — avoids fetch('file://') which Electron blocks
    yaml_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    html = dashboard_src.read_text(encoding="utf-8")
    css = screenplay_css_src.read_text(encoding="utf-8")

    # Replace the external CSS link with inline CSS (so it works from any location)
    html = html.replace(
        '<link rel="stylesheet" href="screenplay.css">',
        f"<style>\n{css}\n</style>"
    )

    injection = f"window.__STORY_DATA__ = {json.dumps(yaml_data)};"
    html = html.replace(
        "// ─── Boot ─────────────────────────────────────────────────────────────────────",
        injection + "\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
    )

    # Inject screenplay text the same way — fetch('file://') is blocked in Electron
    screenplay_path = project_path / "screenplay.fountain"
    if screenplay_path.exists():
        screenplay_text = screenplay_path.read_text(encoding="utf-8")
        html = html.replace(
            "// ─── Boot ─────────────────────────────────────────────────────────────────────",
            f'window.__SCREENPLAY_TEXT__ = {json.dumps(screenplay_text)};\n// ─── Boot ─────────────────────────────────────────────────────────────────────',
        )

        # Inject screenplay stats (computed server-side)
        try:
            stats = _compute_screenplay_stats(screenplay_text)
            if stats:
                stats_json = json.dumps(stats)
                html = html.replace(
                    "// ─── Boot ─────────────────────────────────────────────────────────────────────",
                    f"window.__SCREENPLAY_STATS__ = {stats_json};\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
                )
        except Exception:
            pass  # Dashboard still works without stats

    # Name temp file after the story title
    project_name = (yaml_data.get("project", {}).get("name") or project).strip()
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name).strip().replace(" ", "_")
    tmp_dir = Path(tempfile.gettempdir())
    tmp_path = tmp_dir / f"{safe_name}.html"
    tmp_path.write_text(html, encoding="utf-8")

    return json.dumps({
        "success": True,
        "message": f"Dashboard opened for {project}",
        "dashboard_url": f"file://{tmp_path}",
        "project": project,
    })
