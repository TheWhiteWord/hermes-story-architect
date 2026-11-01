"""Fountain lexer — faithful port of Better Fountain's afterwriting-parser.js.

Ported from: /home/davide/.vscode/extensions/piersdeseilligny.betterfountain-1.14.2/out/afterwriting-parser.js
Uses Python `regex` module for Unicode property escape support (\\p{Ll}, \\p{Lu}, etc.)
"""
import regex as re

# ─── Regex patterns (copied verbatim from Better Fountain lines 29-55) ───

REGEX = {
    'title_page': re.compile(r'(title|credit|author[s]?|source|notes|draft date|date|watermark|contact( info)?|revision|copyright|font|tl|tc|tr|cc|br|bl|header|footer)\:.*', re.IGNORECASE),
    'section': re.compile(r'^[ \t]*(#+)(?: *)(.*)'),
    'synopsis': re.compile(r'^[ \t]*(?:\=(?!\=+))(.*)'),
    'scene_heading': re.compile(r'^[ \t]*([.](?![.])|(?:[*]{0,3}_?)(?:int[.]?\/ext|int[.]?\/e|ext|est|int|i[.]?\/e)[. ])(.+?)(#[-.0-9a-z]+#)?$', re.IGNORECASE),
    'scene_number': re.compile(r'#(.+)#'),
    'transition': re.compile(r'^[ \t]*((?:FADE (?:TO BLACK|OUT)|CUT TO BLACK)\.|.+ TO\:|^TO\:)$'),
    'dialogue': re.compile(r'^[ \t]*(\*_+[^\p{Ll}\p{Lo}\p{So}\r\n]*)(\^?)?(?:\n(?!\n+))([\s\S]+)', re.UNICODE),
    'character': re.compile(r'^[ \t]*(?![#!]|((\[\[))|(SUPERIMPOSE:))(((?!@)[^\p{Ll}\r\n]*?\p{Lu}[^\p{Ll}\r\n]*?)|((@)[^\r\n]*?))(\(.*\))?(\s*\^)?$', re.UNICODE),
    'parenthetical': re.compile(r'^[ \t]*(\(.+\))$'),
    'action': re.compile(r'^(.+)'),
    'centered': re.compile(r'^[ \t]*(?:> *)(.+)(?: *<)(\n.+)*'),
    'page_break': re.compile(r'^\={3,}$'),
    'line_break': re.compile(r'^ {2}$'),
    'note_inline': re.compile(r'(?:\[\[(?!\[))([\s\S]+?)(?:\]\](?!\[))'),
    'emphasis': re.compile(r'( _|\*{1,3}|_\*{1,3}|\*{1,3}_)(.+)( _|\*{1,3}|_\*{1,3}|\*{1,3}_)'),
    'bold_italic_underline': re.compile(r'(_{1}\*{3}(?=.+\*{3}_{1})|\*{3}_{1}(?=.+_{1}\*{3}))(.+?)(\*{3}_{1}|_{1}\*{3})'),
    'bold_underline': re.compile(r'(_{1}\*{2}(?=.+\*{2}_{1})|\*{2}_{1}(?=.+_{1}\*{2}))(.+?)(\*{2}_{1}|_{1}\*{2})'),
    'italic_underline': re.compile(r'(?:_{1}\*{1}(?=.+\*{1}_{1})|\*{1}_{1}(?=.+_{1}\*{1}))(.+?)(\*{1}_{1}|_{1}\*{1})'),
    'bold_italic': re.compile(r'(\*{3}(?=.+\*{3}))(.+?)(\*{3})'),
    'bold': re.compile(r'(\*{2}(?=.+\*{2}))(.+?)(\*{2})'),
    'italic': re.compile(r'(\*{1}(?=.+\*{1}))(.+?)(\*{1})'),
    'link': re.compile(r'\[?\[([^\[\]]*)\)]?\('),
    'lyric': re.compile(r'^(\~.+)'),
    'underline': re.compile(r'(_{1}(?=.+_{1}))(.+?)(_{1})'),
}

# ─── Module-level regex aliases ───

CHARACTER_RE = REGEX['character']
SCENE_HEADING_RE = REGEX['scene_heading']
TRANSITION_RE = REGEX['transition']
SECTION_RE = REGEX['section']
SYNOPSIS_RE = REGEX['synopsis']
PARENTHETICAL_RE = REGEX['parenthetical']
CENTERED_RE = REGEX['centered']
PAGE_BREAK_RE = REGEX['page_break']
LYRIC_RE = REGEX['lyric']
NOTE_INLINE_RE = REGEX['note_inline']
BONEYARD_START_RE = re.compile(r'/\*')
BONEYARD_END_RE = re.compile(r'\*/')

# ─── Title page positioning (from BF titlePageDisplay) ───

TITLE_PAGE_DISPLAY = {
    'title': {'position': 'cc', 'index': 0},
    'credit': {'position': 'cc', 'index': 1},
    'author': {'position': 'cc', 'index': 2},
    'authors': {'position': 'cc', 'index': 3},
    'source': {'position': 'cc', 'index': 4},
    'watermark': {'position': 'hidden', 'index': -1},
    'font': {'position': 'hidden', 'index': -1},
    'header': {'position': 'hidden', 'index': -1},
    'footer': {'position': 'hidden', 'index': -1},
    'notes': {'position': 'bl', 'index': 0},
    'copyright': {'position': 'bl', 'index': 1},
    'revision': {'position': 'br', 'index': 0},
    'date': {'position': 'br', 'index': 1},
    'draft_date': {'position': 'br', 'index': 2},
    'contact': {'position': 'br', 'index': 3},
    'contact_info': {'position': 'br', 'index': 4},
    'br': {'position': 'br', 'index': -1},
    'bl': {'position': 'bl', 'index': -1},
    'tr': {'position': 'tr', 'index': -1},
    'tc': {'position': 'tc', 'index': -1},
    'tl': {'position': 'tl', 'index': -1},
    'cc': {'position': 'cc', 'index': -1},
}

# ─── Token creation (from token.js lines 4-66) ───

def create_token(text, cursor, line, new_line_length, type=None):
    """Create a token dict matching Better Fountain's token structure."""
    t = {
        'text': text,
        'type': type,
        'start': cursor,
        'end': cursor,
        'line': line,
        'ignore': False,
        'number': None,
        'dual': None,
        'html': None,
        'level': None,
        'time': None,
        'character': None,
        'index': -1,
        'takeNumber': -1,
        'original_line': None,
    }
    if text:
        t['end'] = cursor + len(text) - 1 + new_line_length
    return t


# ─── Character utilities (from utils.js) ───

def trim_character_extension(character):
    """Remove character extension like (V.O.) or (CONT'D)."""
    return re.sub(r'[ \t]*(\(.*\))[ \t]*([ \t]*\^)?$', '', character).strip()


def trim_character_force_symbol(character):
    """Remove @ prefix from character cue."""
    return re.sub(r'^[ \t]*@', '', character)


def parse_location_information(match):
    """Parse regex match into location info."""
    if match and len(match.groups()) >= 3:
        location_text = match.group(2)
        split = re.search(r'(.*)[-–—−](.*)', location_text)
        return {
            'name': split.group(1).strip() if split else location_text.strip(),
            'interior': 'I' in match.group(1),
            'exterior': 'EX' in match.group(1) or 'E.' in match.group(1),
            'time_of_day': split.group(2).strip() if split else '',
        }
    return None


def classify_line(line, prev_type=None):
    """Classify a single line without full state machine."""
    stripped = line.strip()
    if stripped == '':
        return 'separator'
    if SCENE_HEADING_RE.match(stripped):
        return 'scene_heading'
    if TRANSITION_RE.match(stripped):
        return 'transition'
    if SECTION_RE.match(stripped):
        return 'section'
    if SYNOPSIS_RE.match(stripped):
        return 'synopsis'
    if CENTERED_RE.match(stripped):
        return 'centered'
    if PAGE_BREAK_RE.match(stripped):
        return 'page_break'
    if LYRIC_RE.match(stripped):
        return 'lyric'
    if CHARACTER_RE.match(stripped):
        return 'character'
    if prev_type == 'character':
        if PARENTHETICAL_RE.match(stripped):
            return 'parenthetical'
        return 'dialogue'
    return 'action'


def parse_location(heading):
    """Parse scene heading string into location info. Returns None if not a heading."""
    match = SCENE_HEADING_RE.match(heading)
    if not match:
        return None
    return parse_location_information(match)


def tokenize(script):
    """Parse Fountain screenplay and return token list."""
    return parse(script)['tokens']


def extract_scene_content(fountain, scene_index):
    """Extract raw content for a scene by index."""
    tokens = tokenize(fountain)
    scenes = [t for t in tokens if t['type'] == 'scene_heading']
    if scene_index >= len(scenes):
        return ''
    lines = fountain.split('\n')
    start_line = scenes[scene_index]['line']
    end_line = scenes[scene_index + 1]['line'] if scene_index + 1 < len(scenes) else len(lines)
    return '\n'.join(lines[start_line:end_line])


def fountain_to_html(fountain):
    """Convert Fountain text to HTML."""
    tokens = tokenize(fountain)
    return tokens_to_html(tokens)


# ─── Main parser (from afterwriting-parser.js lines 126-749) ───

def parse(original_script, cfg=None, generate_html=False):
    """Parse Fountain screenplay into tokens.

    Faithful port of Better Fountain's parse() function.
    """
    if cfg is None:
        cfg = {
            'print_notes': True,
            'print_dialogue_numbers': False,
            'use_dual_dialogue': True,
            'merge_multiple_empty_lines': False,
            'each_scene_on_new_page': False,
        }
    emptytitlepage = True
    new_line_length = 2 if '\r\n' in original_script else 1
    lines = re.split(r'\r\n|\r|\n', original_script)

    result = {
        'title_page': {'tl': [], 'tc': [], 'tr': [], 'cc': [], 'bl': [], 'br': [], 'hidden': []},
        'tokens': [],
        'scriptHtml': '',
        'titleHtml': '',
        'lengthAction': 0,
        'lengthDialogue': 0,
        'tokenLines': {},
        'properties': {
            'sceneLines': [],
            'scenes': [],
            'sceneNames': [],
            'titleKeys': [],
            'firstTokenLine': float('inf'),
            'fontLine': -1,
            'lengthAction': 0,
            'lengthDialogue': 0,
            'characters': {},
            'locations': {},
            'structure': [],
        }
    }

    if not original_script:
        return result

    # State variables
    nested_comments = 0
    cache_state_for_comment = 'normal'
    current = 0
    scene_number = 1
    current_depth = 0
    last_title_page_token = None
    last_was_separator = False
    token_category = 'none'
    last_character_index = 0
    dual_right = False
    state = 'normal'
    previous_character = None
    title_page_started = False
    ignored_last_token = False
    take_count = 1
    length_action_so_far = 0
    length_dialogue_so_far = 0

    def push_token(token):
        result['tokens'].append(token)
        if token['line'] is not None:
            result['tokenLines'][token['line']] = len(result['tokens']) - 1

    def update_previous_scene_length():
        nonlocal length_action_so_far, length_dialogue_so_far
        action = result['lengthAction'] - length_action_so_far
        dialogue = result['lengthDialogue'] - length_dialogue_so_far
        length_action_so_far = result['lengthAction']
        length_dialogue_so_far = result['lengthDialogue']
        if result['properties']['scenes']:
            result['properties']['scenes'][-1]['actionLength'] = action
            result['properties']['scenes'][-1]['dialogueLength'] = dialogue

    def latest_section_or_scene(depth, condition):
        if depth <= 0:
            return None
        elif depth == 1:
            items = [s for s in result['properties']['structure'] if condition(s)]
            return items[-1] if items else None
        else:
            prev = latest_section_or_scene(depth - 1, condition)
            if prev and prev.get('children'):
                children = [c for c in prev['children'] if condition(c)]
                if children:
                    return children[-1]
            return prev

    def latest_section(depth):
        return latest_section_or_scene(depth, lambda t: t.get('section'))

    def process_inline_note(text, linenumber):
        notes = REGEX['note_inline'].findall(text)
        if not notes:
            return 0
        irrelevant_length = 0
        level = latest_section_or_scene(current_depth + 1, lambda _: True)
        if level:
            level['notes'] = level.get('notes', [])
            for note in notes:
                level['notes'].append({'note': note, 'line': linenumber})
                irrelevant_length += len(note) + 4
        else:
            for note in notes:
                result['properties']['structure'].append({
                    'text': note, 'id': '/' + str(linenumber), 'isnote': True,
                    'children': [], 'level': 0, 'notes': [], 'section': False, 'synopses': []
                })
                irrelevant_length += len(note) + 4
        return irrelevant_length

    def calculate_dialogue_duration(text):
        duration = 0
        sanitized = re.sub(r'[^\w]', '', text)
        duration += (len(sanitized) / 3) * 0.1945548
        # JS: dialogue.match(/(\.|\?|\!|\:) |(\, )/g) returns full match strings
        # JS uses punct[0].length * 0.75 + punct[1].length * 0.3 (first=period, second=comma)
        punct = re.findall(r'(?:\.|\?|\!|\:) |\, ', text)
        if punct:
            duration += 0.75 * len(punct[0])
            if len(punct) > 1:
                duration += 0.3 * len(punct[1])
        return duration

    def process_dialogue_block(token):
        text_without_notes = REGEX['note_inline'].sub('', token['text'])
        process_inline_note(token['text'], token['line'])
        token['time'] = calculate_dialogue_duration(text_without_notes)
        if not cfg.get('print_notes'):
            token['text'] = text_without_notes
            if token['text'].strip() == '':
                token['ignore'] = True
        result['lengthDialogue'] += token['time']

    def process_action_block(token):
        irrelevant = process_inline_note(token['text'], token['line'])
        token['time'] = (len(token['text']) - irrelevant) / 20
        if not cfg.get('print_notes'):
            token['text'] = REGEX['note_inline'].sub('', token['text'])
            if token['text'].strip() == '':
                token['ignore'] = True
        result['lengthAction'] += token['time']

    def slugify(text):
        return re.sub(r'-+$', '', re.sub(r'^-+', '', re.sub(r'-{2,}', '-', re.sub(r'[^\w-]+', '', re.sub(r'\s+', '-', text.lower())))))

    lines_length = len(lines)

    for i in range(lines_length):
        text = lines[i]

        # Handle boneyard (comments) with nesting
        parts = re.split(r'(\/\*|\*\/)', text)
        new_parts = []
        for part in parts:
            if part == '/*':
                nested_comments += 1
            elif part == '*/':
                nested_comments -= 1
            elif nested_comments == 0:
                new_parts.append(part)
        text = ''.join(new_parts)

        if nested_comments and state != 'ignore':
            cache_state_for_comment = state
            state = 'ignore'
        elif state == 'ignore':
            state = cache_state_for_comment
        if nested_comments == 0 and state == 'ignore':
            state = cache_state_for_comment

        thistoken = create_token(text, current, i, new_line_length)
        thistoken['original_line'] = i + 1
        current = thistoken['end'] + 1

        # Empty line handling
        if text.strip() == '' and text != '  ':
            skip_separator = (cfg.get('merge_multiple_empty_lines') and last_was_separator) or (ignored_last_token and len(result['tokens']) > 1 and result['tokens'][-1]['type'] == 'separator')
            if ignored_last_token:
                ignored_last_token = False
            if state == 'dialogue':
                push_token(create_token(None, None, None, None, 'dialogue_end'))
            if state == 'dual_dialogue':
                push_token(create_token(None, None, None, None, 'dual_dialogue_end'))
            state = 'normal'
            if skip_separator or state == 'title_page':
                continue
            dual_right = False
            thistoken['type'] = 'separator'
            last_was_separator = True
            push_token(thistoken)
            continue

        token_category = 'script'

        # Title page detection
        if not title_page_started and REGEX['title_page'].match(thistoken['text']):
            state = 'title_page'

        if state == 'title_page':
            if REGEX['title_page'].match(thistoken['text']):
                colon_idx = thistoken['text'].find(':')
                thistoken['type'] = thistoken['text'][:colon_idx].lower().replace(' ', '_')
                thistoken['text'] = thistoken['text'][colon_idx + 1:].strip()
                last_title_page_token = thistoken
                keyformat = TITLE_PAGE_DISPLAY.get(thistoken['type'])
                if keyformat:
                    thistoken['index'] = keyformat['index']
                    result['title_page'][keyformat['position']].append(thistoken)
                    emptytitlepage = False
                title_page_started = True
                continue
            elif title_page_started and last_title_page_token:
                last_title_page_token['text'] += ('\n' if last_title_page_token['text'] else '') + thistoken['text'].strip()
                continue

        # Normal state parsing
        if state == 'normal':
            if REGEX['line_break'].match(thistoken['text']):
                token_category = 'none'
            elif result['properties']['firstTokenLine'] == float('inf'):
                result['properties']['firstTokenLine'] = thistoken['line']

            scene_heading_match = REGEX['scene_heading'].match(thistoken['text'])
            if scene_heading_match:
                thistoken['text'] = re.sub(r'^\.', '', thistoken['text'])
                thistoken['type'] = 'scene_heading'
                thistoken['number'] = str(scene_number)
                scene_num_match = REGEX['scene_number'].search(thistoken['text'])
                if scene_num_match:
                    thistoken['text'] = REGEX['scene_number'].sub('', thistoken['text']).strip()
                    thistoken['number'] = scene_num_match.group(1)

                cobj = {
                    'text': thistoken['text'],
                    'children': None,
                    'range': {'start': {'line': thistoken['line'], 'character': 0}, 'end': {'line': thistoken['line'], 'character': len(thistoken['text'])}},
                }
                if current_depth == 0:
                    cobj['id'] = '/' + str(thistoken['line'])
                    result['properties']['structure'].append(cobj)
                else:
                    level = latest_section(current_depth)
                    if level:
                        cobj['id'] = level['id'] + '/' + str(thistoken['line'])
                        level['children'].append(cobj)
                    else:
                        cobj['id'] = '/' + str(thistoken['line'])
                        result['properties']['structure'].append(cobj)

                update_previous_scene_length()
                result['properties']['scenes'].append({
                    'scene': thistoken['number'],
                    'text': thistoken['text'],
                    'line': thistoken['line'],
                    'actionLength': 0,
                    'dialogueLength': 0,
                })
                result['properties']['sceneLines'].append(thistoken['line'])
                result['properties']['sceneNames'].append(thistoken['text'])

                location = parse_location_information(scene_heading_match)
                if location:
                    location_slug = slugify(location['name'])
                    if location_slug in result['properties']['locations']:
                        values = result['properties']['locations'][location_slug]
                        if not any(it['scene_number'] == scene_number for it in values):
                            values.append({'scene_number': scene_number, 'line': thistoken['line'], **location})
                    else:
                        result['properties']['locations'][location_slug] = [{'scene_number': scene_number, 'line': thistoken['line'], **location}]

                scene_number += 1

            elif thistoken['text'] and thistoken['text'][0] == '!':
                thistoken['type'] = 'action'
                thistoken['text'] = thistoken['text'][1:]
                process_action_block(thistoken)

            elif REGEX['centered'].match(thistoken['text']):
                thistoken['type'] = 'centered'
                thistoken['text'] = re.sub(r'>|<', '', thistoken['text']).strip()

            elif REGEX['transition'].match(thistoken['text']):
                thistoken['text'] = re.sub(r'^> ?', '', thistoken['text'])
                thistoken['type'] = 'transition'

            elif REGEX['synopsis'].match(thistoken['text']):
                match = REGEX['synopsis'].match(thistoken['text'])
                thistoken['text'] = match.group(1)
                thistoken['type'] = 'synopsis' if thistoken['text'] else 'separator'
                level = latest_section_or_scene(current_depth + 1, lambda _: True)
                if level:
                    level['synopses'] = level.get('synopses', [])
                    level['synopses'].append({'synopsis': thistoken['text'], 'line': thistoken['line']})

            elif REGEX['section'].match(thistoken['text']):
                match = REGEX['section'].match(thistoken['text'])
                thistoken['level'] = len(match.group(1))
                thistoken['text'] = match.group(2)
                thistoken['type'] = 'section'
                cobj = {
                    'text': thistoken['text'],
                    'level': thistoken['level'],
                    'children': [],
                    'range': {'start': {'line': thistoken['line'], 'character': 0}, 'end': {'line': thistoken['line'], 'character': len(thistoken['text'])}},
                    'section': True,
                }
                current_depth = thistoken['level']
                level = current_depth > 1 and latest_section_or_scene(current_depth, lambda t: t.get('section') and t.get('level', 0) < current_depth)
                if current_depth == 1 or not level:
                    cobj['id'] = '/' + str(thistoken['line'])
                    result['properties']['structure'].append(cobj)
                else:
                    cobj['id'] = level['id'] + '/' + str(thistoken['line'])
                    level['children'].append(cobj)

            elif REGEX['page_break'].match(thistoken['text']):
                thistoken['text'] = ''
                thistoken['type'] = 'page_break'

            elif (REGEX['character'].match(thistoken['text']) and
                  i != lines_length and i != lines_length - 1 and
                  ((lines[i + 1].strip() == '') == (lines[i + 1] == '  '))):
                state = 'dialogue'
                thistoken['type'] = 'character'
                thistoken['takeNumber'] = take_count
                take_count += 1
                thistoken['text'] = trim_character_force_symbol(thistoken['text'])

                if thistoken['text'].endswith('^'):
                    if cfg.get('use_dual_dialogue'):
                        state = 'dual_dialogue'
                        dialogue_tokens = ['dialogue', 'character', 'parenthetical']
                        while last_character_index < len(result['tokens']) and result['tokens'][last_character_index]['type'] in dialogue_tokens:
                            result['tokens'][last_character_index]['dual'] = 'left'
                            last_character_index += 1
                        foundmatch = False
                        temp_index = len(result['tokens']) - 1
                        while not foundmatch:
                            temp_index -= 1
                            tok_type = result['tokens'][temp_index]['type']
                            if tok_type == 'dialogue_end':
                                # BF uses splice(temp_index) which removes ALL tokens from here onwards
                                # This also removes the separator pushed for the empty line between speakers
                                result['tokens'] = result['tokens'][:temp_index]
                                temp_index -= 1
                            elif tok_type in ('separator', 'character', 'dialogue', 'parenthetical'):
                                pass
                            elif tok_type == 'dialogue_begin':
                                result['tokens'][temp_index]['type'] = 'dual_dialogue_begin'
                                foundmatch = True
                            else:
                                foundmatch = True
                        dual_right = True
                        thistoken['dual'] = 'right'
                    else:
                        push_token(create_token(None, None, None, None, 'dialogue_begin'))
                    thistoken['text'] = re.sub(r'\^$', '', thistoken['text'])
                else:
                    push_token(create_token(None, None, None, None, 'dialogue_begin'))

                character = trim_character_extension(thistoken['text']).strip()
                previous_character = character
                if character in result['properties']['characters']:
                    values = result['properties']['characters'][character]
                    if scene_number not in values:
                        values.append(scene_number)
                else:
                    result['properties']['characters'][character] = [scene_number]
                last_character_index = len(result['tokens'])

            else:
                thistoken['type'] = 'action'
                process_action_block(thistoken)

        else:
            # Dialogue state
            if REGEX['parenthetical'].match(thistoken['text']):
                thistoken['type'] = 'parenthetical'
            else:
                thistoken['type'] = 'dialogue'
                process_dialogue_block(thistoken)
                thistoken['character'] = previous_character

            if dual_right:
                thistoken['dual'] = 'right'

        last_was_separator = False

        if token_category == 'script' and state != 'ignore':
            if thistoken['type'] in ('scene_heading', 'transition'):
                thistoken['text'] = thistoken['text'].upper()
                title_page_started = True

            if thistoken['text'] and thistoken['text'][0] == '~':
                thistoken['text'] = '*' + thistoken['text'][1:] + '*'

            if thistoken['type'] not in ('action', 'dialogue'):
                thistoken['text'] = thistoken['text'].strip()

            if thistoken['ignore']:
                ignored_last_token = True
            else:
                ignored_last_token = False
                push_token(thistoken)

    # Close any open dialogue
    if state == 'dialogue':
        push_token(create_token(None, None, None, None, 'dialogue_end'))
    if state == 'dual_dialogue':
        push_token(create_token(None, None, None, None, 'dual_dialogue_end'))

    # Clean trailing separators
    while result['tokens'] and result['tokens'][-1]['type'] == 'separator':
        result['tokens'].pop()

    return result


def extract_scenes(screenplay_content):
    """Extract scenes from Fountain content."""
    result = parse(screenplay_content)
    scenes = []
    current = None
    
    for token in result['tokens']:
        if token['type'] == 'scene_heading':
            if current:
                scenes.append(current)
            current = {
                'heading': token['text'],
                'number': token['number'],
                'characters': [],
                'location': '',
                'content': token['text'],
                'content_html': '',
            }
        elif current is not None:
            current['content'] += '\n' + token['text']
            
            if token['type'] == 'character':
                name = token.get('character', '').strip()
                if not name:
                    name = trim_character_extension(token['text']).strip()
                if name and name not in current['characters']:
                    current['characters'].append(name)
    
    if current:
        scenes.append(current)
    
    for i, scene in enumerate(scenes, 1):
        scene['id'] = i
        scene['content_html'] = tokens_to_html(result['tokens'])
    
    return scenes


def tokens_to_html(tokens):
    """Convert tokens to HTML with fountain-{type} CSS classes."""
    html = []
    isaction = False

    for token in tokens:
        t = token.get('type', '')
        text = token.get('text', '')
        ignore = token.get('ignore', False)


        if t in ('action', 'centered') and not ignore:
            # Strip emphasis markers and extract inline notes [[...]]
            notes = REGEX['note_inline'].findall(text)
            clean = REGEX['note_inline'].sub('', text)
            clean = re.sub(r'_{1,3}|\*{1,3}', '', clean)
            clean = clean.strip()
            classes = f'fountain-{t}'
            if notes:
                # Render action text, then notes after
                if not isaction:
                    html.append(f'<p><span class="{classes}">{clean}</span>')
                else:
                    html.append(f'<span class="{classes}">{clean}</span>')
                isaction = True
                for note in notes:
                    html.append(f'<p class="fountain-note">{note.strip()}</p>')
            else:
                if not isaction:
                    html.append(f'<p><span class="{classes}">{clean}</span>')
                else:
                    html.append(f'<span class="{classes}">{clean}</span>')
                isaction = True
        elif t == 'separator' and isaction:
            html.append('</p>')
            isaction = False
        else:
            if isaction:
                isaction = False
                html.append('</p>')

            if t == 'scene_heading':
                num = token.get('number', '')
                html.append(f'<h3 class="fountain-scene_heading" data-scenenumber="{num}">{text}</h3>')
            elif t == 'transition':
                html.append(f'<h2 class="fountain-transition">{text}</h2>')
            elif t == 'dual_dialogue_begin':
                html.append('<div class="dual-dialogue">')
            elif t == 'dialogue_begin':
                html.append('<div class="dialogue">')
            elif t == 'character':
                html.append(f'<h4 class="fountain-character">{text}</h4>')
            elif t == 'parenthetical':
                html.append(f'<p class="fountain-parenthetical">{text}</p>')
            elif t == 'dialogue':
                html.append(f'<p class="fountain-dialogue">{text}</p>')
            elif t == 'dialogue_end':
                html.append('</div>')
            elif t == 'dual_dialogue_end':
                html.append('</div></div>')
            elif t == 'section':
                depth = token.get('level', '')
                html.append(f'<p class="fountain-section" data-depth="{depth}">{text}</p>')
            elif t == 'synopsis':
                html.append(f'<p class="fountain-synopsis">{text}</p>')
            elif t == 'lyric':
                html.append(f'<p class="fountain-lyric">{text}</p>')
            elif t == 'note':
                html.append(f'<p class="fountain-note">{text}</p>')
            elif t == 'boneyard_begin':
                html.append('<!-- ')
            elif t == 'boneyard_end':
                html.append(' -->')
            elif t == 'page_break':
                html.append('<hr />')
            elif t == 'centered':
                html.append(f'<span class="fountain-centered">{text}</span>')

    if isaction:
        html.append('</p>')

    return '\n'.join(html)
