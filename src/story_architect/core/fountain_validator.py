"""Fountain syntax validator — for the future script-import feature.

DO NOT WIRE THIS INTO THE AUTHORING PATH. It is not the check you want, and
it is not broken. Read the two sections below before changing anything here.

WHAT THIS IS FOR
    A future "import entities/stats from an existing .fountain script"
    feature, which is not implemented. No tool handler calls this today. It is
    a *parser-side* check: given a screenplay someone else wrote, say what is
    in it. Pure functions only — no DB, no tool imports. Pairs with
    core/screenplay.py for the Fountain→entity extraction pipeline.

WHY IT MUST NOT BE MODIFIED FOR AUTHORING
    The authoring path needs the opposite job. An agent is *writing* script
    from a documented format and needs to be told where it departed. That is a
    linter; this is a parser. The same input gets opposite verdicts:

        ELIAS: You could have telephoned.

    _classify_line requires `stripped.isupper()` for a character cue, and the
    dialogue after the colon is lowercase, so this line classifies as `action`.

    - Here (import): correct. In Fountain the line genuinely IS action.
      Reporting "unknown element" would be a false alarm on a valid file.
    - For a linter (authoring): a missed catch. The author almost certainly
      meant a cue — it is what an agent naturally produces.

    Also: every rule here is local (does this line agree with its neighbour).
    A scene with no scene heading has no misbehaving line, so it passes — which
    is right for a partial screenplay and wrong for authoring feedback, where
    the missing heading is exactly the finding.

    Making this stricter to serve authoring would break a working importer to
    solve an unrelated problem. The fix is a SEPARATE module wired into
    `validate_shape` in core/drafts.py, taking inspiration from this one. See
    tasks/task_17*/bugs.md (B11). Do not rename this file either: a new module
    must not look like a variant of this one, or the two "validate Fountain"
    while answering different questions.

TODO(import feature): this is the only intended caller. Until then, leave
this file untouched.
"""
import re
from typing import Optional

# Scene heading prefixes
SCENE_PREFIXES = ['INT', 'EXT', 'EST', 'INT./EXT', 'INT/EXT', 'I/E']

# Transition suffixes
TRANSITION_SUFFIXES = ['TO:', 'TO BLACK.', 'OUT.']


class ValidationError:
    """A single validation issue."""
    def __init__(self, line: int, message: str, severity: str = 'error'):
        self.line = line
        self.message = message
        self.severity = severity  # 'error', 'warning', 'info'
    
    def __str__(self):
        return f"Line {self.line}: {self.message}"


def validate_screenplay(content: str) -> list[ValidationError]:
    """Validate a Fountain screenplay for syntax issues.
    
    Returns a list of ValidationError objects.
    """
    errors = []
    lines = content.split('\n')
    
    prev_type = None
    prev_line_num = None
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            prev_type = 'empty'
            prev_line_num = i
            continue
        
        # Classify the line
        line_type = _classify_line(stripped)
        
        # Rule: Character must have empty line before it
        if line_type == 'character' and prev_type not in ('empty', None):
            errors.append(ValidationError(
                i,
                f"Character cue '{stripped}' should have a blank line before it",
                'warning'
            ))
        
        # Rule: Scene heading must have empty line before it
        if line_type == 'scene_heading' and prev_type not in ('empty', None):
            errors.append(ValidationError(
                i,
                f"Scene heading '{stripped}' should have a blank line before it",
                'warning'
            ))
        
        # Rule: Transition must have empty line before and after
        if line_type == 'transition':
            if prev_type not in ('empty', None):
                errors.append(ValidationError(
                    i,
                    f"Transition '{stripped}' should have a blank line before it",
                    'warning'
                ))
            # Check if next line is empty
            if i < len(lines) and lines[i].strip():
                errors.append(ValidationError(
                    i,
                    f"Transition '{stripped}' should have a blank line after it",
                    'warning'
                ))
        
        # Rule: Dialogue must follow character or parenthetical
        if line_type == 'dialogue' and prev_type not in ('character', 'parenthetical', 'dialogue'):
            errors.append(ValidationError(
                i,
                f"Dialogue '{stripped[:30]}...' should follow a character or parenthetical",
                'error'
            ))
        
        # Rule: Parenthetical must follow character or dialogue
        if line_type == 'parenthetical' and prev_type not in ('character', 'dialogue'):
            errors.append(ValidationError(
                i,
                f"Parenthetical '{stripped}' should follow a character or dialogue",
                'warning'
            ))
        
        # Rule: Character must be ALL CAPS
        if line_type == 'character':
            if any(c.islower() for c in stripped):
                errors.append(ValidationError(
                    i,
                    f"Character cue '{stripped}' should be ALL CAPS",
                    'error'
                ))
        
        # Rule: Scene heading should start with valid prefix
        if line_type == 'scene_heading':
            has_prefix = any(stripped.upper().startswith(p) for p in SCENE_PREFIXES)
            if not has_prefix and not stripped.startswith('.'):
                errors.append(ValidationError(
                    i,
                    f"Scene heading '{stripped}' should start with INT/EXT/EST",
                    'error'
                ))
        
        # Rule: Parenthetical must be wrapped in ()
        if line_type == 'parenthetical':
            if not (stripped.startswith('(') and stripped.endswith(')')):
                errors.append(ValidationError(
                    i,
                    f"Parenthetical '{stripped}' should be wrapped in parentheses",
                    'error'
                ))
        
        # Rule: Transition should end with TO: or similar
        if line_type == 'transition':
            if not any(stripped.upper().endswith(s) for s in TRANSITION_SUFFIXES):
                errors.append(ValidationError(
                    i,
                    f"Transition '{stripped}' should end with 'TO:' or similar",
                    'warning'
                ))
        
        # Rule: Lyrics should start with ~
        if line_type == 'lyric' and not stripped.startswith('~'):
            errors.append(ValidationError(
                i,
                f"Lyric '{stripped}' should start with ~",
                'error'
            ))
        
        # Rule: Centered text should be wrapped in > <
        if line_type == 'centered':
            if not (stripped.startswith('>') and stripped.endswith('<')):
                errors.append(ValidationError(
                    i,
                    f"Centered text '{stripped}' should be wrapped in > <",
                    'error'
                ))
        
        # Rule: Title page keys should end with colon
        if line_type == 'title_page':
            if ':' not in stripped:
                errors.append(ValidationError(
                    i,
                    f"Title page entry '{stripped}' should be in 'key: value' format",
                    'error'
                ))
        
        prev_type = line_type
        prev_line_num = i
    
    return errors


def _classify_line(line: str) -> str:
    """Classify a single line of Fountain text."""
    stripped = line.strip()
    
    if not stripped:
        return 'empty'
    
    # Title page (key: value)
    if ':' in stripped and not stripped.startswith('(') and not stripped.startswith('>'):
        key = stripped.split(':')[0].strip()
        if key.lower() in ['title', 'credit', 'author', 'authors', 'source', 
                          'draft date', 'date', 'contact', 'copyright', 'notes',
                          'revision', 'watermark', 'font', 'header', 'footer']:
            return 'title_page'
    
    # Scene heading
    if any(stripped.upper().startswith(p) for p in SCENE_PREFIXES):
        return 'scene_heading'
    
    # Forced scene heading
    if stripped.startswith('.') and len(stripped) > 1 and stripped[1].isalnum():
        return 'scene_heading'
    
    # Transition
    if any(stripped.upper().endswith(s) for s in TRANSITION_SUFFIXES):
        return 'transition'
    
    # Forced transition
    if stripped.startswith('>'):
        return 'transition'
    
    # Centered
    if stripped.startswith('>') and stripped.endswith('<'):
        return 'centered'
    
    # Lyric
    if stripped.startswith('~'):
        return 'lyric'
    
    # Parenthetical
    if stripped.startswith('(') and stripped.endswith(')'):
        return 'parenthetical'
    
    # Character (ALL CAPS)
    if stripped.isupper() and any(c.isalpha() for c in stripped):
        return 'character'
    
    # Default: action
    return 'action'


def is_valid_screenplay(content: str) -> bool:
    """Quick check if a screenplay has no errors (warnings are OK)."""
    errors = validate_screenplay(content)
    return not any(e.severity == 'error' for e in errors)


def get_validation_summary(content: str) -> dict:
    """Get a summary of validation results."""
    errors = validate_screenplay(content)
    return {
        'valid': not any(e.severity == 'error' for e in errors),
        'errors': [str(e) for e in errors if e.severity == 'error'],
        'warnings': [str(e) for e in errors if e.severity == 'warning'],
        'total_issues': len(errors),
    }
