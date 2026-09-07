"""Section parser — zero-dependency regex parser for ## headings."""
import re

SECTION_RE = re.compile(r'^##\s+(.+)$', re.MULTILINE)


def list_sections(body: str) -> list[str]:
    """Extract ## headings from note body."""
    return SECTION_RE.findall(body)


def get_section(body: str, section: str) -> str:
    """Get a single section by name."""
    parts = SECTION_RE.split(body)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        body_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading.lower() == section.lower():
            return f"## {heading}\n{body_text}"
    return ""


def replace_section(body: str, section: str, new_body: str) -> str:
    """Replace a section's body."""
    parts = SECTION_RE.split(body)
    for i in range(1, len(parts), 2):
        heading = parts[i].strip().lstrip('#').strip()
        if heading.lower() == section.lower():
            original = parts[i + 1]
            # Preserve trailing newlines (blank line before next section)
            trailing = '\n\n' if original.endswith('\n\n') else '\n' if original.endswith('\n') else ''
            parts[i + 1] = '\n' + new_body.rstrip('\n') + trailing
            # Restore ## prefix to ALL headings (regex strips it)
            for j in range(1, len(parts), 2):
                parts[j] = '## ' + parts[j].strip().lstrip('#').strip()
            return ''.join(parts)
    return body
