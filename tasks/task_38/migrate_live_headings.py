#!/usr/bin/env python3
"""One-shot: replace each scene's frontmatter `heading` with `int_ext` + `place`.

Not plugin code. Run once against the live project, after the structured-heading
change landed:

    .venv/bin/python tasks/task_38/migrate_live_headings.py           # dry run
    .venv/bin/python tasks/task_38/migrate_live_headings.py --apply

`location` and `time_of_day` already exist in these notes and are left alone —
the retired free-text heading is only the source of `int_ext` / `place`. The
next story_import canonicalises whatever `## Content` heading line remains
(frontmatter wins field by field), so the vault ends up in the target shape.
"""

import re
import sys
from pathlib import Path

import frontmatter

from story_architect.core.scene_script import parse_heading_line

DEFAULT_PROJECT = Path(
    "/media/theww/AI/TWW/hermes-story-architect/projects/browser-verification-test"
)
HEADING_LINE = re.compile(r"^heading:[ \t]*(.+?)[ \t]*$", re.MULTILINE)


def _location_names(project: Path) -> dict:
    """slug -> name, so a heading naming a different place than the linked
    location is reported instead of silently changing the composed heading."""
    names = {}
    folder = project / "locations"
    if not folder.is_dir():
        return names
    for f in folder.glob("*.md"):
        fm = frontmatter.load(f)
        names[str(fm.metadata.get("id") or f.stem)] = str(fm.metadata.get("name") or "")
    return names


def _replacement(parsed: dict, existing: dict) -> list:
    """Lines replacing `heading:`, skipping fields the note already carries."""
    if parsed["forced_heading"]:
        return [] if existing.get("forced_heading") else [
            f"forced_heading: {parsed['forced_heading']}"]
    out = []
    if not existing.get("int_ext"):
        out.append(f"int_ext: {parsed['int_ext']}")
    if not existing.get("place"):
        out.append('place: ""')
    return out


def main(project: Path, apply: bool) -> int:
    names = _location_names(project)
    migrated = 0
    for path in sorted((project / "scenes").glob("*.md")):
        text = path.read_text()
        m = HEADING_LINE.search(text)
        if not m:
            continue
        fm = frontmatter.load(path)
        old = m.group(1).strip().strip("\"'")
        parsed = parse_heading_line(old)
        if not parsed:
            print(f"SKIP {path.name}: cannot parse heading {old!r}")
            continue

        lines = _replacement(parsed, fm.metadata)
        print(path.name)
        print(f"    heading: {old}")
        print(f"    -> {'  '.join(lines) if lines else '(fields already set, drop heading)'}")

        loc = str(fm.metadata.get("location") or "")
        declared_name = names.get(loc, "")
        if (parsed["location"] and declared_name
                and parsed["location"].upper() != declared_name.upper()):
            print(f"    ! linked location {loc!r} is {declared_name!r}; "
                  f"composes as {declared_name.upper()!r}")
        tod = str(fm.metadata.get("time_of_day") or "")
        if parsed["time_of_day"] and tod and parsed["time_of_day"].upper() != tod.upper():
            print(f"    ! declared time_of_day {tod!r}, heading said "
                  f"{parsed['time_of_day']!r}")

        migrated += 1
        if apply and lines:
            path.write_text(text[: m.start()] + "\n".join(lines) + text[m.end():])

    print(f"\n{migrated} scene(s) {'migrated' if apply else 'to migrate'}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(Path(args[0]) if args else DEFAULT_PROJECT, "--apply" in sys.argv))
