"""story_dashboard tool — open project dashboard in preview pane."""
import json
import re
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
        from core.fountain_lexer import parse as fountain_parse, tokens_to_html
    except ImportError:
        from core.fountain_lexer import parse as fountain_parse, tokens_to_html

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
    # Strip emphasis markers from title page token text
    for pos in title_page:
        for tok in title_page[pos]:
            if isinstance(tok, dict) and tok.get('text'):
                tok['text'] = re.sub(r'\*{1,3}|_{1,3}', '', tok['text'])

    # ── Pre-rendered HTML ──
    # Filter out title page custom field tokens (tl:, tc:, etc.) — they appear
    # in both title_page dict and tokens list as action tokens
    script_tokens = [t for t in tokens if t.get('text') and not re.match(r'^(tl|tc|tr|cc|bl|br):\s', t.get('text', ''))]
    script_html = tokens_to_html(script_tokens)

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


def _build_title_page(project_frontmatter: dict) -> dict:
    """Build a title page dict from project.md frontmatter.

    Returns the {tl, tc, tr, cc, bl, br, hidden} structure expected by
    buildScriptView() in the dashboard. Fields are output-only — never indexed.
    """
    cc = []
    bl = []
    br = []

    title = project_frontmatter.get("screenplay_title", "")
    if title:
        cc.append({"text": title, "type": "title"})
    credit = project_frontmatter.get("credit", "")
    if credit:
        cc.append({"text": credit, "type": "credit"})
    author = project_frontmatter.get("author", "")
    if author:
        cc.append({"text": author, "type": "author"})

    draft_date = project_frontmatter.get("draft_date", "")
    if draft_date:
        bl.append({"text": draft_date, "type": "draft_date"})
    draft = project_frontmatter.get("draft", "")
    if draft:
        bl.append({"text": draft, "type": "draft"})

    contact = project_frontmatter.get("contact", "")
    if contact:
        br.append({"text": contact, "type": "contact"})

    return {"tl": [], "tc": [], "tr": [], "cc": cc, "bl": bl, "br": br, "hidden": []}


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
    """Open project dashboard in preview pane."""
    import tempfile
    import frontmatter as fm

    from core.config import load_plugin_config
    from core.db import get_dashboard_data, has_schema
    from .story_resolve import resolve_project

    config = load_plugin_config()
    vault_path = Path(config.get("vault_path", "~/story-vault")).expanduser()
    project = args["project"]

    try:
        project_path = resolve_project(project, vault_path)
    except ValueError as e:
        return json.dumps({"error": str(e)})

    db_path = project_path / ".story" / "story.db"
    if not db_path.exists():
        return json.dumps({"error": "Database not found. Run story_import first."})

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        if not has_schema(conn):
            return json.dumps({"error": "Database schema not found. Run story_import first."})
    finally:
        conn.close()

    # Get all dashboard data from DB in one call
    try:
        data = get_dashboard_data(project_path)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        # Find the exact line that failed
        lines = tb.strip().split("\n")
        last_line = lines[-1] if lines else "no traceback"
        return json.dumps({"error": f"Failed: {e}", "last_line": last_line, "full_tb": tb})

    return _render_dashboard(data, project_path, project)


def _render_dashboard(data: dict, project_path: Path, project: str) -> str:
    """Render dashboard HTML from get_dashboard_data() output."""
    import tempfile
    import frontmatter as fm

    dashboard_src = Path(__file__).parent.parent / "src" / "dashboard" / "story-dashboard.html"
    if not dashboard_src.exists():
        return json.dumps({"error": "Dashboard file not found in plugin"})

    screenplay_css_src = dashboard_src.parent / "screenplay.css"
    if not screenplay_css_src.exists():
        return json.dumps({"error": "Screenplay CSS file not found in plugin"})

    html = dashboard_src.read_text(encoding="utf-8")
    css = screenplay_css_src.read_text(encoding="utf-8")

    # Read project.md directly for title page fields (output-only, not in DB title_page)
    try:
        project_fm = fm.load(project_path / "project.md")
        project_frontmatter = dict(project_fm.metadata)
    except Exception:
        project_frontmatter = {}

    # Replace the external CSS link with inline CSS
    html = html.replace(
        '<link rel="stylesheet" href="screenplay.css">',
        f"<style>\n{css}\n</style>"
    )

    # Build all injections from get_dashboard_data output
    injections = f"window.__STORY_DATA__ = {json.dumps(data['story_data'])};"

    # Inject section content
    if data.get("sections"):
        injections += f"\nwindow.__SECTIONS__ = {json.dumps(data['sections'])};"

    # Inject screenplay stats from DB scene content
    scene_text = data.get("screenplay_text", "")
    if scene_text:
        try:
            stats = _compute_screenplay_stats(scene_text)
            if stats:
                stats["titlePage"] = _build_title_page(project_frontmatter)
                injections += f"\nwindow.__SCREENPLAY_STATS__ = {json.dumps(stats)};"
        except Exception:
            pass  # Dashboard still works without stats

    # Inject structural stats
    if data.get("structural_stats"):
        injections += f"\nwindow.__STRUCTURAL_STATS__ = {json.dumps(data['structural_stats'])};"

    html = html.replace(
        "// ─── Boot ─────────────────────────────────────────────────────────────────────",
        injections + "\n// ─── Boot ─────────────────────────────────────────────────────────────────────",
    )

    # Name temp file after the story title
    project_name = ""
    sd = data.get("story_data", {})
    if isinstance(sd, dict):
        project_name = sd.get("project", {}).get("name", "")
    else:
        for row in sd:
            if row.get("type") == "project" and row.get("name"):
                project_name = row["name"]
                break
    if not project_name:
        project_name = project
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
