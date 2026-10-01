#!/usr/bin/env python3
"""One-shot rename: plot_payoff -> plot_resolution in a project database.

Not plugin code. Run by hand once, after the vocabulary rename landed in code:

    python3 tasks/task_31/rename_plot_roles.py [path/to/story.db]

Defaults to the live project. Only the `plot_payoff` kind is touched;
plot_setup / plot_crisis / plot_climax keep their names.
"""

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(
    "/media/theww/AI/TWW/hermes-story-architect/projects"
    "/browser-verification-test/.story/story.db"
)
OLD, NEW = "plot_payoff", "plot_resolution"


def main(db_path: Path) -> int:
    if not db_path.is_file():
        print(f"no database at {db_path}")
        return 1

    con = sqlite3.connect(db_path)
    try:
        before = dict(
            con.execute("SELECT kind, COUNT(*) FROM relations GROUP BY kind").fetchall()
        )
        con.execute("UPDATE relations SET kind=? WHERE kind=?", (NEW, OLD))
        con.commit()
        after = dict(
            con.execute("SELECT kind, COUNT(*) FROM relations GROUP BY kind").fetchall()
        )
    finally:
        con.close()

    print(f"{db_path}")
    for kind in sorted(set(before) | set(after)):
        if not kind.startswith("plot_"):
            continue
        b, a = before.get(kind, 0), after.get(kind, 0)
        moved = f"  <- {b} renamed" if b and b != a else ""
        print(f"  {kind:20} before {b:>3}  after {a:>3}{moved}")
    print(f"total rows rewritten: {before.get(OLD, 0)}")
    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    sys.exit(main(path))