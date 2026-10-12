"""One-time fixture migration for B1/B2: strip removed value fields from markdown.

The fixture DB is a build artifact (see conftest.py). Markdown is the source
of truth. This script strips the removed fields from every fixture markdown
file's frontmatter, idempotently, with a backup.

Usage: python tests/migrate_fixture_b1_b2.py [--dry-run]
"""
import shutil
import sys
from pathlib import Path

import frontmatter

FIXTURE = Path(__file__).parent / "fixtures" / "save-the-children"

# arc beat fields (shift, y) are kept until B3 — only these paths are migrated.
MIGRATED_PREFIXES = ("scenes/", "acts/", "sequences/", "project.md")

# value_at_open/close appear on acts, sequences and scenes — all migrated.
# story_value* on project, conflict_levels on scenes — all migrated.
# shift and y appear ONLY on scenes among migrated paths (arcs are excluded).
ALL_REMOVED = {
    "story_value", "story_value_at_open", "story_value_at_close",
    "value_at_open", "value_at_close",
    "shift", "y", "conflict_levels",
}


def migrate(dry_run: bool = False) -> int:
    """Strip removed fields from fixture markdown. Returns count of files changed."""
    changed = 0
    for md in FIXTURE.rglob("*.md"):
        rel_str = md.relative_to(FIXTURE).as_posix()
        if not rel_str.startswith(MIGRATED_PREFIXES):
            continue
        post = frontmatter.load(md)
        to_remove = ALL_REMOVED & set(post.keys())
        if not to_remove:
            continue
        changed += 1
        rel = md.relative_to(FIXTURE)
        print(f"  {rel}: removing {sorted(to_remove)}")
        if not dry_run:
            for field in to_remove:
                del post[field]
            frontmatter.dump(post, md)
    return changed


def backup() -> Path:
    bak = FIXTURE.parent / "save-the-children.bak"
    if bak.exists():
        shutil.rmtree(bak)
    shutil.copytree(str(FIXTURE), str(bak))
    return bak


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("Dry run — no changes written:")
        n = migrate(dry_run=True)
        print(f"{n} files would be changed.")
    else:
        bak = backup()
        print(f"Backup: {bak}")
        n = migrate(dry_run=False)
        print(f"{n} files changed.")
