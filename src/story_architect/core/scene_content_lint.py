"""A linter for a scene's `Content`, not a Fountain parser.

There are two Fountain questions in this codebase and they have opposite
answers:

- `core/fountain_validator.py` — "is this a real screenplay?" Built to accept
  a human's own script for import. Loose, permissive parsing is correct there:
  a fragment with no scene heading is still valid input. **Do not modify it.**
- This module — "did the agent depart from the format it was given?" Strict,
  and only about the one failure that is silent rather than visible.

**The only thing checked here is that the first non-blank line of a scene's
`Content` is a scene heading.** Everything else the format allows is the
agent's business, and restating it in code would mean two things to update when
the format evolves. This one case is worth a check because the failure is
invisible: `core/screenplay.py:33` only accumulates into a scene once a heading
has been seen, so

- no heading at all  -> the scene renders as **nothing**, and
- text before one   -> that text is **silently discarded**

Both look like a working dashboard. Neither is signalled anywhere.

A forced heading (`.SNIPER SCOPE POV`) is a legitimate heading and is accepted
here for free — `SCENE_HEADING_RE` already matches it, and this module does not
re-derive that regex, so the two can never disagree about what a heading is.
"""

from .fountain_lexer import SCENE_HEADING_RE


def check_scene_content(content: str, heading: str = "") -> list[str]:
    """Findings for one scene's `Content`. Empty list means it renders.

    `heading` is the scene's frontmatter heading, if it has one. It is only
    used to make the message actionable: the author already wrote the heading
    somewhere, and naming it saves them writing it twice.
    """
    lines = (content or "").splitlines()
    first = next((ln for ln in lines if ln.strip()), "")

    if not first:
        return []  # Empty or whitespace-only: nothing to render, nothing wrong.

    if SCENE_HEADING_RE.match(first):
        return []

    # Two different failures, and saying which one it is saves a confused
    # round-trip: with no heading anywhere the scene is absent from the script
    # entirely, which looks like a dashboard bug rather than a formatting one.
    has_heading_later = any(SCENE_HEADING_RE.match(ln) for ln in lines)
    consequence = (
        "the scene is absent from the script"
        if not has_heading_later
        else "everything before the heading is dropped from the script")

    where = f" (frontmatter has '{heading}')" if heading else ""
    return [
        f"scene Content must open with a scene heading — the first line is "
        f"{first.strip()[:40]!r}, not one{where}, so {consequence}. Write "
        f"'INT./EXT. LOCATION - TIME OF DAY', or a forced heading "
        f"('.SNIPER SCOPE POV') for a location that has no INT/EXT."
    ]


def check_scenes(scenes: dict) -> list[str]:
    """Findings for `{entity_id: {"content": ..., "heading": ...}}`."""
    findings = []
    for entity_id, data in scenes.items():
        for f in check_scene_content(data.get("content", ""),
                                     data.get("heading", "")):
            findings.append(f"{entity_id}: {f}")
    return findings
