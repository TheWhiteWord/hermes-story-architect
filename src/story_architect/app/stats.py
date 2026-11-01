"""story_dashboard tool — open project dashboard in preview pane."""
import json
import re
from pathlib import Path

from story_architect.core.constants import ENTITY_SCHEMAS, UNFILLED

CSS_ORDER = ["base.css", "components.css", "views.css", "statistics.css",
             "graph.css", "value-graph.css",
             "panel-tabs.css", "scene-beats.css", "character-journey.css",
             "chat.css"]
# Load-bearing order. `panel-tabs.js` wraps `openPanel`/`closePanel` and the
# `show*Panel` functions, so it must come after everything it wraps; the two tab
# modules call `D.panelTabs.register` at load time, so they come after it; and
# `track-data.js` reads `D.valueModel`, so it comes after `value-graph.js`.
# A reorder here fails silently — the wrap unwires and the panel renders exactly
# as it did before, with no error. tests/test_dashboard.py pins the pairs.
JS_ORDER = [
    "core.js", "colors.js", "utils.js", "navigation.js", "data-load.js",
    "views/scenes.js", "views/locations.js", "views/plots.js",
    "views/relationships.js", "views/worlds.js", "views/story.js",
    "panels/panel-manager.js", "panels/entity-panels.js", "panels/memory-dialog.js",
    "panels/panel-tabs.js",
    "graph/network.js",
    "graph/value-graph.js",
    "graph/track-data.js",
    "panels/scene-beats-tab.js", "panels/character-journey-tab.js",
    "statistics/statistics.js", "statistics/charts.js",
    "script-view.js",
    "chat-api.js", "chat-md.js", "chat-render.js", "chat-app.js",
]

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


def _compute_screenplay_stats(screenplay_text, scene_ids=None):
    """Compute screenplay statistics from fountain text using fountain_lexer.

    Returns a dict suitable for JSON injection as window.__SCREENPLAY_STATS__.
    Returns None on any error — dashboard still works without stats.
    """
    try:
        from story_architect.core.fountain_lexer import parse as fountain_parse, tokens_to_html
    except ImportError:
        return None

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
        'sceneIds': scene_ids or [],
    }


def _hsl_from_name(name):
    """Generate a deterministic HSL color from a name string."""
    h = 0
    for c in name:
        h = (h * 31 + ord(c)) % 360
    return f'hsl({h}, 60%, 65%)'


def _slot(fm: dict, field: str, token_type: str) -> dict:
    """A title-page token, or a labelled reminder when the field is empty.

    An unfilled slot shows `<label>: N.A.` rather than nothing, so the reader can
    see which slots are open — otherwise a filled page and an empty one are
    structurally identical. The token carries `unfilled: True` so the dashboard
    styles it as a reminder rather than as typeset content; a printed page has
    no such distinction, and there the label is the whole signal.

    Always returns a token, never None. A slot that could be dropped would make
    the consumer index by position, and the first `cc` entry is the title *only*
    because it is written first — `screenplay_title` is empty in the fixture, and
    a position-based split put the credit line where the title belongs.
    """
    value = (fm.get(field) or "").strip()
    if value:
        return {"text": value, "type": token_type}
    label = ENTITY_SCHEMAS["project"].get(field, {}).get("label") or field.replace("_", " ").title()
    return {"text": f"{label}: {UNFILLED}", "type": f"{token_type}_unfilled", "unfilled": True}


def _build_title_page(project_frontmatter: dict) -> dict:
    """Build a title page dict from DB-backed project data.

    Returns the {tl, tc, tr, cc, bl, br, hidden} structure expected by
    buildScriptView() in the dashboard. Fields are output-only — never indexed.
    """
    cc, bl, br = [], [], []

    title = project_frontmatter.get("screenplay_title") or ""
    cc.append(_slot({"screenplay_title": title}, "screenplay_title", "title"))
    for field, token_type in (("credit", "credit"), ("author", "author")):
        cc.append(_slot(project_frontmatter, field, token_type))
    for field, token_type in (("draft_date", "draft_date"), ("draft", "draft")):
        bl.append(_slot(project_frontmatter, field, token_type))
    br.append(_slot(project_frontmatter, "contact", "contact"))

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


