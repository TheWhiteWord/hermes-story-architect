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
    start_line = scenes[scene_index]['line']
    end_line = scenes[scene_index + 1]['line'] if scene_index + 1 < len(scenes) else float('inf')
    lines = fountain.split('\n')
    return '\n'.join(lines[start_line:end_line])


def fountain_to_html(fountain):
    """Convert Fountain text to HTML."""
    tokens = tokenize(fountain)
    return tokens_to_html(tokens)


# ─── Main parser (from afterwriting-parser.js lines 126-749) ───

def parse(original_script, generate_html=False):
    """Parse Fountain screenplay into tokens.
    
    Faithful port of Better Fountain's parse() function.
    """
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
    
    def push_token(token):
        result['tokens'].append(token)
        if token['line'] is not None:
            result['tokenLines'][token['line']] = len(result['tokens']) - 1
    
    lines_length = len(lines)
    
    for i in range(lines_length):
        text = lines[i]
        
        # Handle boneyard (comments) with nesting (line 276)
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
        
        if nested_comments > 0 and state != 'ignore':
            state = 'ignore'
        elif state == 'ignore' and nested_comments == 0:
            state = 'normal'
        
        thistoken = create_token(text, current, i, new_line_length)
        thistoken['original_line'] = i + 1
        current = thistoken['end'] + 1
        
        # Empty line handling (lines 290-307)
        if text.strip() == '' and text != '  ':
            if state == 'dialogue':
                push_token(create_token(None, None, None, None, 'dialogue_end'))
            if state == 'dual_dialogue':
                push_token(create_token(None, None, None, None, 'dual_dialogue_end'))
            state = 'normal'
            dual_right = False
            thistoken['type'] = 'separator'
            last_was_separator = True
            push_token(thistoken)
            continue
        
        token_category = 'script'
        
        # Title page detection (lines 310-332)
        if not title_page_started and REGEX['title_page'].match(thistoken['text']):
            state = 'title_page'
        
        if state == 'title_page':
            if REGEX['title_page'].match(thistoken['text']):
                colon_idx = thistoken['text'].find(':')
                thistoken['type'] = thistoken['text'][:colon_idx].lower().replace(' ', '_')
                thistoken['text'] = thistoken['text'][colon_idx + 1:].strip()
                last_title_page_token = thistoken
                title_page_started = True
                continue
            elif title_page_started and last_title_page_token:
                last_title_page_token['text'] += ('\n' if last_title_page_token['text'] else '') + thistoken['text'].strip()
                continue
        
        # Normal state parsing (lines 334-513)
        if state == 'normal':
            scene_heading_match = REGEX['scene_heading'].match(thistoken['text'])
            if scene_heading_match:
                thistoken['text'] = re.sub(r'^\.', '', thistoken['text'])
                thistoken['type'] = 'scene_heading'
                thistoken['number'] = str(scene_number)
                scene_num_match = REGEX['scene_number'].search(thistoken['text'])
                if scene_num_match:
                    thistoken['text'] = REGEX['scene_number'].sub('', thistoken['text']).strip()
                    thistoken['number'] = scene_num_match.group(1)
                
                result['properties']['scenes'].append({
                    'scene': thistoken['number'],
                    'text': thistoken['text'],
                    'line': thistoken['line'],
                })
                scene_number += 1
            
            elif thistoken['text'] and thistoken['text'][0] == '!':
                thistoken['type'] = 'action'
                thistoken['text'] = thistoken['text'][1:]
            
            elif REGEX['centered'].match(thistoken['text']):
                thistoken['type'] = 'centered'
                thistoken['text'] = re.sub(r'>|(<)', '', thistoken['text']).strip()
            
            elif REGEX['transition'].match(thistoken['text']):
                thistoken['text'] = re.sub(r'^> ?', '', thistoken['text'])
                thistoken['type'] = 'transition'
            
            elif REGEX['synopsis'].match(thistoken['text']):
                match = REGEX['synopsis'].match(thistoken['text'])
                thistoken['text'] = match.group(1)
                thistoken['type'] = 'synopsis' if thistoken['text'] else 'separator'
            
            elif REGEX['section'].match(thistoken['text']):
                match = REGEX['section'].match(thistoken['text'])
                thistoken['level'] = len(match.group(1))
                thistoken['text'] = match.group(2)
                thistoken['type'] = 'section'
                current_depth = thistoken['level']
            
            elif REGEX['page_break'].match(thistoken['text']):
                thistoken['text'] = ''
                thistoken['type'] = 'page_break'
            
            elif (REGEX['character'].match(thistoken['text']) and 
                  i != lines_length and i != lines_length - 1):
                # Check next line for dialogue validation (line 443)
                next_line = lines[i + 1] if i + 1 < lines_length else ''
                if next_line.strip() == '' and next_line != '  ':
                    thistoken['type'] = 'action'
                else:
                    state = 'dialogue'
                    thistoken['type'] = 'character'
                    thistoken['text'] = trim_character_force_symbol(thistoken['text'])
                    
                    if thistoken['text'].endswith('^'):
                        state = 'dual_dialogue'
                        dual_right = True
                        thistoken['dual'] = 'right'
                        thistoken['text'] = re.sub(r'\^$', '', thistoken['text'])
                    else:
                        push_token(create_token(None, None, None, None, 'dialogue_begin'))
                    
                    character = trim_character_extension(thistoken['text']).strip()
                    previous_character = character
                    last_character_index = len(result['tokens'])
            
            else:
                thistoken['type'] = 'action'
        
        else:
            # Dialogue state (lines 516-527)
            if REGEX['parenthetical'].match(thistoken['text']):
                thistoken['type'] = 'parenthetical'
            else:
                thistoken['type'] = 'dialogue'
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
            
            if not thistoken['ignore']:
                push_token(thistoken)
    
    # Close any open dialogue (lines 551-556)
    if state == 'dialogue':
        push_token(create_token(None, None, None, None, 'dialogue_end'))
    if state == 'dual_dialogue':
        push_token(create_token(None, None, None, None, 'dual_dialogue_end'))
    
    # Clean trailing separators (lines 745-747)
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
    """Convert tokens to HTML."""
    html = []
    isaction = False
    
    for token in tokens:
        if token['type'] in ('action', 'centered') and not token['ignore']:
            classes = 'haseditorline'
            el_start = '\n'
            if not isaction:
                el_start = '<p>'
            if token['type'] == 'centered':
                if isaction:
                    el_start = ''
                classes += ' centered'
            html.append(f'{el_start}<span class="{classes}">{token.get("text", "")}</span>')
            isaction = True
        
        elif token['type'] == 'separator' and isaction:
            html.append('</p>')
        else:
            if isaction:
                isaction = False
                html.append('</p>')
            
            if token['type'] == 'scene_heading':
                html.append(f'<h3 data-scenenumber="{token["number"]}">{token["text"]}</h3>')
            elif token['type'] == 'transition':
                html.append(f'<h2>{token["text"]}</h2>')
            elif token['type'] == 'dialogue_begin':
                html.append(f'<div class="dialogue">')
            elif token['type'] == 'character':
                html.append(f'<h4>{token["text"]}</h4>')
            elif token['type'] == 'parenthetical':
                html.append(f'<p class="parenthetical">{token["text"]}</p>')
            elif token['type'] == 'dialogue':
                html.append(f'<p>{token["text"]}</p>')
            elif token['type'] == 'dialogue_end':
                html.append('</div>')
            elif token['type'] == 'page_break':
                html.append('<hr />')
    
    return '\n'.join(html)
